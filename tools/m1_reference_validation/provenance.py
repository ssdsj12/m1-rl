"""Verify reference M1 file provenance without importing a simulator.

This checks the declared source, four M1 binaries, and the single permitted
overlay path relocation. It does not establish USD runtime dependency closure,
physical behavior, or authenticity beyond the supplied reference hash list.
"""

import hashlib
import json
from pathlib import Path


_SOURCE = "/home/xk/ros2_ws/src/zjs_m1_v3_description/urdf/ZJ_V3_URDF_V1_0"
_ENTRY = "m1/ZJ_V3_URDF_V1_0/configuration/ZJ_V3_URDF_V1_0_physics.usd"
_BUNDLE = Path("assets/m1_panda")
_BINARY_ROOT = _BUNDLE / "m1/ZJ_V3_URDF_V1_0"
_BINARIES = (
    _BINARY_ROOT / "ZJ_V3_URDF_V1_0.usd",
    _BINARY_ROOT / "configuration/ZJ_V3_URDF_V1_0_base.usd",
    _BINARY_ROOT / "configuration/ZJ_V3_URDF_V1_0_physics.usd",
    _BINARY_ROOT / "configuration/ZJ_V3_URDF_V1_0_sensor.usd",
)
_ORIGINAL_OVERLAY = Path("assets/m1_usd/ZJ_V3_URDF_V1_0_floating.usda")
_PORTABLE_OVERLAY = _BUNDLE / "m1_floating.usda"


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _utf8_text(data):
    """Decode with universal newlines while retaining raw bytes for evidence."""
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _parse_hash_list(data):
    records = {}
    for line_number, line in enumerate(_utf8_text(data).splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split(maxsplit=1)
        if (
            len(fields) != 2
            or len(fields[0]) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in fields[0])
        ):
            raise ValueError(f"Malformed SHA-256 hash record on line {line_number}")
        expected, name = fields
        # GNU sha256sum marks binary-mode records with a leading '*'.
        if name.startswith("*"):
            name = name[1:]
        if not name:
            raise ValueError(f"Malformed SHA-256 hash record on line {line_number}")
        if name in records:
            raise ValueError(f"Duplicate SHA-256 hash record for {name}")
        records[name] = expected.lower()
    return records


def _require_hash(records, relative_path, actual):
    name = relative_path.as_posix()
    if name not in records:
        raise ValueError(f"Missing SHA-256 hash record for {name}")
    if records[name] != actual:
        raise ValueError(f"SHA-256 mismatch for {name}: expected {records[name]}, got {actual}")


def audit_provenance(project):
    """Return provenance evidence for a reference Go2Pvcnn project directory.

    Missing/unreadable files raise OSError (including FileNotFoundError).
    Invalid UTF-8, malformed JSON, and failed provenance contracts raise
    ValueError or its subclasses. No success report is returned after failure.
    """
    project = Path(project).resolve(strict=True)
    manifest_bytes = (project / _BUNDLE / "source_manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("m1") != {
        "source": _SOURCE,
        "entry": _ENTRY,
    }:
        raise ValueError("Manifest m1 must contain exactly the approved source and entry")

    hash_list_bytes = (project / _BUNDLE / "source_files.sha256").read_bytes()
    records = _parse_hash_list(hash_list_bytes)
    binary_hashes = {}
    for relative_path in _BINARIES:
        actual = _sha256((project / relative_path).read_bytes())
        _require_hash(records, relative_path, actual)
        binary_hashes[relative_path.as_posix()] = actual

    original_bytes = (project / _ORIGINAL_OVERLAY).read_bytes()
    portable_path = project / _PORTABLE_OVERLAY
    portable_bytes = portable_path.read_bytes()
    original_text = _utf8_text(original_bytes)
    portable_text = _utf8_text(portable_bytes)
    original_token = f"@{_SOURCE}/configuration/ZJ_V3_URDF_V1_0_physics.usd@"
    if original_text.count(original_token) != 1:
        raise ValueError("Original overlay must contain exactly one approved source sublayer token")
    expected_text = original_text.replace(original_token, f"@./{_ENTRY}@", 1)
    if expected_text != portable_text:
        raise ValueError("Portable overlay is not equivalent to the original after path relocation")

    portable_lf_sha256 = _sha256(portable_text.encode("utf-8"))
    _require_hash(records, _PORTABLE_OVERLAY, portable_lf_sha256)
    return {
        "passed": True,
        "overlay_path": str(portable_path.resolve()),
        "binary_hashes": binary_hashes,
        "manifest_sha256": _sha256(manifest_bytes),
        "source_hash_list_sha256": _sha256(hash_list_bytes),
        "original_overlay_sha256": _sha256(original_bytes),
        "portable_overlay_sha256": _sha256(portable_bytes),
        "portable_overlay_lf_sha256": portable_lf_sha256,
        "scope": "provenance_only_not_runtime_or_behavior",
    }
