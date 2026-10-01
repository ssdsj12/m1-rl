"""Synthetic, simulator-free contracts for the reference M1 provenance gate."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SOURCE = "/home/xk/ros2_ws/src/zjs_m1_v3_description/urdf/ZJ_V3_URDF_V1_0"
ENTRY = "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd"
ORIGINAL_TOKEN = f"@{SOURCE}/configuration/ZJ_V3_URDF_V1_0_physics.usd@"
PORTABLE_TOKEN = f"@./{ENTRY}@"
BUNDLE = Path("assets/m1_panda")
MANIFEST = BUNDLE / "source_manifest.json"
HASH_LIST = BUNDLE / "source_files.sha256"
ORIGINAL = Path("assets/m1_usd/ZJ_V3_URDF_V1_0_floating.usda")
PORTABLE = BUNDLE / "m1_floating.usda"
BINARY_PATHS = (
    BUNDLE / "m1/ZJ_V3_URDF_V1_0/ZJ_V3_URDF_V1_0.usd",
    BUNDLE / "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_base.usd",
    BUNDLE / "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd",
    BUNDLE / "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_sensor.usd",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def normalized_bytes(path):
    return path.read_text(encoding="utf-8").encode("utf-8")


def load_guard():
    implementation = Path(__file__).resolve().parents[1] / "provenance.py"
    assert implementation.is_file(), "Missing provenance guard implementation"
    spec = importlib.util.spec_from_file_location("m1_provenance_under_test", implementation)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit_provenance


def refresh_hash_list(project):
    lines = [
        f"{digest((project / path).read_bytes())}  {path.as_posix()}"
        for path in BINARY_PATHS
    ]
    lines.append(f"{digest(normalized_bytes(project / PORTABLE))}  {PORTABLE.as_posix()}")
    (project / HASH_LIST).write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "Go2Pvcnn"
    (root / MANIFEST).parent.mkdir(parents=True)
    (root / MANIFEST).write_text(
        json.dumps({"m1": {"source": SOURCE, "entry": ENTRY}, "panda": {}}),
        encoding="utf-8",
    )
    for index, relative in enumerate(BINARY_PATHS):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"PXR-USDC\x00\xff\x00" + bytes([index]))
    original_text = (
        "#usda 1.0\n(\n"
        f"    subLayers = [{ORIGINAL_TOKEN}]\n"
        ')\n\nover "Robot"\n{\n    float drive:angular:physics:stiffness = 80\n}\n'
    )
    (root / ORIGINAL).parent.mkdir(parents=True)
    (root / ORIGINAL).write_bytes(original_text.replace("\n", "\r\n").encode("utf-8"))
    portable_text = original_text.replace(ORIGINAL_TOKEN, PORTABLE_TOKEN)
    (root / PORTABLE).write_bytes(portable_text.replace("\n", "\r\n").encode("utf-8"))
    refresh_hash_list(root)
    return root


def test_valid_crlf_bundle_returns_hash_evidence_and_narrow_scope(project):
    audit = load_guard()
    result = audit(project)
    assert result == {
        "passed": True,
        "overlay_path": str((project / PORTABLE).resolve()),
        "binary_hashes": {
            path.as_posix(): digest((project / path).read_bytes()) for path in BINARY_PATHS
        },
        "manifest_sha256": digest((project / MANIFEST).read_bytes()),
        "source_hash_list_sha256": digest((project / HASH_LIST).read_bytes()),
        "original_overlay_sha256": digest((project / ORIGINAL).read_bytes()),
        "portable_overlay_sha256": digest((project / PORTABLE).read_bytes()),
        "portable_overlay_lf_sha256": digest(normalized_bytes(project / PORTABLE)),
        "scope": "provenance_only_not_runtime_or_behavior",
    }
    assert result["portable_overlay_sha256"] != result["portable_overlay_lf_sha256"]


def test_valid_mixed_newline_bundle_and_string_project_path(project):
    audit = load_guard()
    (project / PORTABLE).write_bytes(normalized_bytes(project / PORTABLE))
    assert audit(str(project))["passed"] is True


@pytest.mark.parametrize("relative", BINARY_PATHS)
def test_corrupt_binary_is_rejected(project, relative):
    audit = load_guard()
    (project / relative).write_bytes(b"different binary")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        audit(project)


@pytest.mark.parametrize("update_hash", [False, True])
def test_behavior_change_is_rejected_even_with_recomputed_overlay_hash(project, update_hash):
    audit = load_guard()
    overlay = project / PORTABLE
    overlay.write_bytes(normalized_bytes(overlay).replace(b"stiffness = 80", b"stiffness = 0"))
    if update_hash:
        refresh_hash_list(project)
    with pytest.raises(ValueError, match="overlay.*equivalent"):
        audit(project)


@pytest.mark.parametrize("relative", (*BINARY_PATHS, ORIGINAL, PORTABLE, MANIFEST, HASH_LIST))
def test_missing_required_file_fails_closed(project, relative):
    audit = load_guard()
    (project / relative).unlink()
    with pytest.raises(FileNotFoundError):
        audit(project)


@pytest.mark.parametrize(
    "m1",
    [
        {"source": "/untrusted/source", "entry": ENTRY},
        {"source": SOURCE, "entry": f"./{ENTRY}"},
        {"source": SOURCE, "entry": ENTRY, "extra": "unapproved"},
        {"source": SOURCE},
        None,
    ],
)
def test_source_manifest_requires_exact_m1_record(project, m1):
    audit = load_guard()
    (project / MANIFEST).write_text(json.dumps({"m1": m1}), encoding="utf-8")
    with pytest.raises(ValueError, match="m1.*source.*entry"):
        audit(project)


@pytest.mark.parametrize("same_digest", [True, False])
def test_duplicate_hash_record_is_rejected(project, same_digest):
    audit = load_guard()
    hash_path = project / HASH_LIST
    records = hash_path.read_text(encoding="utf-8")
    duplicate = records.splitlines()[0]
    if not same_digest:
        duplicate = "0" * 64 + duplicate[64:]
    hash_path.write_text(records + duplicate + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate.*hash"):
        audit(project)


@pytest.mark.parametrize("relative", (*BINARY_PATHS, PORTABLE))
def test_missing_required_hash_record_is_rejected(project, relative):
    audit = load_guard()
    hash_path = project / HASH_LIST
    records = hash_path.read_text(encoding="utf-8").splitlines()
    hash_path.write_text(
        "\n".join(line for line in records if not line.endswith(relative.as_posix())) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Missing.*hash"):
        audit(project)


def test_wrong_overlay_hash_is_rejected(project):
    audit = load_guard()
    hash_path = project / HASH_LIST
    records = hash_path.read_text(encoding="utf-8")
    correct_digest = digest(normalized_bytes(project / PORTABLE))
    hash_path.write_text(records.replace(correct_digest, "0" * 64), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        audit(project)


@pytest.mark.parametrize("token_count", [0, 2])
def test_original_requires_exactly_one_source_sublayer_token(project, token_count):
    audit = load_guard()
    original = project / ORIGINAL
    original.write_text(
        original.read_text(encoding="utf-8").replace(ORIGINAL_TOKEN, ORIGINAL_TOKEN * token_count),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly one"):
        audit(project)


def test_portable_sublayer_requires_dot_slash_even_with_updated_hash(project):
    audit = load_guard()
    overlay = project / PORTABLE
    overlay.write_text(
        overlay.read_text(encoding="utf-8").replace(PORTABLE_TOKEN, f"@{ENTRY}@"),
        encoding="utf-8",
    )
    refresh_hash_list(project)
    with pytest.raises(ValueError, match="overlay.*equivalent"):
        audit(project)


@pytest.mark.parametrize("record", ["invalid", "g" * 64 + "  assets/file.usd", "0" * 64 + "  "])
def test_malformed_hash_records_are_rejected(project, record):
    audit = load_guard()
    hash_path = project / HASH_LIST
    hash_path.write_text(hash_path.read_text(encoding="utf-8") + record + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed.*hash"):
        audit(project)
