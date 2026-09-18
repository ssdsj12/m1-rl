"""Read-only evidence of ordinary cloning and the declared USD collision graph.

Importing this module loads neither USD nor the simulator. Collection membership
describes the authored graph, not contact behavior in the running physics engine.
"""


def clone_collision_evidence(scene, bar_paths):
    """Reject a changed environment group graph and record bar membership as found."""
    from pxr import Sdf, Usd

    def require(condition, message):
        if not condition:
            raise ValueError("clone collision evidence: " + message)

    try:
        replicate = scene.cfg.replicate_physics
        filtering = scene.cfg.filter_collisions
        count = scene.cfg.num_envs
        stage = scene.stage
        physics_path = str(scene.physics_scene_path)
        env_paths = [str(path) for path in scene.env_prim_paths]
        global_paths = list(dict.fromkeys(str(path) for path in scene._global_prim_paths))
    except (AttributeError, TypeError) as error:
        raise ValueError("clone collision evidence: missing actual scene configuration or paths") from error
    require(replicate is False, "replicate_physics must be False")
    require(filtering is True, "filter_collisions must be True")
    require(stage is not None, "missing actual scene stage")
    require(len(env_paths) == count and count > 0 and len(set(env_paths)) == count,
            "environment path count/uniqueness differs from actual scene cfg")
    require(bool(global_paths), "missing global prim paths")
    bars = [str(path) for path in bar_paths]
    require(len(bars) == count and len(set(bars)) == count, "bar path count/uniqueness mismatch")
    for path in [physics_path, "/World/ground"] + env_paths + global_paths + bars:
        usd_path = Sdf.Path(path)
        require(usd_path.IsAbsolutePath() and usd_path.IsPrimPath() and bool(stage.GetPrimAtPath(usd_path)),
                "missing or invalid actual prim: " + path)
        prim = stage.GetPrimAtPath(usd_path)
        require(prim.IsActive() and prim.IsDefined(), "inactive or undefined actual prim: " + path)
    physics = stage.GetPrimAtPath(physics_path)
    require(physics.GetTypeName() == "PhysicsScene", "actual physics scene has wrong type")
    invert = physics.GetAttribute("physxScene:invertCollisionGroupFilter").Get()
    require(invert is True, "physxScene:invertCollisionGroupFilter must be True")

    env_groups = [f"/World/collisions/group{i}" for i in range(count)]
    global_group = "/World/collisions/global_group"
    expected_groups = set(env_groups + [global_group])
    actual_groups = {str(prim.GetPath()): prim for prim in stage.TraverseAll()
                     if prim.GetTypeName() == "PhysicsCollisionGroup"}
    require(set(actual_groups) == expected_groups, "missing, extra, or wrong-type collision groups: "
            + str(sorted(set(actual_groups) ^ expected_groups)))
    root = stage.GetPrimAtPath("/World/collisions")
    require(root and {str(prim.GetPath()) for prim in root.GetAllChildren()} == expected_groups,
            "unexpected children under /World/collisions")

    def targets(prim, name, forwarded=False):
        relation = prim.GetRelationship(name)
        if not relation:
            return []
        return [str(path) for path in (relation.GetForwardedTargets() if forwarded else relation.GetTargets())]

    groups, queries = [], {}
    for path in sorted(actual_groups):
        prim = actual_groups[path]
        require(prim.IsActive() and prim.IsDefined(), "inactive or undefined collision group: " + path)
        collection = Usd.CollectionAPI.Get(prim, "colliders")
        require(prim.HasAPI(Usd.CollectionAPI, "colliders"), "missing colliders collection: " + path)
        record = {
            "path": path, "type_name": str(prim.GetTypeName()),
            "includes": targets(prim, "collection:colliders:includes"),
            "includes_forwarded": targets(prim, "collection:colliders:includes", True),
            "filtered_groups": targets(prim, "physics:filteredGroups"),
            "filtered_groups_forwarded": targets(prim, "physics:filteredGroups", True),
            "excludes": targets(prim, "collection:colliders:excludes"),
            "excludes_forwarded": targets(prim, "collection:colliders:excludes", True),
            "expansion_rule": collection.GetExpansionRuleAttr().Get(),
            "include_root": collection.GetIncludeRootAttr().Get(),
            "merge_group": prim.GetAttribute("physics:mergeGroup").Get(),
            "invert_filtered_groups": prim.GetAttribute("physics:invertFilteredGroups").Get(),
        }
        expected_includes = global_paths if path == global_group else [env_paths[env_groups.index(path)]]
        expected_filtered = expected_groups if path == global_group else {path, global_group}
        for key in ("includes", "includes_forwarded"):
            require(set(record[key]) == set(expected_includes), f"unexpected {key}: {path}")
        for key in ("filtered_groups", "filtered_groups_forwarded"):
            require(set(record[key]) == expected_filtered, f"unexpected {key}: {path}")
        require(record["expansion_rule"] == "expandPrims", "unexpected expansion rule: " + path)
        require(not record["excludes"] and not record["excludes_forwarded"], "unexpected excludes: " + path)
        require(record["include_root"] in (None, False), "unexpected includeRoot: " + path)
        require(record["merge_group"] in (None, ""), "unexpected mergeGroup: " + path)
        require(record["invert_filtered_groups"] in (None, False), "unexpected invertFilteredGroups: " + path)
        queries[path] = collection.ComputeMembershipQuery()
        groups.append(record)

    def membership(path):
        return {"path": path, "collision_groups": [group for group, query in queries.items()
                if query.IsPathIncluded(Sdf.Path(path))]}

    env_memberships = [membership(path) for path in env_paths]
    for index, member in enumerate(env_memberships):
        require(member["collision_groups"] == [env_groups[index]], "incorrect env container membership: " + member["path"])
    global_memberships = [membership(path) for path in global_paths]
    for member in global_memberships:
        require(member["collision_groups"] == [global_group], "incorrect global prim membership: " + member["path"])
    ground_membership = membership("/World/ground")
    require(ground_membership["collision_groups"] == [global_group], "ground missing exclusive global group membership")
    bar_memberships = [membership(path) for path in bars]
    return {
        "replicate_physics": replicate, "filter_collisions": filtering,
        "physics_scene_path": physics_path, "invert_collision_group_filter": invert,
        "env_prim_paths": env_paths, "global_prim_paths": global_paths,
        "collision_groups": groups, "env_memberships": env_memberships,
        "global_memberships": global_memberships, "ground_membership": ground_membership,
        "bar_memberships": bar_memberships,
        "bars_without_collision_group": [member["path"] for member in bar_memberships if not member["collision_groups"]],
        "declared_graph_valid": True, "dynamic_collision_filtering_verified": False,
        "bar_own_environment_isolation_verified": False,
        "limitations": "Declared USD group graph and collection membership only; no per-collider/instance-proxy audit "
                       "or dynamic physics filtering test. Ungrouped bars are reported as found. This does not prove "
                       "bars collide only with their own environment; no contact opportunity is not filtering validation.",
    }
