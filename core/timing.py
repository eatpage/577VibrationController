"""计时精度工具。

Windows 默认的系统计时器精度是 15.6ms，直接 time.sleep(1/125) 实际只会
睡到 ~15.6ms（约 64Hz），达不到 125Hz 的震动刷新率。
调用 timeBeginPeriod(1) 可以把系统计时器精度提到 1ms。
"""

from __future__ import annotations

import ctypes
import time


class TimerResolution:
    """上下文管理器：进程存活期间提升系统计时精度。"""

    def __init__(self, milliseconds: int = 1) -> None:
        self.milliseconds = milliseconds
        self._winmm = None
        self._active = False

    def __enter__(self) -> "TimerResolution":
        try:
            winmm = ctypes.WinDLL("winmm.dll")
            winmm.timeBeginPeriod.argtypes = [ctypes.c_uint]
            winmm.timeBeginPeriod.restype = ctypes.c_uint
            winmm.timeEndPeriod.argtypes = [ctypes.c_uint]
            winmm.timeEndPeriod.restype = ctypes.c_uint
            winmm.timeBeginPeriod(self.milliseconds)
            self._winmm = winmm
            self._active = True
        except Exception:
            self._winmm = None
            self._active = False
        return self

    def __exit__(self, *_exc) -> None:
        if self._winmm is not None and self._active:
            try:
                self._winmm.timeEndPeriod(self.milliseconds)
            except Exception:
                pass
            self._active = False


def precise_sleep_until(target: float) -> None:
    """睡到 perf_counter() >= target。

    策略：先用 sleep 睡掉大部分，最后 1.5ms 用忙等收尾，
    兼顾低 CPU 占用与节拍精度。
    """
    while True:
        remaining = target - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > 0.0010:
            time.sleep(remaining - 0.0010)
        else:
            # 忙等收尾
            while time.perf_counter() < target:
                pass
            return
