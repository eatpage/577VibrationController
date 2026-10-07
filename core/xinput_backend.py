"""XInput 后端 —— 设备枚举、连接检测、震动下发。适用于任何走 XInput 的 Xbox 协议手柄。

【为什么这个模块必须这么写】
XInputSetState 设置的是「状态」而不是「一次性指令」。然而绝大多数手柄固件
普遍内置震动看门狗：超过约 100ms 收不到新的震动指令，
就会自动把马达归零。这就是各种小工具「震一会儿自己就停了」的根本原因。

结论：调用方必须以 >=60Hz 的频率 **无条件重复下发**，哪怕数值完全没变。
本项目的 RumbleEngine 以 125Hz 重发，因此可以无限持续震动。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

# ---------------------------------------------------------------- 常量

ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167

MAX_CONTROLLERS = 4  # XInput 固定只有 4 个槽位

# XInputGetCapabilities 的 Flags 位
XINPUT_CAPS_FFB_SUPPORTED = 0x0001   # 支持力反馈（震动）
XINPUT_CAPS_WIRELESS = 0x0002
XINPUT_CAPS_VOICE_SUPPORTED = 0x0004
XINPUT_CAPS_PMD = 0x0008

# 优先使用 Win10 1809+ 的 xinput1_4.dll，逐级回退
_DLL_CANDIDATES = ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll")


# ---------------------------------------------------------------- 结构体


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ("wLeftMotorSpeed", wintypes.WORD),
        ("wRightMotorSpeed", wintypes.WORD),
    ]


class XINPUT_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("Type", ctypes.c_ubyte),
        ("SubType", ctypes.c_ubyte),
        ("Flags", wintypes.WORD),
        ("Gamepad", XINPUT_GAMEPAD),
        ("Vibration", XINPUT_VIBRATION),
    ]


# ---------------------------------------------------------------- 设备信息


@dataclass
class DeviceInfo:
    index: int
    connected: bool
    wireless: bool = False
    supports_ffb: bool = False
    name: str = ""

    @property
    def label(self) -> str:
        if not self.connected:
            return f"槽位 {self.index}　——　未连接"
        link = "无线" if self.wireless else "有线"
        ffb = "" if self.supports_ffb else "（无震动支持）"
        model = self.name or "Xbox 兼容手柄"
        return f"槽位 {self.index}　{model}　[{link}]{ffb}"


# ---------------------------------------------------------------- 后端


class XInputBackend:
    """对 xinput*.dll 的薄封装。所有方法都不抛异常，失败时返回中性值。"""

    def __init__(self) -> None:
        self.dll = None
        self.dll_name = ""
        self.load_error = ""
        self._load()

    # -- 初始化 ------------------------------------------------

    def _load(self) -> None:
        last_err = ""
        for name in _DLL_CANDIDATES:
            try:
                dll = ctypes.WinDLL(name)
            except OSError as exc:  # DLL 不存在
                last_err = f"{name}: {exc}"
                continue

            try:
                dll.XInputGetState.argtypes = [
                    wintypes.DWORD,
                    ctypes.POINTER(XINPUT_STATE),
                ]
                dll.XInputGetState.restype = wintypes.DWORD

                dll.XInputSetState.argtypes = [
                    wintypes.DWORD,
                    ctypes.POINTER(XINPUT_VIBRATION),
                ]
                dll.XInputSetState.restype = wintypes.DWORD

                dll.XInputGetCapabilities.argtypes = [
                    wintypes.DWORD,
                    wintypes.DWORD,
                    ctypes.POINTER(XINPUT_CAPABILITIES),
                ]
                dll.XInputGetCapabilities.restype = wintypes.DWORD
            except AttributeError as exc:
                last_err = f"{name}: 缺少导出函数 {exc}"
                continue

            self.dll = dll
            self.dll_name = name
            return

        self.load_error = last_err or "未找到可用的 xinput DLL"

    @property
    def available(self) -> bool:
        return self.dll is not None

    # -- 查询 --------------------------------------------------

    def is_connected(self, index: int) -> bool:
        if self.dll is None or not (0 <= index < MAX_CONTROLLERS):
            return False
        state = XINPUT_STATE()
        return self.dll.XInputGetState(index, ctypes.byref(state)) == ERROR_SUCCESS

    def capabilities(self, index: int) -> XINPUT_CAPABILITIES | None:
        if self.dll is None or not (0 <= index < MAX_CONTROLLERS):
            return None
        caps = XINPUT_CAPABILITIES()
        rc = self.dll.XInputGetCapabilities(index, 0x00000000, ctypes.byref(caps))
        if rc != ERROR_SUCCESS:
            return None
        return caps

    def probe(self, index: int) -> DeviceInfo:
        if not self.is_connected(index):
            return DeviceInfo(index=index, connected=False)
        caps = self.capabilities(index)
        if caps is None:
            return DeviceInfo(index=index, connected=True, supports_ffb=True, name="Xbox 兼容手柄")
        return DeviceInfo(
            index=index,
            connected=True,
            wireless=bool(caps.Flags & XINPUT_CAPS_WIRELESS),
            supports_ffb=bool(caps.Flags & XINPUT_CAPS_FFB_SUPPORTED),
            name="Xbox 兼容手柄",
        )

    def enumerate(self) -> list[DeviceInfo]:
        return [self.probe(i) for i in range(MAX_CONTROLLERS)]

    # -- 控制 --------------------------------------------------

    def set_vibration(self, index: int, left: int, right: int) -> bool:
        """left/right 取值 0~65535。返回 False 表示设备不可用。"""
        if self.dll is None or not (0 <= index < MAX_CONTROLLERS):
            return False
        vib = XINPUT_VIBRATION(
            wLeftMotorSpeed=max(0, min(65535, int(left))),
            wRightMotorSpeed=max(0, min(65535, int(right))),
        )
        rc = self.dll.XInputSetState(index, ctypes.byref(vib))
        return rc == ERROR_SUCCESS

    def stop(self, index: int, repeats: int = 3) -> None:
        """强制归零。多次下发以确保手柄固件确实收到（退出时必须调用）。"""
        for _ in range(repeats):
            self.set_vibration(index, 0, 0)


# 模块级单例，避免重复加载 DLL
_backend: XInputBackend | None = None


def get_backend() -> XInputBackend:
    global _backend
    if _backend is None:
        _backend = XInputBackend()
    return _backend
