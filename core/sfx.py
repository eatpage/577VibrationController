"""界面音效 —— 用 winsound 从内存播放，不落任何文件。

音效在启动时用 numpy 合成成 WAV 字节流缓存在内存里，
播放走 `winsound.PlaySound(bytes, SND_MEMORY | SND_ASYNC)`。
零依赖（winsound 是 Python 标准库）、零磁盘文件、不干扰主音频流。
"""

from __future__ import annotations

import io
import math
import threading
import wave

import numpy as np

try:
    import winsound
    _HAS_WINSOUND = True
except Exception:  # pragma: no cover - 非 Windows
    winsound = None
    _HAS_WINSOUND = False

SR = 44100

# 音效配方：名称 -> (起始频率, 结束频率, 时长秒, 波形, 衰减指数)
RECIPES: dict[str, tuple[float, float, float, str, float]] = {
    "click":     (900.0, 1500.0, 0.045, "sine", 9.0),
    "wave":      (1300.0, 2100.0, 0.038, "sine", 11.0),
    "tick":      (2100.0, 2100.0, 0.014, "sine", 16.0),
    "on":        (520.0, 1180.0, 0.110, "sine", 3.6),
    "off":       (1080.0, 430.0, 0.110, "sine", 3.6),
    "random":    (700.0, 1900.0, 0.130, "triangle", 4.0),
    "listen_on": (300.0, 900.0, 0.230, "sine", 2.2),
    "listen_off":(900.0, 260.0, 0.200, "sine", 2.6),
}


def _wave_form(phase: np.ndarray, kind: str) -> np.ndarray:
    if kind == "triangle":
        return 2.0 * np.abs(2.0 * ((phase / (2.0 * np.pi)) % 1.0) - 1.0) - 1.0
    return np.sin(phase)


def render(name: str, volume: float = 0.5) -> bytes:
    """把一个配方渲染成完整的 WAV 字节流。"""
    f0, f1, dur, kind, decay = RECIPES[name]
    n = max(8, int(SR * dur))
    t = np.linspace(0.0, dur, n, endpoint=False, dtype=np.float64)

    freq = f0 + (f1 - f0) * (t / dur)
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    signal = _wave_form(phase, kind)

    # 指数衰减包络 + 2ms 淡入，消除起始爆音
    env = np.exp(-decay * t / dur)
    fade = max(1, int(SR * 0.002))
    env[:fade] *= np.linspace(0.0, 1.0, fade)

    amp = 0.55 * float(np.clip(volume, 0.0, 1.0))
    samples = np.clip(signal * env * amp, -1.0, 1.0)
    pcm = (samples * 32767.0).astype("<i2")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(pcm.tobytes())
    return buf.getvalue()


class SfxPlayer:
    """线程安全的音效播放器。渲染结果按 (音效名, 音量档) 缓存。"""

    def __init__(self, enabled: bool = True, volume: float = 0.45) -> None:
        self.enabled = enabled
        self._volume = volume
        self._cache: dict[tuple[str, int], bytes] = {}
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return _HAS_WINSOUND

    def set_volume(self, value: float) -> None:
        self._volume = float(np.clip(value, 0.0, 1.0))
        with self._lock:
            self._cache.clear()

    def volume(self) -> float:
        return self._volume

    def _data(self, name: str) -> bytes | None:
        if name not in RECIPES:
            return None
        bucket = int(round(self._volume * 10))
        key = (name, bucket)
        with self._lock:
            hit = self._cache.get(key)
            if hit is None:
                try:
                    hit = render(name, bucket / 10.0)
                except Exception:
                    return None
                self._cache[key] = hit
            return hit

    def play(self, name: str) -> None:
        if not (self.enabled and _HAS_WINSOUND) or self._volume <= 0.001:
            return
        data = self._data(name)
        if not data:
            return
        try:
            winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            pass

    def preload(self) -> None:
        """启动时预热缓存，避免第一次点击卡顿。"""
        for name in RECIPES:
            self._data(name)


_player: SfxPlayer | None = None


def player() -> SfxPlayer:
    global _player
    if _player is None:
        _player = SfxPlayer()
    return _player
