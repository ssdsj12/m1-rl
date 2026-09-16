import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "vulkan" / "nvidia_egl_icd.json"
PROBE = ROOT / "scripts" / "probe_isaac_vulkan.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("probe_isaac_vulkan", PROBE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_selects_the_headless_nvidia_egl_icd():
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == {
        "file_format_version": "1.0.1",
        "ICD": {
            "library_path": "libEGL_nvidia.so.0",
            "api_version": "1.4.303",
        },
    }


def test_resolve_loader_requires_exactly_one_gpu_foundation_loader(tmp_path):
    probe = _load_probe()
    with pytest.raises(RuntimeError, match="exactly one"):
        probe.resolve_loader(tmp_path)

    first = (
        tmp_path
        / "lib/python3.10/site-packages/isaacsim/extscache"
        / "omni.gpu_foundation-one/bin/deps/libvulkan.so.1"
    )
    first.parent.mkdir(parents=True)
    first.touch()
    assert probe.resolve_loader(tmp_path) == first.resolve()

    second = (
        tmp_path
        / "lib/python3.10/site-packages/isaacsim/extscache"
        / "omni.gpu_foundation-two/bin/deps/libvulkan.so.1"
    )
    second.parent.mkdir(parents=True)
    second.touch()
    with pytest.raises(RuntimeError, match="exactly one"):
        probe.resolve_loader(tmp_path)


class _FakeFunction:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


class _FakeVulkan:
    def __init__(self, *, create_result=0, enumerate_result=0, device_count=8):
        self.destroyed = []

        def create(_create_info, _allocator, instance_out):
            if create_result == 0:
                instance_out._obj.value = 0xCAFE
            return create_result

        def enumerate_devices(_instance, count_out, _devices):
            count_out._obj.value = device_count
            return enumerate_result

        def destroy(instance, _allocator):
            self.destroyed.append(instance.value)

        self.vkCreateInstance = _FakeFunction(create)
        self.vkEnumeratePhysicalDevices = _FakeFunction(enumerate_devices)
        self.vkDestroyInstance = _FakeFunction(destroy)


def test_probe_counts_devices_and_always_destroys_a_created_instance(monkeypatch):
    probe = _load_probe()
    library = _FakeVulkan(device_count=8)
    monkeypatch.setattr(probe.ctypes, "CDLL", lambda _path: library)

    assert probe.probe_vulkan(Path("/fake/libvulkan.so.1")) == 8
    assert library.destroyed == [0xCAFE]


def test_probe_reports_create_failure_without_destroying(monkeypatch):
    probe = _load_probe()
    library = _FakeVulkan(create_result=-9)
    monkeypatch.setattr(probe.ctypes, "CDLL", lambda _path: library)

    with pytest.raises(probe.VulkanCallError) as error:
        probe.probe_vulkan(Path("/fake/libvulkan.so.1"))

    assert error.value.operation == "vkCreateInstance"
    assert error.value.result == -9
    assert library.destroyed == []


def test_probe_destroys_instance_when_enumeration_fails(monkeypatch):
    probe = _load_probe()
    library = _FakeVulkan(enumerate_result=-3)
    monkeypatch.setattr(probe.ctypes, "CDLL", lambda _path: library)

    with pytest.raises(probe.VulkanCallError) as error:
        probe.probe_vulkan(Path("/fake/libvulkan.so.1"))

    assert error.value.operation == "vkEnumeratePhysicalDevices"
    assert error.value.result == -3
    assert library.destroyed == [0xCAFE]
