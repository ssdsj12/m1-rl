# M1 Reference Provenance Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before any eight-environment simulation, fail closed unless the portable floating M1 asset is the documented, unchanged reference bundle and preserves the original floating overlay.

**Architecture:** Add a standalone provenance module under `tools/m1_reference_validation` in the existing m1_rl project, leaving all reference and production-training files unchanged. A pure standard-library check establishes source/hash/overlay equivalence; a separate read-only USD inspection establishes runtime composition and material resolution before the later controller adapter. This is the first bounded implementation stage of the approved 8→1024 design, not completion of that design.

**Tech Stack:** Python3.10 in amp, pytest, pathlib/hashlib/json, existing pxr for read-only composition inspection. No package installation or Isaac launch in this stage.

---

## Locations and baseline

- Remote project: `/home/hexinkun/m1_rl`, branch `m1_rl`, baseline `bd78daa` plus preserved dirty user work.
- Read-only reference: `/home/hexinkun/m1`.
- Local editing stage: `C:/Users/xk/Documents/project/m1_reference_validation_stage`.
- Create remote `tools/m1_reference_validation/provenance.py` and `tools/m1_reference_validation/tests/test_provenance.py`; local stage mirrors these paths.
- Main agent owns upload, commit and note synchronization. The implementer must not touch existing files or start simulation.
- CPU reference baseline already observed: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=/home/hexinkun/m1/Go2Pvcnn /home/hexinkun/miniconda3/envs/amp/bin/python -m pytest -q -p no:cacheprovider /home/hexinkun/m1/Go2Pvcnn/tests/test_m1_curriculum.py` →88passed.

## Task 1: Source provenance guard

- [ ] Create the following test file first. Its loader uses an assertion so absence of the module is a failing feature test, not an unrelated import error.

```python
from pathlib import Path
import hashlib
import importlib.util
import json
import pytest

def load_module():
    path = Path(__file__).parents[1] / "provenance.py"
    assert path.is_file(), "provenance implementation is missing"
    spec = importlib.util.spec_from_file_location("reference_provenance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def fixture_bundle(tmp_path):
    project = tmp_path / "Go2Pvcnn"
    asset = project / "assets/m1_panda"
    asset.mkdir(parents=True)
    old_root = "/home/xk/ros2_ws/src/zjs_m1_v3_description/urdf/ZJ_V3_URDF_V1_0"
    entry = "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd"
    (asset / "source_manifest.json").write_text(json.dumps({"m1": {"source": old_root, "entry": entry}}))
    names = ["ZJ_V3_URDF_V1_0.usd"] + ["configuration/ZJ_V3_URDF_V1_0_" + part + ".usd" for part in ("base", "physics", "sensor")]
    records = []
    for name in names:
        file = asset / "m1/ZJ_V3_URDF_V1_0" / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(name.encode())
        records.append(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.relative_to(project).as_posix())
    text = '#usda 1.0\n( subLayers = [@' + old_root + '/configuration/ZJ_V3_URDF_V1_0_physics.usd@] )\nover "Robot" {}\n'
    original = project / "assets/m1_usd/ZJ_V3_URDF_V1_0_floating.usda"
    original.parent.mkdir(parents=True)
    original.write_bytes(text.encode())
    portable = asset / "m1_floating.usda"
    portable.write_bytes(text.replace(old_root + "/configuration/ZJ_V3_URDF_V1_0_physics.usd", "./" + entry).replace("\n", "\r\n").encode())
    records.append(hashlib.sha256(portable.read_bytes().replace(b"\r\n", b"\n")).hexdigest() + "  assets/m1_panda/m1_floating.usda")
    (asset / "source_files.sha256").write_text("\n".join(records))
    return project, portable

def test_reference_copy_accepts_only_path_and_newline_relocation(tmp_path):
    project, portable = fixture_bundle(tmp_path)
    result = load_module().audit_provenance(project)
    assert result["passed"] is True
    assert result["overlay_path"] == str(portable.resolve())
    assert len(result["binary_hashes"]) == 4

def test_modified_binary_fails_closed(tmp_path):
    project, _ = fixture_bundle(tmp_path)
    file = project / "assets/m1_panda/m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_base.usd"
    file.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_module().audit_provenance(project)

def test_overlay_behavior_change_is_rejected(tmp_path):
    project, portable = fixture_bundle(tmp_path)
    portable.write_bytes(portable.read_bytes() + b"\nover \"wheel\" {}\n")
    with pytest.raises(ValueError):
        load_module().audit_provenance(project)

def test_missing_dependency_fails_closed(tmp_path):
    project, _ = fixture_bundle(tmp_path)
    (project / "assets/m1_panda/m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_sensor.usd").unlink()
    with pytest.raises(FileNotFoundError):
        load_module().audit_provenance(project)

def test_wrong_provenance_source_rejected(tmp_path):
    project, _ = fixture_bundle(tmp_path)
    path = project / "assets/m1_panda/source_manifest.json"
    data = json.loads(path.read_text())
    data["m1"]["source"] = "/other/robot"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="source"):
        load_module().audit_provenance(project)
```

- [ ] Upload only tests to the new remote directory and run them with amp pytest, `-p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`; confirm the missing-module assertion fails. Do not run tests against unrelated existing source.
- [ ] Add the exact minimal implementation below, then rerun the same tests.

```python
"""Read-only source/hash guard for the portable reference M1 floating asset."""
from pathlib import Path
import hashlib
import json

ORIGINAL_ROOT = "/home/xk/ros2_ws/src/zjs_m1_v3_description/urdf/ZJ_V3_URDF_V1_0"
ENTRY = "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd"
BINARY_NAMES = ("ZJ_V3_URDF_V1_0.usd", "configuration/ZJ_V3_URDF_V1_0_base.usd", "configuration/ZJ_V3_URDF_V1_0_physics.usd", "configuration/ZJ_V3_URDF_V1_0_sensor.usd")

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def audit_provenance(project):
    project = Path(project).resolve(strict=True)
    assets = project / "assets/m1_panda"
    manifest_path = assets / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("m1") != {"source": ORIGINAL_ROOT, "entry": ENTRY}:
        raise ValueError("source manifest does not identify the expected original M1")
    expected = {}
    for line in (assets / "source_files.sha256").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if name in expected:
            raise ValueError("duplicate source hash entry: " + name)
        expected[name] = checksum
    hashes = {}
    for name in BINARY_NAMES:
        path = assets / "m1/ZJ_V3_URDF_V1_0" / name
        relative = path.relative_to(project).as_posix()
        actual = sha256(path)
        if expected.get(relative) != actual:
            raise ValueError("hash mismatch: " + relative)
        hashes[relative] = actual
    original = project / "assets/m1_usd/ZJ_V3_URDF_V1_0_floating.usda"
    portable = assets / "m1_floating.usda"
    original_text = original.read_text(encoding="utf-8")
    portable_text = portable.read_text(encoding="utf-8")
    old_ref = "@" + ORIGINAL_ROOT + "/configuration/ZJ_V3_URDF_V1_0_physics.usd@"
    new_ref = "@./" + ENTRY + "@"
    if original_text.count(old_ref) != 1 or original_text.replace(old_ref, new_ref) != portable_text:
        raise ValueError("floating overlay changes more than the sublayer path")
    normalized_hash = hashlib.sha256(portable_text.encode("utf-8")).hexdigest()
    if expected.get("assets/m1_panda/m1_floating.usda") != normalized_hash:
        raise ValueError("portable overlay hash mismatch after newline normalization")
    return {"passed": True, "overlay_path": str(portable.resolve()), "binary_hashes": hashes,
            "manifest_sha256": sha256(manifest_path), "source_hash_list_sha256": sha256(assets / "source_files.sha256"),
            "original_overlay_sha256": sha256(original), "portable_overlay_sha256": sha256(portable),
            "portable_overlay_lf_sha256": normalized_hash,
            "scope": "provenance_only_not_runtime_or_behavior"}
```

- [ ] Add a regression for a correct hash but altered overlay by updating its hash record; require the textual-equivalence check still rejects it. Add duplicate-record and missing-hash-record tests. All reads must remain read-only and no module import may load torch/Isaac/pxr.
- [ ] Spec review, then independent quality review. Fix discovered Important issues before real-asset use.
- [ ] Run `audit_provenance(Path('/home/hexinkun/m1/Go2Pvcnn'))` with amp; save its JSON to the task's evidence directory through a reviewed caller. Confirm four binary records and equivalent overlay. Main agent commits only the two new files.

## Task 2: Read-only USD dependency gate (no application start)

- [ ] Use the installed amp `omni.usd.libs` Python/bin paths and the installed `omni/mdl/core/Base` MDL search directory, not any tests directory. Verify `Ar` resolver context can resolve `OmniPBR.mdl`.
- [ ] Open the provenance-verified floating overlay in `Usd.Stage`; compute `UsdUtils.ComputeAllDependencies` under the bound resolver context. Require zero unresolved USD/mesh/material asset names and zero stage composition errors.
- [ ] Verify17 rigid bodies,16 named revolute joints,one articulation at BASE_LINK,inactive root_joint,13mesh+4cylinder robot collisions,wheel cylinder radius0.0959,width0.0465,Yaxis. Record authored total mass41.045319557kg and that overlay's stand-alone stage units/upAxis are fallback values shared by old/new overlays, not a change to be silently repaired.
- [ ] Freeze source/hash/asset results and actual installed interpreter/pxr locations. If closure fails, stop before simulation and report exact unresolved identifiers; do not substitute material or robot assets.
- [ ] Record the distinction between actual cylinder radius0.0959 and reference acceptance helper radius0.095. Later adapter must retain original helper results and independently enforce the approved actual-radius-plus5mm criterion; never loosen the criterion.

## Downstream gate (not implemented in this preflight task)

After Tasks1–2 pass, prepare the bounded controller adapter/metrics plan using these already-read interfaces: explicit ContactFreePlay cfg+M1RslRlEnvWrapper,zero16dim residual,RecorderTerm.record_post_step before reset,EXPORT_NONE,first-episode failure latch,terrain1×N unique8m tiles. That next plan must include exact metric tests, source-binding tests and process completion tests before code. It executes8×32 then3×8×1600 before any1024×32/1600 trial. No fallback to1env and no10000training.
