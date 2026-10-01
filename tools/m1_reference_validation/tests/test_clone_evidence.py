"""CPU-only checks of the ordinary-clone USD collision graph; no simulator starts."""

import builtins
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from pxr import Sdf, Usd, UsdGeom, UsdPhysics


def evidence_module():
    path = Path(__file__).resolve().parents[1] / "clone_evidence.py"
    assert path.is_file(), "Missing read-only clone collision evidence helper"
    spec = importlib.util.spec_from_file_location("clone_evidence_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collision_scene():
    stage = Usd.Stage.CreateInMemory()
    physics = UsdPhysics.Scene.Define(stage, "/World/physicsScene").GetPrim()
    physics.CreateAttribute("physxScene:invertCollisionGroupFilter", Sdf.ValueTypeNames.Bool).Set(True)
    env_paths = [f"/World/envs/env_{i}" for i in range(8)]
    bar_paths = [f"/World/semantic_course/small/row_00/col_{i:02d}/slot_00" for i in range(8)]
    for path in env_paths + bar_paths + ["/World/ground"]:
        UsdGeom.Xform.Define(stage, path)
    group_paths = [f"/World/collisions/group{i}" for i in range(8)]
    global_group = "/World/collisions/global_group"
    for group_path, included in zip(group_paths + [global_group], env_paths + ["/World/ground"]):
        group = UsdPhysics.CollisionGroup.Define(stage, group_path)
        collection = Usd.CollectionAPI.Apply(group.GetPrim(), "colliders")
        collection.CreateExpansionRuleAttr().Set(Usd.Tokens.expandPrims)
        collection.CreateIncludesRel().SetTargets([included])
        filtered = [group_path, global_group] if group_path != global_group else [global_group] + group_paths
        group.CreateFilteredGroupsRel().SetTargets(filtered)
    scene = SimpleNamespace(stage=stage, physics_scene_path=str(physics.GetPath()),
                            env_prim_paths=env_paths, _global_prim_paths=["/World/ground", "/World/ground"],
                            cfg=SimpleNamespace(num_envs=8, replicate_physics=False, filter_collisions=True))
    return scene, bar_paths


def test_valid_graph_records_actual_relationships_membership_and_limitations_without_writes():
    scene, bars = collision_scene()
    before = scene.stage.GetRootLayer().ExportToString()
    evidence = evidence_module().clone_collision_evidence(scene, bars)
    assert scene.stage.GetRootLayer().ExportToString() == before
    assert evidence["replicate_physics"] is False and evidence["filter_collisions"] is True
    assert evidence["invert_collision_group_filter"] is True
    assert evidence["physics_scene_path"] == scene.physics_scene_path
    assert evidence["env_prim_paths"] == scene.env_prim_paths
    assert evidence["global_prim_paths"] == ["/World/ground"]
    assert len(evidence["collision_groups"]) == 9
    groups = {group["path"]: group for group in evidence["collision_groups"]}
    group = groups["/World/collisions/group0"]
    assert group["type_name"] == "PhysicsCollisionGroup"
    assert group["includes"] == group["includes_forwarded"] == [scene.env_prim_paths[0]]
    assert set(group["filtered_groups"]) == set(group["filtered_groups_forwarded"]) == {
        group["path"], "/World/collisions/global_group"}
    assert group["expansion_rule"] == "expandPrims"
    assert evidence["env_memberships"] == [
        {"path": path, "collision_groups": [f"/World/collisions/group{i}"]}
        for i, path in enumerate(scene.env_prim_paths)]
    assert evidence["ground_membership"] == {
        "path": "/World/ground", "collision_groups": ["/World/collisions/global_group"]}
    assert evidence["bar_memberships"] == [{"path": path, "collision_groups": []} for path in bars]
    assert evidence["bars_without_collision_group"] == bars
    assert evidence["declared_graph_valid"] is True
    assert evidence["dynamic_collision_filtering_verified"] is False
    assert evidence["bar_own_environment_isolation_verified"] is False
    assert "no contact opportunity" in evidence["limitations"]
    json.dumps(evidence, allow_nan=False)


@pytest.mark.parametrize("fault", [
    "missing_group", "extra_group", "extra_group_elsewhere", "wrong_type", "wrong_env",
    "wrong_filtered_target", "missing_self_target", "wrong_global_includes", "wrong_global_filter",
    "filter_disabled", "replicate_enabled", "invert_false", "invert_missing", "wrong_expansion",
    "excludes", "include_root", "merge_group", "local_invert", "forwarded_includes", "forwarded_filtered",
    "missing_env", "missing_bar", "missing_physics_scene", "missing_actual_field", "env_count",
    "inactive_group", "inactive_global_group", "inactive_physics_scene", "inactive_env", "inactive_ground", "inactive_bar",
    "undefined_group", "undefined_global_group", "undefined_physics_scene", "undefined_env", "undefined_ground", "undefined_bar",
])
def test_incomplete_or_changed_graph_is_rejected_without_writes(fault):
    scene, bars = collision_scene()
    stage = scene.stage
    group = stage.GetPrimAtPath("/World/collisions/group0")
    global_group = stage.GetPrimAtPath("/World/collisions/global_group")
    if fault == "missing_group":
        stage.RemovePrim("/World/collisions/group7")
    elif fault in ("extra_group", "extra_group_elsewhere"):
        UsdPhysics.CollisionGroup.Define(stage, "/World/collisions/group8" if fault == "extra_group" else "/World/extra")
    elif fault == "wrong_type":
        group.SetTypeName("Scope")
    elif fault == "wrong_env":
        group.GetRelationship("collection:colliders:includes").SetTargets([scene.env_prim_paths[1]])
    elif fault in ("wrong_filtered_target", "missing_self_target"):
        targets = ["/World/collisions/global_group"]
        if fault == "wrong_filtered_target":
            targets += ["/World/collisions/group0", "/World/collisions/group1"]
        group.GetRelationship("physics:filteredGroups").SetTargets(targets)
    elif fault == "wrong_global_includes":
        global_group.GetRelationship("collection:colliders:includes").SetTargets([bars[0]])
    elif fault == "wrong_global_filter":
        global_group.GetRelationship("physics:filteredGroups").SetTargets(["/World/collisions/global_group"])
    elif fault in ("filter_disabled", "replicate_enabled"):
        setattr(scene.cfg, "filter_collisions" if fault == "filter_disabled" else "replicate_physics",
                fault == "replicate_enabled")
    elif fault == "invert_false":
        stage.GetPrimAtPath(scene.physics_scene_path).GetAttribute("physxScene:invertCollisionGroupFilter").Set(False)
    elif fault == "invert_missing":
        stage.GetPrimAtPath(scene.physics_scene_path).RemoveProperty("physxScene:invertCollisionGroupFilter")
    elif fault == "wrong_expansion":
        group.GetAttribute("collection:colliders:expansionRule").Set("explicitOnly")
    elif fault == "excludes":
        group.CreateRelationship("collection:colliders:excludes").SetTargets([scene.env_prim_paths[0] + "/Robot"])
    elif fault == "include_root":
        group.CreateAttribute("collection:colliders:includeRoot", Sdf.ValueTypeNames.Bool).Set(True)
    elif fault == "merge_group":
        group.CreateAttribute("physics:mergeGroup", Sdf.ValueTypeNames.String).Set("merged")
    elif fault == "local_invert":
        group.CreateAttribute("physics:invertFilteredGroups", Sdf.ValueTypeNames.Bool).Set(True)
    elif fault in ("forwarded_includes", "forwarded_filtered"):
        relation = group.CreateRelationship("forwarding")
        relation.SetTargets([scene.env_prim_paths[0] if fault == "forwarded_includes" else "/World/collisions/group0"])
        group.GetRelationship("collection:colliders:includes" if fault == "forwarded_includes"
                              else "physics:filteredGroups").SetTargets([relation.GetPath()])
    elif fault == "missing_env":
        stage.RemovePrim(scene.env_prim_paths[7])
    elif fault == "missing_bar":
        stage.RemovePrim(bars[7])
    elif fault == "missing_physics_scene":
        stage.RemovePrim(scene.physics_scene_path)
    elif fault == "missing_actual_field":
        del scene._global_prim_paths
    elif fault == "env_count":
        scene.cfg.num_envs = 7
    elif fault.startswith(("inactive_", "undefined_")):
        state, target = fault.split("_", 1)
        path = {"group": "/World/collisions/group0", "global_group": "/World/collisions/global_group",
                "physics_scene": scene.physics_scene_path, "env": scene.env_prim_paths[0],
                "ground": "/World/ground", "bar": bars[0]}[target]
        if state == "inactive":
            stage.GetPrimAtPath(path).SetActive(False)
        else:
            stage.GetRootLayer().GetPrimAtPath(path).specifier = Sdf.SpecifierOver
    before = stage.GetRootLayer().ExportToString()
    with pytest.raises(ValueError, match="clone collision"):
        evidence_module().clone_collision_evidence(scene, bars)
    assert stage.GetRootLayer().ExportToString() == before


def test_bar_membership_is_computed_from_usd_collection_instead_of_path_assumption():
    scene, bars = collision_scene()
    nested_bar = scene.env_prim_paths[3] + "/bar"
    UsdGeom.Xform.Define(scene.stage, nested_bar)
    bars[3] = nested_bar
    evidence = evidence_module().clone_collision_evidence(scene, bars)
    assert evidence["bar_memberships"][3] == {
        "path": nested_bar, "collision_groups": ["/World/collisions/group3"]}
    assert nested_bar not in evidence["bars_without_collision_group"]
    assert evidence["bar_own_environment_isolation_verified"] is False


def test_import_does_not_import_simulator_or_usd(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        assert name.split(".")[0] not in {"isaaclab", "isaacsim", "omni", "carb", "pxr"}
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    assert callable(evidence_module().clone_collision_evidence)


@pytest.mark.parametrize("missing_group", [False, True])
def test_validate_scene_persists_evidence_and_rejects_bad_graph(tmp_path, monkeypatch, missing_group):
    path = Path(__file__).resolve().parents[1] / "runtime.py"
    spec = importlib.util.spec_from_file_location("clone_runtime_under_test", path)
    rt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rt)
    scene_data, bars = collision_scene()
    stage = scene_data.stage
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    ground = UsdGeom.Mesh.Define(stage, "/World/ground/mesh")
    ground.GetPointsAttr().Set([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)])
    ground.GetFaceVertexCountsAttr().Set([3, 3])
    ground.GetFaceVertexIndicesAttr().Set([0, 1, 2, 0, 2, 3])
    for index, bar in enumerate(bars):
        cube = UsdGeom.Cube.Define(stage, bar + "/cube")
        cube.GetSizeAttr().Set(1)
        cube.AddTranslateOp().Set((0.85, index * 8 - 0.2, 0.015))
        cube.AddScaleOp().Set((0.06, 0.16, 0.06))
    body_paths = [f"{env}/Robot/{body}" for env in scene_data.env_prim_paths for body in rt.CONTACT_BODY_NAMES]
    robot = SimpleNamespace(is_fixed_base=False, body_names=list(rt.CONTACT_BODY_NAMES),
                            joint_names=[f"j{i}" for i in range(16)],
                            root_physx_view=SimpleNamespace(prim_paths=[env + "/Robot" for env in scene_data.env_prim_paths]),
                            data=SimpleNamespace(body_pos_w=np.zeros((8, 17, 3))))
    view = SimpleNamespace(prim_paths=body_paths, get_transforms=lambda: np.zeros((136, 7)))
    sensor = SimpleNamespace(_body_physx_view=view, body_names=list(rt.CONTACT_BODY_NAMES),
                             row_for_env=np.arange(8), own_indices=np.arange(8),
                             semantic_filter_paths=bars, contact_path_evidence={}, _sensor_paths=body_paths)
    class Scene(SimpleNamespace):
        def __getitem__(self, key):
            return robot if key == "robot" else sensor
    scene = Scene(**vars(scene_data), env_origins=np.array([[0, i * 8, 0] for i in range(8)]))
    env = SimpleNamespace(scene=scene, num_envs=8)
    for name in ("isaaclab", "isaaclab.sim", "extension", "extension.semantic_course"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    sys.modules["isaaclab.sim"].utils = SimpleNamespace(get_current_stage=lambda: stage)
    sys.modules["extension.semantic_course"].DEFAULT_GROUNDING_EMBED_DEPTH_M = 0.015
    monkeypatch.setitem(sys.modules, "clone_evidence", evidence_module())
    if missing_group:
        stage.RemovePrim("/World/collisions/group7")
    before = stage.GetRootLayer().ExportToString()
    if missing_group:
        with pytest.raises(ValueError, match="clone collision"):
            rt.validate_scene(env, tmp_path)
        assert not (tmp_path / "scene_manifest.json").exists()
    else:
        manifest, _, _ = rt.validate_scene(env, tmp_path)
        assert manifest["clone_collision_evidence"]["declared_graph_valid"] is True
        assert json.loads((tmp_path / "scene_manifest.json").read_text())["clone_collision_evidence"] == \
            manifest["clone_collision_evidence"]
    assert stage.GetRootLayer().ExportToString() == before
