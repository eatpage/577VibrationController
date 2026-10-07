"""音频后端 —— WASAPI Loopback 采集 + 立体声波束播放。

技术选型：`pyaudiowpatch`（PyAudioWPatch）。它原生支持 WASAPI Loopback，
不仅能抓系统回放，还能同库做输出流，一个依赖搞定两件事。

分频策略（按马达物理特性来分，不是随便切的）：
    · 低频 20~120Hz   → 左马达（大偏心质量，擅长出低频强震）
    · 中频 120~900Hz  → 右马达（小偏心质量，擅长出高频细震）
    · 高频 900~4kHz   → 右马达（额外加权，负责「沙沙」的细节感）

无音频设备 / 无权限时全部优雅降级，不抛异常，调用方看 `available` 即可。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

try:
    import pyaudiowpatch as pyaudio
    _PYAUDIO_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover
    pyaudio = None
    _PYAUDIO_IMPORT_ERROR = str(exc)

FFT_SIZE = 4096
BLOCK_FRAMES = 1024

# 频段划分（Hz）
BASS_RANGE = (20.0, 120.0)
MID_RANGE = (120.0, 900.0)
HIGH_RANGE = (900.0, 4000.0)


# ==================================================================== 数据结构


@dataclass
class LoopbackDevice:
    index: int
    name: str
    samplerate: int
    channels: int

    @property
    def label(self) -> str:
        short = self.name.replace(" [Loopback]", "")
        return f"{short}　({self.samplerate}Hz)"


@dataclass
class OutputDevice:
    index: int
    name: str
    samplerate: int
    channels: int

    @property
    def label(self) -> str:
        return f"{self.name}　({self.samplerate}Hz)"


@dataclass
class AudioState:
    """采集线程发布的实时状态，UI 直接读。"""

    bass: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    level: float = 0.0
    raw_bass: float = 0.0
    raw_mid: float = 0.0
    raw_high: float = 0.0
    capturing: bool = False
    error: str = ""


# ==================================================================== 音频中心


class AudioHub:
    """持有唯一的 PyAudio 实例并做设备枚举。"""

    _instance: Optional["AudioHub"] = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.pa = None
        self.error = ""
        self._init()

    @classmethod
    def instance(cls) -> "AudioHub":
        if cls._instance is None:
            cls._instance = AudioHub()
        return cls._instance

    def _init(self) -> None:
        if pyaudio is None:
            self.error = f"未安装 pyaudiowpatch：{_PYAUDIO_IMPORT_ERROR}"
            return
        try:
            self.pa = pyaudio.PyAudio()
        except Exception as exc:
            self.pa = None
            self.error = f"音频子系统初始化失败：{exc}"

    @property
    def available(self) -> bool:
        return self.pa is not None

    # ---------------------------------------------------------- 设备枚举

    def default_output(self) -> Optional[OutputDevice]:
        if self.pa is None:
            return None
        try:
            info = self.pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            dev = self.pa.get_device_info_by_index(info["defaultOutputDevice"])
            return OutputDevice(
                index=int(dev["index"]),
                name=str(dev["name"]),
                samplerate=int(dev["defaultSampleRate"]),
                channels=int(dev["maxOutputChannels"]),
            )
        except Exception:
            return None

    def list_loopback_devices(self) -> list[LoopbackDevice]:
        """列出所有 WASAPI Loopback 设备，默认输出设备的 loopback 排最前。"""
        if self.pa is None:
            return []
        found: list[LoopbackDevice] = []
        try:
            for lb in self.pa.get_loopback_device_info_generator():
                found.append(
                    LoopbackDevice(
                        index=int(lb["index"]),
                        name=str(lb["name"]),
                        samplerate=int(lb["defaultSampleRate"]),
                        channels=int(lb["maxInputChannels"]),
                    )
                )
        except Exception:
            return []

        default_out = self.default_output()
        if default_out is not None:
            for i, dev in enumerate(found):
                if default_out.name in dev.name:
                    found.insert(0, found.pop(i))
                    break
        return found

    def find_loopback_for(self, output_name: str) -> Optional[LoopbackDevice]:
        for dev in self.list_loopback_devices():
            if output_name in dev.name:
                return dev
        return None

    def terminate(self) -> None:
        with self._lock:
            if self.pa is not None:
                try:
                    self.pa.terminate()
                except Exception:
                    pass
                self.pa = None


# ==================================================================== 采集


class LoopbackCapture:
    """后台线程抓系统回放音频 → FFT 分频段能量。"""

    def __init__(self, device_index: Optional[int] = None) -> None:
        self.hub = AudioHub.instance()
        self.device_index = device_index
        self.state = AudioState()

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._stream = None

        self._attack = 0.55
        self._release = 0.10
        self.sensitivity = 2.2
        self.noise_floor = 0.012

        # 需要在分频计算时挖掉的频段 —— 用于切断「聆听波束」自己造成的回授回路
        self.exclude_ranges: list[tuple[float, float]] = []

        # 波段平滑后的值（包络跟随）
        self._env = np.zeros(3, dtype=np.float32)

    # ---------------------------------------------------------- 控制

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, device_index: Optional[int] = None) -> bool:
        if self.running:
            return True
        if not self.hub.available:
            self.state.error = self.hub.error or "音频不可用"
            return False

        if device_index is not None:
            self.device_index = device_index
        if self.device_index is None:
            out = self.hub.default_output()
            lb = self.hub.find_loopback_for(out.name) if out else None
            if lb is None:
                devices = self.hub.list_loopback_devices()
                if not devices:
                    self.state.error = "找不到任何 Loopback 录音设备"
                    return False
                lb = devices[0]
            self.device_index = lb.index

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="loopback-capture", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        self.state.capturing = False

    # ---------------------------------------------------------- 主循环

    def _loop(self) -> None:
        hub = self.hub
        stream = None
        try:
            info = hub.pa.get_device_info_by_index(self.device_index)
            sr = int(info["defaultSampleRate"])
            ch = min(2, int(info["maxInputChannels"])) or 1

            stream = hub.pa.open(
                format=pyaudio.paFloat32,
                channels=ch,
                rate=sr,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=BLOCK_FRAMES,
            )
            self._stream = stream
            self.state.capturing = True
            self.state.error = ""

            window = np.hanning(FFT_SIZE).astype(np.float32)
            freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / sr)
            masks = [
                _band_mask(freqs, *BASS_RANGE),
                _band_mask(freqs, *MID_RANGE),
                _band_mask(freqs, *HIGH_RANGE),
            ]

            history = [np.zeros(0, dtype=np.float32)] * (FFT_SIZE // BLOCK_FRAMES)
            idx = 0

            while not self._stop.is_set():
                try:
                    raw = stream.read(BLOCK_FRAMES, exception_on_overflow=False)
                except Exception:
                    time.sleep(0.02)
                    continue

                block = np.frombuffer(raw, dtype=np.float32)
                if ch > 1 and block.size >= ch:
                    block = block.reshape(-1, ch).mean(axis=1)
                else:
                    block = block.copy()

                history[idx % len(history)] = block
                idx += 1
                if idx < len(history):
                    continue

                frame = np.concatenate(history)
                if frame.size < FFT_SIZE:
                    frame = np.pad(frame, (FFT_SIZE - frame.size, 0))
                else:
                    frame = frame[-FFT_SIZE:]

                mono = frame * window
                spec = np.abs(np.fft.rfft(mono))
                # 幅度归一化（Hann 相干增益 0.5）→ 近似的 RMS 尺度
                spec = spec / (FFT_SIZE * 0.5)

                # 挖掉指定频段（斩断自激回授）
                for lo, hi in self.exclude_ranges:
                    spec[(freqs >= lo) & (freqs < hi)] = 0.0

                raw_bands = []
                for mask in masks:
                    power = float(np.sum(spec[mask] ** 2)) * 0.5
                    raw_bands.append(float(np.sqrt(power)) * 2.0)

                raw_bands = np.asarray(raw_bands, dtype=np.float32)
                # 扣掉底噪再乘灵敏度
                scaled = np.clip((raw_bands - self.noise_floor) * self.sensitivity, 0.0, 4.0)

                for k in range(3):
                    coef = self._attack if scaled[k] > self._env[k] else self._release
                    self._env[k] += (scaled[k] - self._env[k]) * coef

                self.state.raw_bass = float(raw_bands[0])
                self.state.raw_mid = float(raw_bands[1])
                self.state.raw_high = float(raw_bands[2])
                self.state.bass = float(min(1.0, self._env[0]))
                self.state.mid = float(min(1.0, self._env[1]))
                self.state.high = float(min(1.0, self._env[2]))
                self.state.level = float(min(1.0, max(self.state.bass, self.state.mid)))

        except Exception as exc:
            self.state.error = f"采集失败：{exc}"
            self.state.capturing = False
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            self._stream = None
            self.state.capturing = False


def _band_mask(freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (freqs >= lo) & (freqs < hi)


# ==================================================================== 波束播放


TIMBRES = {
    "rumble": ("马达嗡鸣", 58.0, "sine"),
    "sub":    ("超低潜行", 36.0, "sine"),
    "buzz":   ("蜂鸣", 168.0, "saw"),
    "grain":  ("颗粒摩擦", 0.0, "noise"),
}


class StereoBeamPlayer:
    """把引擎的 (左包络, 右包络) 实时渲染成立体声播放出来。

    左马达的包络 → 左声道，右马达的包络 → 右声道。
    这样波束扫到哪边，声音就偏向哪边 —— 用耳朵直接「听」波束的位置。
    """

    def __init__(self, device_index: Optional[int] = None, timbre: str = "rumble") -> None:
        self.hub = AudioHub.instance()
        self.device_index = device_index
        self.timbre = timbre if timbre in TIMBRES else "rumble"
        self.volume = 0.55

        self._env = np.zeros(2, dtype=np.float32)   # 引擎给的目标
        self._lock = threading.Lock()
        self._phase = 0.0
        self._noise_state = np.zeros(3, dtype=np.float32)

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._stream = None

        self.level = (0.0, 0.0)     # 实际输出电平，给 UI 用
        self.error = ""
        self._sr = 44100

    # ---------------------------------------------------------- 控制

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def set_envelope(self, left: float, right: float) -> None:
        with self._lock:
            self._env[0] = float(min(1.0, max(0.0, left)))
            self._env[1] = float(min(1.0, max(0.0, right)))

    def set_timbre(self, key: str) -> None:
        if key in TIMBRES:
            self.timbre = key

    def start(self, device_index: Optional[int] = None) -> bool:
        if self.running:
            return True
        if not self.hub.available:
            self.error = self.hub.error or "音频不可用"
            return False

        if device_index is not None:
            self.device_index = device_index
        out = self.hub.default_output()
        if self.device_index is None:
            if out is None:
                self.error = "找不到可用的输出设备"
                return False
            self.device_index = out.index

        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="beam-player", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None

    # ---------------------------------------------------------- 主循环

    def _loop(self) -> None:
        hub = self.hub
        stream = None
        block = 1024
        try:
            info = hub.pa.get_device_info_by_index(self.device_index)
            sr = int(info["defaultSampleRate"])
            self._sr = sr
            channels = 2 if int(info["maxOutputChannels"]) >= 2 else 1

            stream = hub.pa.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=sr,
                output=True,
                output_device_index=self.device_index,
                frames_per_buffer=block,
            )
            self._stream = stream
            self.error = ""

            cur = np.zeros(2, dtype=np.float32)
            t_axis = np.arange(block, dtype=np.float32)

            while not self._stop.is_set():
                with self._lock:
                    target = self._env.copy()

                # 逐样本线性插值，避免音频出现台阶噪声
                ramp = np.linspace(cur[0], target[0], block, dtype=np.float32)
                ramp_r = np.linspace(cur[1], target[1], block, dtype=np.float32)
                cur = target

                name, freq, kind = TIMBRES[self.timbre]
                if kind == "noise":
                    white = np.random.uniform(-1.0, 1.0, block).astype(np.float32)
                    # 4 抽头滑动平均，把白噪塑成「摩擦」质感（向量化，不进 Python 循环）
                    kernel = np.ones(4, dtype=np.float32) / 4.0
                    pads = np.concatenate([self._noise_state, white])
                    out = np.convolve(pads, kernel, mode="same")[len(self._noise_state):]
                    self._noise_state = white[-3:].copy()
                    carrier = (out * 3.4).astype(np.float32)
                else:
                    omega = 2.0 * np.pi * freq / sr
                    phases = self._phase + omega * t_axis
                    self._phase = float((self._phase + omega * block) % (2.0 * np.pi))
                    carrier = np.sin(phases)
                    if kind == "saw":
                        carrier = 2.0 * ((phases / (2.0 * np.pi)) % 1.0) - 1.0
                    carrier = carrier.astype(np.float32)

                left = carrier * ramp * self.volume
                right = carrier * ramp_r * self.volume
                np.clip(left, -1.0, 1.0, out=left)
                np.clip(right, -1.0, 1.0, out=right)

                self.level = (float(np.abs(left).max()), float(np.abs(right).max()))

                if channels == 2:
                    data = np.stack([left, right], axis=1).ravel()
                else:
                    data = (left + right) * 0.5
                stream.write(data.astype(np.float32).tobytes())

        except Exception as exc:
            self.error = f"播放失败：{exc}"
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            self._stream = None
            self.level = (0.0, 0.0)
