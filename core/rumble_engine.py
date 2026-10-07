"""震动引擎 —— 把波形变成持续不断的马达指令。

设计要点：
1. 独立线程，默认 125Hz。**每个 tick 都无条件调用 XInputSetState**，
   这是绕开手柄固件震动看门狗、实现「无限持续震动」的核心。
2. 用 perf_counter 累加式定时并补偿漂移，而不是裸 sleep。
3. 每次 tick 顺带查询连接状态，断线自动重连，不打断用户操作。
4. 波束（声像 / 拍频 / 同相聚合）在这里合成，左右马达一起算。
5. 音频跟随模式：把系统回放的低频/中频能量当作波形源。
6. 每帧把 (左, 右) 包络推给 frame_sink —— 立体声播放器从这里拿数据，
   于是「波束扫到哪边，声音就偏哪边」。
"""

from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from . import xinput_backend
from .beam import BeamParams, BeamProcessor, clamp01
from .timing import TimerResolution, precise_sleep_until
from .waveforms import DEFAULT_CURVE, WAVEFORMS, eval_curve

MAX_RAW = 65535

# 音源模式
SOURCE_WAVEFORM = "waveform"   # 只放波形
SOURCE_AUDIO = "audio"         # 只跟音频
SOURCE_MIX = "mix"             # 波形被音频调制


@dataclass
class EngineParams:
    # ---- 强度 ----
    master: float = 0.80
    left_gain: float = 1.00
    right_gain: float = 1.00

    # ---- 波形 ----
    waveform: str = "breath"
    waveform_b: str = ""          # 混合用的第二波形（空 = 不混合）
    mix: float = 0.0              # 0 = 纯 A，1 = 纯 B
    speed: float = 1.00
    floor: float = 0.00
    smoothing: float = 0.15
    phase_shift: float = 0.00
    curve_points: tuple[tuple[float, float], ...] = field(
        default_factory=lambda: tuple(DEFAULT_CURVE)
    )
    curve_duration: float = 4.0

    # ---- 波束 ----
    beam_enabled: bool = False
    beam_position: float = 0.0
    beam_width: float = 0.45
    beam_sweep: bool = False
    beam_sweep_rate: float = 0.5
    beam_sweep_depth: float = 0.85
    beam_beat_hz: float = 0.0
    beam_beat_depth: float = 0.75
    beam_polarity: str = "in"

    # ---- 音频跟随 ----
    source: str = SOURCE_WAVEFORM
    audio_gain_l: float = 1.0     # 低频 -> 左马达（大）
    audio_gain_r: float = 1.0     # 中高频 -> 右马达（小）
    audio_threshold: float = 0.04

    # ---- 体感增强 ----
    # 起停锐化：ERM 有 15~30ms 的启停迟滞，上升沿给 1~2 个 tick 满功率「冲击」
    # 冲过静摩擦，下降沿不跟平滑直接瞬切，让脉冲变脆。
    # （微软在 Xbox 手柄里就是用电压冲击 + H 桥制动做这件事的）
    sharpen: float = 0.0
    # 随机共振底噪：叠加一层低于感知阈值的随机微震。文献表明
    # 适当强度的触觉噪声能提高对阈下信号的检出率（stochastic resonance）。
    noise_floor: float = 0.0
    # 反适应漂移：恒定振动持续 2~5 秒后会被感知适应（「震麻了」）。
    # 叠加一层极慢的随机游走，让信号永不真正静止。
    anti_adapt: float = 0.0
    # 占空比：压缩脉冲宽度。占空比在触觉文献里是与频率、强度并列的独立情绪维度。
    duty: float = 1.0

    def beam_params(self) -> BeamParams:
        return BeamParams(
            enabled=self.beam_enabled,
            position=self.beam_position,
            width=self.beam_width,
            sweep_enabled=self.beam_sweep,
            sweep_rate=self.beam_sweep_rate,
            sweep_depth=self.beam_sweep_depth,
            beat_hz=self.beam_beat_hz,
            beat_depth=self.beam_beat_depth,
            polarity=self.beam_polarity,
        )


class RumbleEngine:
    """线程安全的震动引擎。UI 侧只调用公开方法，不要直接碰私有字段。"""

    FALLBACK_KEY = "breath"

    def __init__(self, tick_hz: int = 125, history: int = 600) -> None:
        self.tick_hz = tick_hz
        self._lock = threading.Lock()
        self._params = EngineParams()
        self._device = 0
        self._running = False
        self._stop_flag = threading.Event()
        self._wake = threading.Event()      # 空闲时被打断用，避免启动延迟
        self._thread: Optional[threading.Thread] = None

        self._phase = 0.0
        self._env_l = 0.0
        self._env_r = 0.0
        self._release_ticks = 0
        self._prev_time = 0.0
        self._clock = 0.0            # 引擎内部累计时间，供拍频用
        self._beam = BeamProcessor()

        # 体感增强的状态
        self._prev_target_l = 0.0
        self._prev_target_r = 0.0
        self._kick_l = 0             # 上升沿冲击剩余 tick 数
        self._kick_r = 0
        self._cut_l = 0              # 下降沿瞬切剩余 tick 数
        self._cut_r = 0
        self._noise_a = 0.0          # 随机共振噪声的整形状态
        self._noise_b = 0.0
        self._drift = 0.0            # 反适应随机游走

        # 音频能量提供者：返回 (低音, 中高音)，由 UI 注入
        self.audio_provider: Optional[Callable[[], tuple[float, float]]] = None
        # 每帧输出回调（左包络, 右包络），喂给立体声播放器
        self.frame_sink: Optional[Callable[[float, float], None]] = None
        # 干跑模式：不发 XInput 指令、假装设备已连接。
        # 用于无手柄时预览波形 / 试听波束，以及自动化测试。
        self.dry_run = False

        # ---- 对外只读状态 ----
        self.connected = False
        self.left_raw = 0
        self.right_raw = 0
        self.device = 0
        self.measured_hz = 0.0
        self.phase_value = 0.0
        self.beam_position = 0.0
        self.env_l = 0.0
        self.env_r = 0.0
        self.audio_bass = 0.0
        self.audio_mid = 0.0
        self.last_error = ""
        self.history: deque[tuple[float, float]] = deque(maxlen=history)

    # ---------------------------------------------------------- 生命周期

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._loop, name="rumble-engine", daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        backend = xinput_backend.get_backend()
        backend.stop(self.device, repeats=5)
        self.left_raw = self.right_raw = 0
        self.env_l = self.env_r = 0.0

    # ---------------------------------------------------------- 参数

    def update_params(self, **kwargs) -> None:
        with self._lock:
            valid = {k: v for k, v in kwargs.items()
                     if k in EngineParams.__dataclass_fields__}
            merged = replace(self._params, **valid)

            merged.master = clamp01(merged.master)
            merged.left_gain = clamp01(merged.left_gain)
            merged.right_gain = clamp01(merged.right_gain)
            merged.floor = clamp01(merged.floor)
            merged.smoothing = clamp01(merged.smoothing)
            merged.mix = clamp01(merged.mix)
            merged.speed = max(0.05, min(3.0, merged.speed))
            merged.phase_shift = merged.phase_shift % 1.0
            merged.curve_duration = max(0.5, min(30.0, merged.curve_duration))

            merged.beam_position = max(-1.0, min(1.0, merged.beam_position))
            merged.beam_width = clamp01(merged.beam_width)
            merged.beam_sweep_rate = max(0.01, min(5.0, merged.beam_sweep_rate))
            merged.beam_sweep_depth = clamp01(merged.beam_sweep_depth)
            merged.beam_beat_hz = max(0.0, min(20.0, merged.beam_beat_hz))
            merged.beam_beat_depth = clamp01(merged.beam_beat_depth)
            if merged.beam_polarity not in ("in", "out"):
                merged.beam_polarity = "in"

            merged.audio_gain_l = max(0.0, min(3.0, merged.audio_gain_l))
            merged.audio_gain_r = max(0.0, min(3.0, merged.audio_gain_r))
            merged.audio_threshold = clamp01(merged.audio_threshold)
            if merged.source not in (SOURCE_WAVEFORM, SOURCE_AUDIO, SOURCE_MIX):
                merged.source = SOURCE_WAVEFORM

            merged.sharpen = clamp01(merged.sharpen)
            merged.noise_floor = clamp01(merged.noise_floor)
            merged.anti_adapt = clamp01(merged.anti_adapt)
            merged.duty = max(0.12, min(1.0, merged.duty))

            self._params = merged

    def params(self) -> EngineParams:
        with self._lock:
            return self._params

    def set_device(self, index: int) -> None:
        with self._lock:
            old = self._device
            self._device = max(0, min(xinput_backend.MAX_CONTROLLERS - 1, int(index)))
        if old != self._device:
            xinput_backend.get_backend().stop(old, repeats=3)
            self._env_l = self._env_r = 0.0
            self.connected = False

    def set_running(self, running: bool) -> None:
        with self._lock:
            if running == self._running:
                return
            self._running = running
        self._release_ticks = 0 if running else max(self._release_ticks, 40)
        # 空闲态是 150ms 一轮的休眠，不叫醒它的话点「开始」要等最多 150ms 才起震
        self._wake.set()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ---------------------------------------------------------- 波形求值

    def _base_period(self, p: EngineParams) -> float:
        if p.waveform == "custom":
            return p.curve_duration
        wf = WAVEFORMS.get(p.waveform)
        return wf.period if wf is not None else WAVEFORMS[self.FALLBACK_KEY].period

    def _sample(self, p: EngineParams, phase: float, right_shift: float) -> tuple[float, float]:
        if p.waveform == "custom":
            left = eval_curve(p.curve_points, phase)
            right = eval_curve(p.curve_points, phase + right_shift) if right_shift > 1e-6 else left
            return left, right

        wf = WAVEFORMS.get(p.waveform) or WAVEFORMS[self.FALLBACK_KEY]
        left, right = wf.sample(phase)
        if right_shift > 1e-6:
            _unused, right = wf.sample(phase + right_shift)

        if p.waveform_b and p.mix > 0.001:
            wf2 = WAVEFORMS.get(p.waveform_b)
            if wf2 is not None:
                l2, r2 = wf2.sample(phase)
                if right_shift > 1e-6:
                    _u2, r2 = wf2.sample(phase + right_shift)
                k = p.mix
                left += (l2 - left) * k
                right += (r2 - right) * k

        return clamp01(left), clamp01(right)

    def _audio_bands(self, p: EngineParams) -> tuple[float, float]:
        if self.audio_provider is None or p.source == SOURCE_WAVEFORM:
            return 1.0, 1.0
        try:
            bass, mid = self.audio_provider()
        except Exception:
            return 1.0, 1.0
        self.audio_bass = bass
        self.audio_mid = mid
        th = p.audio_threshold
        span = max(1e-4, 1.0 - th)
        return clamp01(max(0.0, (bass - th) / span)), clamp01(max(0.0, (mid - th) / span))

    # ---------------------------------------------------------- 主循环

    def _loop(self) -> None:
        backend = xinput_backend.get_backend()
        if not backend.available:
            self.last_error = backend.load_error
            return

        period = 1.0 / float(self.tick_hz)
        hz_window_start = time.perf_counter()
        hz_count = 0
        device = self.device

        def push_frame(a: float, b: float) -> None:
            sink = self.frame_sink
            if sink is not None:
                try:
                    sink(a, b)
                except Exception:
                    pass

        with TimerResolution(1):
            next_t = self._prev_time = time.perf_counter()

            while not self._stop_flag.is_set():
                with self._lock:
                    running = self._running
                    device = self._device
                    params = self._params

                # ---------- 空闲态：低频轮询，几乎不占 CPU ----------
                if not running:
                    if self._release_ticks > 0:
                        self._release_ticks -= 1
                        if not self.dry_run:
                            backend.set_vibration(device, 0, 0)
                        self.left_raw = self.right_raw = 0
                    else:
                        self.connected = self.dry_run or backend.is_connected(device)
                        self.history.append((0.0, 0.0))
                    self._env_l = self._env_r = 0.0
                    self.env_l = self.env_r = 0.0
                    push_frame(0.0, 0.0)
                    if self._release_ticks > 0:
                        self._stop_flag.wait(period)
                    else:
                        # 可被 set_running / shutdown 立刻叫醒
                        self._wake.wait(0.15)
                        self._wake.clear()
                    next_t = self._prev_time = time.perf_counter()
                    continue

                # ---------- 节拍 ----------
                next_t += period
                precise_sleep_until(next_t)
                now = time.perf_counter()
                dt = now - self._prev_time
                self._prev_time = now
                if dt <= 0.0:
                    dt = period
                dt = min(dt, 0.25)
                self._clock += dt

                # ---------- 连接检测 ----------
                connected = True if self.dry_run else backend.is_connected(device)
                self.connected = connected
                if not connected:
                    self.left_raw = self.right_raw = 0
                    self.env_l = self.env_r = 0.0
                    self.history.append((0.0, 0.0))
                    push_frame(0.0, 0.0)
                    continue

                # ---------- 相位推进 ----------
                cycle = self._base_period(params) / max(0.05, params.speed)
                self._phase = (self._phase + dt / max(0.02, cycle)) % 1.0
                self.phase_value = self._phase

                # ---------- 波形求值（极性会额外给右马达加相位偏移）----------
                beam_p = params.beam_params()
                right_shift = (params.phase_shift
                               + BeamProcessor.polarity_phase_shift(beam_p)) % 1.0
                wl, wr = self._sample(params, self._phase, right_shift)

                # ---------- 音源替换 / 调制 ----------
                if params.source != SOURCE_WAVEFORM:
                    bass, mid = self._audio_bands(params)
                    if params.source == SOURCE_AUDIO:
                        wl = bass * params.audio_gain_l
                        wr = mid * params.audio_gain_r
                    else:  # SOURCE_MIX：波形被音频调制
                        wl = wl * bass * params.audio_gain_l
                        wr = wr * mid * params.audio_gain_r

                # ---------- 占空比：压缩脉冲宽度 ----------
                if params.duty < 0.995:
                    cut = 1.0 - params.duty
                    wl = clamp01((wl - cut) / params.duty)
                    wr = clamp01((wr - cut) / params.duty)

                # ---------- 波束（声像 + 拍频 + 聚合）----------
                wl, wr, beam_pos = self._beam.process(wl, wr, beam_p, dt, self._clock)
                self.beam_position = beam_pos

                # ---------- 增益与下限 ----------
                amp_l = params.master * params.left_gain
                amp_r = params.master * params.right_gain
                floor = params.floor
                span = 1.0 - floor
                target_l = clamp01(floor + wl * amp_l * span)
                target_r = clamp01(floor + wr * amp_r * span)

                # ---------- 起停锐化：上升沿冲击 + 下降沿瞬切 ----------
                snap_l = snap_r = False
                if params.sharpen > 0.001:
                    rise_l = target_l - self._prev_target_l
                    rise_r = target_r - self._prev_target_r
                    if rise_l > 0.18:
                        self._kick_l = 2          # 约 16ms 的过冲
                    elif rise_l < -0.22:
                        self._cut_l = 2           # 明显下降沿：不跟平滑，直接切
                    if rise_r > 0.18:
                        self._kick_r = 2
                    elif rise_r < -0.22:
                        self._cut_r = 2

                    if self._kick_l > 0:
                        target_l = clamp01(
                            target_l + params.sharpen * (1.0 - target_l) * 0.85)
                        self._kick_l -= 1
                        snap_l = True
                    if self._kick_r > 0:
                        target_r = clamp01(
                            target_r + params.sharpen * (1.0 - target_r) * 0.85)
                        self._kick_r -= 1
                        snap_r = True
                    if self._cut_l > 0:
                        self._cut_l -= 1
                        snap_l = True
                    if self._cut_r > 0:
                        self._cut_r -= 1
                        snap_r = True

                self._prev_target_l = target_l
                self._prev_target_r = target_r

                # ---------- 体感增强：随机共振底噪 + 反适应漂移 ----------
                # 注意必须加在「目标值」这一层再进平滑，不能加在平滑之后的输出上 ——
                # 平滑本身是个漏积分器，直接加到输出上会被放大 1/alpha 倍（约 7 倍）。
                if params.noise_floor > 0.001:
                    # 一阶低通整形的随机噪声，幅度压在感知阈值以下（<9%）
                    self._noise_a += (random.uniform(-1.0, 1.0) - self._noise_a) * 0.35
                    self._noise_b += (random.uniform(-1.0, 1.0) - self._noise_b) * 0.35
                    target_l = clamp01(target_l + self._noise_a * params.noise_floor * 0.09)
                    target_r = clamp01(target_r + self._noise_b * params.noise_floor * 0.09)

                if params.anti_adapt > 0.001:
                    # 极慢随机游走（相关时间约 1.6 秒），打破「震麻了」的感知适应。
                    # 满量程约 ±10% 强度起伏，刚好卡在振幅 JND（约 15%）之下。
                    self._drift += random.uniform(-1.0, 1.0) * 0.12
                    self._drift = max(-1.0, min(1.0, self._drift * 0.995))
                    drift = self._drift * params.anti_adapt * 0.10
                    target_l = clamp01(target_l + drift)
                    target_r = clamp01(target_r + drift * 0.7)

                # ---------- 平滑 ----------
                if params.smoothing <= 1e-4:
                    self._env_l, self._env_r = target_l, target_r
                else:
                    tau = 0.0015 + params.smoothing * 0.35
                    alpha = 1.0 - math.exp(-dt / tau)
                    a_l = 1.0 if snap_l else alpha
                    a_r = 1.0 if snap_r else alpha
                    self._env_l += (target_l - self._env_l) * a_l
                    self._env_r += (target_r - self._env_r) * a_r
                    self._env_l = clamp01(self._env_l)
                    self._env_r = clamp01(self._env_r)

                # ---------- 下发（关键：每 tick 必发）----------
                li = int(self._env_l * MAX_RAW + 0.5)
                ri = int(self._env_r * MAX_RAW + 0.5)
                if not self.dry_run:
                    backend.set_vibration(device, li, ri)
                self.left_raw = li
                self.right_raw = ri
                self.env_l = self._env_l
                self.env_r = self._env_r
                self.history.append((self._env_l, self._env_r))
                push_frame(self._env_l, self._env_r)

                # ---------- 实测频率 ----------
                hz_count += 1
                if now - hz_window_start >= 1.0:
                    self.measured_hz = hz_count / (now - hz_window_start)
                    hz_count = 0
                    hz_window_start = now

        if not self.dry_run:
            backend.stop(device, repeats=3)

    # ---------------------------------------------------------- 便捷方法

    def preview_history(self) -> list[tuple[float, float]]:
        return list(self.history)

    def reset_phase(self) -> None:
        self._phase = 0.0
        self._beam.reset()
        self._kick_l = self._kick_r = 0
        self._cut_l = self._cut_r = 0
        self._drift = 0.0
        self._prev_target_l = self._prev_target_r = 0.0

    def pulse_once(self, left: float, right: float, duration: float = 0.35) -> None:
        """单次强震（「测试震动」按钮），不改变运行状态。"""
        def worker() -> None:
            backend = xinput_backend.get_backend()
            dev = self.device
            li = int(clamp01(left) * MAX_RAW)
            ri = int(clamp01(right) * MAX_RAW)
            end = time.perf_counter() + duration
            with TimerResolution(1):
                while time.perf_counter() < end and not self._stop_flag.is_set():
                    backend.set_vibration(dev, li, ri)
                    time.sleep(0.004)
                backend.stop(dev, repeats=3)

        threading.Thread(target=worker, name="rumble-pulse", daemon=True).start()
