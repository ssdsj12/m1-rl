#!/usr/bin/env python3
"""Probe Isaac Sim's bundled Vulkan loader with the selected driver ICD."""

from __future__ import annotations

import argparse
import ctypes
from pathlib import Path
import sys


VK_SUCCESS = 0
VK_STRUCTURE_TYPE_APPLICATION_INFO = 0
VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO = 1
VK_API_VERSION_1_1 = (1 << 22) | (1 << 12)


class VkApplicationInfo(ctypes.Structure):
    _fields_ = (
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("pApplicationName", ctypes.c_char_p),
        ("applicationVersion", ctypes.c_uint32),
        ("pEngineName", ctypes.c_char_p),
        ("engineVersion", ctypes.c_uint32),
        ("apiVersion", ctypes.c_uint32),
    )


class VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = (
        ("sType", ctypes.c_uint32),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("pApplicationInfo", ctypes.POINTER(VkApplicationInfo)),
        ("enabledLayerCount", ctypes.c_uint32),
        ("ppEnabledLayerNames", ctypes.POINTER(ctypes.c_char_p)),
        ("enabledExtensionCount", ctypes.c_uint32),
        ("ppEnabledExtensionNames", ctypes.POINTER(ctypes.c_char_p)),
    )


class VulkanCallError(RuntimeError):
    def __init__(self, operation: str, result: int):
        super().__init__(f"{operation} failed with VkResult {result}")
        self.operation = operation
        self.result = result


def resolve_loader(prefix: Path) -> Path:
    pattern = (
        "lib/python3.10/site-packages/isaacsim/extscache/"
        "omni.gpu_foundation-*/bin/deps/libvulkan.so.1"
    )
    matches = sorted(path.resolve() for path in prefix.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one Isaac Vulkan loader under {prefix}, found {len(matches)}"
        )
    return matches[0]


def probe_vulkan(loader: Path) -> int:
    vulkan = ctypes.CDLL(str(loader))
    create_instance = vulkan.vkCreateInstance
    create_instance.argtypes = (
        ctypes.POINTER(VkInstanceCreateInfo),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    )
    create_instance.restype = ctypes.c_int32

    enumerate_devices = vulkan.vkEnumeratePhysicalDevices
    enumerate_devices.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
    )
    enumerate_devices.restype = ctypes.c_int32

    destroy_instance = vulkan.vkDestroyInstance
    destroy_instance.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    destroy_instance.restype = None

    application_info = VkApplicationInfo(
        sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,
        pApplicationName=b"m1-ame-vulkan-probe",
        applicationVersion=1,
        pEngineName=b"none",
        engineVersion=1,
        apiVersion=VK_API_VERSION_1_1,
    )
    create_info = VkInstanceCreateInfo(
        sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        pApplicationInfo=ctypes.pointer(application_info),
    )
    instance = ctypes.c_void_p()
    create_result = int(
        create_instance(ctypes.byref(create_info), None, ctypes.byref(instance))
    )
    if create_result != VK_SUCCESS:
        raise VulkanCallError("vkCreateInstance", create_result)

    try:
        device_count = ctypes.c_uint32()
        enumerate_result = int(
            enumerate_devices(instance, ctypes.byref(device_count), None)
        )
        if enumerate_result != VK_SUCCESS:
            raise VulkanCallError("vkEnumeratePhysicalDevices", enumerate_result)
        return int(device_count.value)
    finally:
        destroy_instance(instance, None)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path(sys.prefix))
    parser.add_argument("--loader", type=Path)
    parser.add_argument("--expect-device-count", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        loader = args.loader.resolve() if args.loader else resolve_loader(args.prefix)
        print(f"loader={loader}", flush=True)
        device_count = probe_vulkan(loader)
    except VulkanCallError as error:
        print(f"{error.operation}={error.result}", flush=True)
        return 1
    except (OSError, RuntimeError) as error:
        print(f"vulkan_probe_error={error}", file=sys.stderr, flush=True)
        return 2

    print("vkCreateInstance=0", flush=True)
    print(f"physical_device_count={device_count}", flush=True)
    if (
        args.expect_device_count is not None
        and device_count != args.expect_device_count
    ):
        print(
            f"expected_device_count={args.expect_device_count}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
