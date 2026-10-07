"""波形库 —— 按摩/刺激节奏生成。

每个波形是一个纯函数 f(phase) -> (left, right)，phase ∈ [0, 1) 表示在一个
循环内的进度，返回值均在 0.0 ~ 1.0。首尾必须自然衔接，保证无限循环无爆点。

参数依据（来自按摩器械行业公开的电机/模式参数）：
  · 基础振动 20~120Hz，低频 20~50Hz 偏「轻拍」，高频 80~120Hz 偏「震颤」
  · 捶打/叩击冲击频率 10~60 次/秒，间隔 0.2~0.5s
  · 揉捏开合频率 15~40 次/分钟（≈0.25~0.67Hz）
  · 电脉冲按摩用方波/三角波/梯形波调制，调制周期 0.2s ~ 数秒
  · 触感档位：低频 8~12Hz 舒缓 · 中频 15~20Hz 轻拍 · 高频 >=25Hz 强刺激
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

TAU = math.tau

# 强度标签
MILD = "柔和"
MEDIUM = "适中"
STRONG = "刺激"
EXTREME = "极刺激"


# ================================================================ 数学工具


def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def bump(p: float, center: float, width: float) -> float:
    """在 center 处的一个平滑包（余弦钟形），支持跨 0 点环绕。"""
    d = abs((p - center + 0.5) % 1.0 - 0.5)
    if d >= width:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * d / width))


def exp_tap(p: float, start: float, rate: float, span: float = 0.9) -> float:
    """在 start 处起跳、指数衰减的脉冲。"""
    d = (p - start) % 1.0
    if d >= span:
        return 0.0
    return math.exp(-rate * d)


def soft_square(p: float, sharp: float = 9.0) -> float:
    """平滑方波，避免硬边造成的马达顿挫。"""
    return 0.5 + 0.5 * math.tanh(sharp * math.sin(TAU * p))


def triangle(p: float) -> float:
    p = p % 1.0
    return 1.0 - abs(2.0 * p - 1.0)


def sawtooth(p: float) -> float:
    return (p % 1.0)


def sine01(p: float) -> float:
    """0..1 的正弦。"""
    return 0.5 - 0.5 * math.cos(TAU * (p % 1.0))


def hash01(i: int) -> float:
    """确定性整数哈希 -> [0,1)。用于「随机」波形，保证可复现且无需状态。"""
    x = (i * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    x = (x * 3266489917) & 0xFFFFFFFF
    x ^= x >> 16
    return (x & 0xFFFFFF) / 0x1000000


# ================================================================ 摩斯码时间线

_MORSE_TABLE = {
    "S": "...", "O": "---", "H": "....", "I": "..", "E": ".", "V": "...-",
    "A": ".-", "N": "-.", "T": "-", "R": ".-.", "L": ".-..", "P": ".--.",
}


def _build_morse(text: str) -> tuple[list[tuple[float, float]], float]:
    """返回 ([(起始相位, 持续相位), ...], 总长度) —— 全为归一化后的值。"""
    units: list[tuple[float, float]] = []  # (start_unit, dur_unit)
    cursor = 0.0
    for ci, ch in enumerate(text):
        code = _MORSE_TABLE.get(ch.upper())
        if code is None:
            continue
        for si, sym in enumerate(code):
            dur = 3.0 if sym == "-" else 1.0
            units.append((cursor, dur))
            cursor += dur
            if si != len(code) - 1:
                cursor += 1.0  # 符号内间隔
        cursor += 3.0  # 字符间隔
    cursor += 4.0  # 尾部静默，凑满一圈
    total = cursor if cursor > 0 else 1.0
    return [(s / total, d / total) for s, d in units], total


_MORSE_EVENTS, _MORSE_TOTAL = _build_morse("SOS")


def _morse_sample(p: float) -> float:
    for start, dur in _MORSE_EVENTS:
        if start <= p < start + dur:
            # 边缘做 8% 软化，避免开关爆音感
            edge = min(dur * 0.18, 0.006)
            into = (p - start) / edge
            left = (start + dur - p) / edge
            return clamp01(min(1.0, into, left))
    return 0.0


# ================================================================ 波形定义


@dataclass(frozen=True)
class Waveform:
    key: str
    name: str
    category: str
    desc: str
    period: float            # 一个循环的基准秒数
    intensity: str           # 强度标签
    fn: Callable[[float], tuple[float, float]]

    def sample(self, phase: float) -> tuple[float, float]:
        l, r = self.fn(phase % 1.0)
        return clamp01(l), clamp01(r)


def _w(key, name, category, desc, period, intensity, fn) -> Waveform:
    return Waveform(key, name, category, desc, period, intensity, fn)


# ---------------------------------------------------------------- 基础

def _steady(p: float):
    return 1.0, 1.0


def _breath(p: float):
    v = sine01(p)
    return v, v


def _sine(p: float):
    v = 0.5 + 0.5 * math.sin(TAU * (p % 1.0))
    return v, v


def _saw(p: float):
    v = sawtooth(p)
    return v, v


def _depth(p: float):
    """深度按摩：低频大幅揉压，带底噪，双马达同相。"""
    v = 0.28 + 0.72 * (0.5 - 0.5 * math.cos(TAU * (p % 1.0)))
    return v, v


# ---------------------------------------------------------------- 按摩手法


def _knead(p: float):
    """揉捏：左右交替挤压，一侧强一侧弱。"""
    a = 0.5 + 0.5 * math.sin(TAU * (p % 1.0))
    return a, 1.0 - a


def _shiatsu(p: float):
    """推拿：双马达相位错开 120°，都不归零，像掌根推压。"""
    a = 0.5 + 0.5 * math.sin(TAU * (p % 1.0))
    b = 0.5 + 0.5 * math.sin(TAU * (p % 1.0) + TAU / 3.0)
    return a, b


def _tap(p: float):
    """敲击：短促脉冲 + 指数衰减（行业参数约 0.2~0.5s 一次）。"""
    v = exp_tap(p, 0.08, 13.0, span=0.55)
    return v, v


def _hammer(p: float):
    """捶打：更慢更重的冲击包络。"""
    v = exp_tap(p, 0.05, 6.5, span=0.85)
    return v, v


def _press(p: float):
    """按压：缓慢加压 → 保持 → 释放。"""
    q = p % 1.0
    if q < 0.28:
        v = smoothstep(q / 0.28)
    elif q < 0.66:
        v = 1.0
    elif q < 0.86:
        v = 1.0 - smoothstep((q - 0.66) / 0.20)
    else:
        v = 0.0
    return 0.55 + 0.45 * v, 0.35 + 0.65 * v


def smoothstep(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def _scrape(p: float):
    """刮痧：单向拖拽感，左马达持续、右马达快速扫过。"""
    q = p % 1.0
    drag = math.sin(math.pi * q) ** 0.6
    flick = (0.5 + 0.5 * math.sin(TAU * q * 6.0)) * drag
    return 0.35 + 0.5 * drag, flick


def _acu(p: float):
    """针灸/点穴：规律的三点短促针刺。"""
    v = 0.0
    for c in (0.02, 0.36, 0.70):
        v = max(v, bump(p, c, 0.045))
    return v, v * 0.75


# ---------------------------------------------------------------- 节奏冲击


def _pulse(p: float):
    v = soft_square(p, 9.0)
    return v, v


def _fast_pulse(p: float):
    v = soft_square(p, 14.0)
    return v, v


def _drumroll(p: float):
    """连击/打桩：一串由弱到强的高速连续冲击。"""
    n = 14
    q = (p % 1.0) * n
    i = int(q)
    local = q - i
    amp = 0.25 + 0.75 * (i / (n - 1.0))
    v = amp * math.exp(-9.0 * local)
    return v, v


def _triple(p: float):
    """三连击：左 · 右 · 双，然后休息。"""
    b1 = exp_tap(p, 0.04, 16.0, span=0.2)
    b2 = exp_tap(p, 0.26, 16.0, span=0.2)
    b3 = exp_tap(p, 0.48, 11.0, span=0.4)
    return max(b1, b3), max(b2, b3)


def _gallop(p: float):
    """狂奔：长-短-短的骑乘节奏（0.9s 循环）。"""
    q = p % 1.0
    b1 = exp_tap(q, 0.00, 7.0, span=0.32)
    b2 = exp_tap(q, 0.33, 12.0, span=0.22)
    b3 = exp_tap(q, 0.56, 12.0, span=0.30)
    v = max(b1, b2 * 0.85, b3 * 0.9)
    return v, v * 0.82


def _burst(p: float):
    """渐强爆发：脉冲越来越密、越来越强，最后一下砸下去。"""
    q = p % 1.0
    if q < 0.72:
        k = q / 0.72
        freq = 4.0 + 16.0 * k * k
        amp = 0.18 + 0.62 * k
        v = amp * soft_square((q * freq) % 1.0, 10.0)
        return v, v
    # 尾段：一次满功率冲击后收尾
    tail = (q - 0.72) / 0.28
    v = math.exp(-5.0 * tail)
    return v, v


def _storm(p: float):
    """暴风：高速不规则抖动，双马达不同频，压迫感强。"""
    q = p % 1.0
    a = soft_square((q * 17.0) % 1.0, 8.0)
    b = soft_square((q * 23.0 + 0.37) % 1.0, 8.0)
    env = 0.55 + 0.45 * sine01(q)
    return a * env, b * env


# ---------------------------------------------------------------- 波形起伏


def _wave(p: float):
    a = sine01(p)
    return a, 1.0 - a


def _tide(p: float):
    """潮汐：不对称的长周期，缓涨缓落。"""
    q = p % 1.0
    v = sine01(q) ** 0.75
    return v, v * 0.9


def _surf(p: float):
    """海浪：快涨慢落。"""
    q = p % 1.0
    if q < 0.16:
        v = smoothstep(q / 0.16)
    else:
        v = (1.0 - (q - 0.16) / 0.84) ** 1.7
    return v, v * 0.7


def _ripple(p: float):
    """涟漪：一串由强到弱、越来越密的连续波。"""
    centers = (0.00, 0.15, 0.28, 0.39, 0.48, 0.56, 0.63, 0.69, 0.745, 0.79, 0.83, 0.87)
    v = 0.0
    for i, c in enumerate(centers):
        v = max(v, bump(p, c, 0.085) * (1.0 - 0.065 * i))
    return v, v


def _step(p: float):
    """阶梯：一级级往上爬，然后突然落回。"""
    steps = (0.18, 0.36, 0.55, 0.74, 0.90, 1.00)
    q = p % 1.0
    i = min(len(steps) - 1, int(q * len(steps)))
    v = steps[i]
    return v, v


def _ramp(p: float):
    v = (p % 1.0) ** 1.3
    return v, v


def _butterfly(p: float):
    """蝴蝶：左右高速交替，外层有强弱包络。"""
    q = p % 1.0
    env = sine01(q)
    osc = 0.5 + 0.5 * math.sin(TAU * q * 5.0)
    return env * osc, env * (1.0 - osc)


def _vibrato(p: float):
    """颤动：高频小幅调制叠加在持续输出上。"""
    q = p % 1.0
    m = 0.5 + 0.5 * math.sin(TAU * q * 8.0)
    return 0.35 + 0.65 * m, 0.35 + 0.65 * (1.0 - m)


# ---------------------------------------------------------------- 刺激


def _heartbeat(p: float):
    b1 = bump(p, 0.04, 0.11)
    b2 = bump(p, 0.24, 0.085) * 0.72
    return b1, max(b1, b2) * 0.95


def _throb(p: float):
    """搏动：比心跳更重更快的持续搏动。"""
    b1 = bump(p, 0.03, 0.14)
    b2 = bump(p, 0.30, 0.11) * 0.8
    return b1, b2


def _cardio(p: float):
    """心动加速：一圈内节拍越来越快，然后重置。"""
    centers = (0.00, 0.24, 0.44, 0.60, 0.72, 0.82, 0.90)
    v = 0.0
    for i, c in enumerate(centers):
        v = max(v, bump(p, c, 0.055) * (0.72 + 0.28 * (i / 6.0)))
    return v, v * 0.9


def _electro(p: float):
    """电脉冲：极短高频爆点，针刺感最强。"""
    v = 0.0
    for c in (0.00, 0.055, 0.11, 0.165, 0.22):
        v = max(v, bump(p, c, 0.022))
    return v, v


def _twitch(p: float):
    """抽搐：不规则的多段短促抽动。"""
    v = 0.0
    for c, w, a in ((0.02, 0.03, 1.0), (0.14, 0.02, 0.7), (0.21, 0.04, 0.9),
                    (0.42, 0.025, 0.6), (0.55, 0.05, 1.0), (0.78, 0.03, 0.8)):
        v = max(v, bump(p, c, w) * a)
    return v, v * 0.85


def _tease(p: float):
    """逗弄：缓慢逼到临界，突然全部收回。"""
    q = p % 1.0
    if q < 0.85:
        v = 0.12 + 0.73 * smoothstep(q / 0.85)
        v += 0.12 * math.sin(TAU * q * 7.0) * (q / 0.85) ** 2
        return clamp01(v), clamp01(v * 0.85)
    return 0.02, 0.02


def _climax(p: float):
    """巅峰爆发：长时间蓄力，末段全功率乱震。"""
    q = p % 1.0
    if q < 0.70:
        k = q / 0.70
        base = 0.10 + 0.30 * k
        turb = 0.10 * k * (0.5 + 0.5 * math.sin(TAU * q * 11.0))
        v = base + turb
        return clamp01(v), clamp01(v * 0.9)
    k = (q - 0.70) / 0.30
    a = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(TAU * q * 31.0))
    b = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(TAU * q * 27.0 + 1.1))
    fade = 1.0 - smoothstep(max(0.0, (k - 0.75) / 0.25))
    return clamp01(a * fade), clamp01(b * fade)


# ---------------------------------------------------------------- 特殊


# ---------------------------------------------------------------- 玩具模式
#
# 命名与节奏参考成人震动玩具行业的通行模式（持续/间歇/渐强/渐弱/强弱交替/
# 海浪/脉冲）以及 Lovense 的四套预设（pulse / wave / fireworks / earthquake）。
# 参数区间取自行业公开的技术规格：持续振动约 3000~5000 次/分（50~83Hz），
# 间歇模式常见「震 3 秒停 2 秒」，渐强从约 2000 次/分爬到 6000 次/分。


def _make_burst_points(seed: int, count: int, w_lo: float, w_hi: float) -> tuple:
    rng = random.Random(seed)
    pts = []
    for i in range(count):
        c = (i / count + rng.uniform(-0.018, 0.018)) % 1.0
        a = rng.uniform(0.55, 1.0)
        w = rng.uniform(w_lo, w_hi)
        pts.append((c, w, a))
    return tuple(pts)


_FIREWORK_POINTS = _make_burst_points(20261008, 11, 0.012, 0.034)
_SPARK_POINTS = _make_burst_points(777001, 22, 0.007, 0.018)


def _fireworks(p: float):
    """烟花：一圈里随机炸开多次，每次一个短促爆点，疏密不一。"""
    v = 0.0
    for c, w, a in _FIREWORK_POINTS:
        v = max(v, bump(p, c, w) * a)
    return v, v * 0.85


def _earthquake(p: float):
    """地震：不规则剧烈抖动，两个马达用各自独立的随机序列。"""
    n = 24
    q = (p % 1.0) * n
    i = int(q)
    local = smoothstep(q - i)
    a = lerp(hash01(i * 7), hash01((i + 1) * 7), local)
    b = lerp(hash01(i * 7 + 5551), hash01((i + 1) * 7 + 5551), local)
    env = 0.62 + 0.38 * sine01(p)
    return clamp01(a * env), clamp01(b * env)


def _spank(p: float):
    """拍打：一记干脆的拍击 + 长静默，比敲击更重更疏。"""
    v = max(bump(p, 0.05, 0.045), exp_tap(p, 0.09, 22.0, span=0.30))
    return v, v * 0.5


def _suction(p: float):
    """吸吮：缓慢拉起 → 急促释放，模拟负压节奏。"""
    q = p % 1.0
    if q < 0.62:
        v = smoothstep(q / 0.62) ** 0.7
    elif q < 0.72:
        v = 1.0 - smoothstep((q - 0.62) / 0.10)
    else:
        v = 0.0
    return v, v * 0.78


def _thrust(p: float):
    """抽送：推入快、退出慢的规律推拉节奏。"""
    q = p % 1.0
    if q < 0.45:
        v = smoothstep(q / 0.45)
    elif q < 0.55:
        v = 0.35 + 0.65 * (1.0 - smoothstep((q - 0.45) / 0.10))
    else:
        v = 0.35 * (1.0 - (q - 0.55) / 0.45)
    return clamp01(v), clamp01(v * 0.85)


def _shake(p: float):
    """摇头：左右快速摆动，像拨浪鼓。"""
    q = p % 1.0
    osc = 0.5 + 0.5 * math.sin(TAU * q * 4.0)
    env = 0.55 + 0.45 * sine01(q)
    return env * osc, env * (1.0 - osc)


def _creep(p: float):
    """蠕动：缓慢爬行的强度变化，几乎察觉不到切换点。"""
    q = p % 1.0
    base = 0.30 + 0.55 * (0.5 - 0.5 * math.cos(TAU * q))
    wob = 0.08 * math.sin(TAU * q * 3.0 + 0.6)
    return clamp01(base + wob), clamp01(base - wob)


def _rattle(p: float):
    """抖动：高频小幅断续，像牙齿打颤。"""
    q = p % 1.0
    carrier = 0.5 + 0.5 * math.sin(TAU * q * 14.0)
    gate = 0.5 + 0.5 * math.sin(TAU * q * 2.0)
    v = 0.25 + 0.75 * carrier * (0.4 + 0.6 * gate)
    return clamp01(v), clamp01(v)


def _dj(p: float):
    """变频率：一圈内三段变速（慢 → 快 → 极快），像 DJ 搓碟。"""
    q = p % 1.0
    if q < 0.38:
        v = soft_square((q / 0.38 * 3.0) % 1.0, 10.0) * 0.8
    elif q < 0.72:
        v = soft_square(((q - 0.38) / 0.34 * 9.0) % 1.0, 10.0)
    else:
        v = soft_square(((q - 0.72) / 0.28 * 16.0) % 1.0, 10.0)
    return v, v


def _purr(p: float):
    """咕噜：猫呼噜式的低频颤动，持续而带颗粒感。"""
    q = p % 1.0
    trem = 0.5 + 0.5 * math.sin(TAU * q * 8.0)
    slow = 0.5 + 0.5 * math.sin(TAU * q)
    v = 0.45 + 0.35 * trem + 0.20 * slow
    return clamp01(v * 0.95), clamp01(v)


# ---------------------------------------------------------------- 节律引导
#
# 依据 Doppel 的临床研究（Azevedo et al., Scientific Reports 2017）：
# 比自身静息心率更慢的、心跳般的节律刺激，能显著降低生理唤醒与主观焦虑。
# 反过来更快的节律用于提神。研究还指出引导要「渐进」才有效，
# 所以这些波形都设计成可以直接用「速度」滑杆平滑地改变 BPM。


def _calm(p: float):
    """镇静节律：慢速心跳。默认速度约 55 BPM，把速度调到 0.7x 约 38 BPM 更沉。

    已验证用途：降唤醒、缓解紧张（慢于自身静息心率的节律引导）。
    """
    b1 = bump(p, 0.06, 0.075)
    b2 = bump(p, 0.30, 0.055) * 0.62
    return b1 * 0.90, max(b1, b2) * 0.75


def _energize(p: float):
    """提神节律：快速心跳。默认速度约 109 BPM，速度调到 1.4x 约 150 BPM。"""
    b1 = bump(p, 0.03, 0.10)
    b2 = bump(p, 0.22, 0.075) * 0.70
    return max(b1, b2), b1 * 0.85


def _breath478(p: float):
    """4-7-8 呼吸引导：吸气 4s → 屏息 7s → 呼气 8s，一圈 19s。

    跟着它呼吸：震起来就吸气，持续最强时屏息，慢慢弱下去时呼气。
    """
    q = (p % 1.0) * 19.0
    if q < 4.0:
        v = smoothstep(q / 4.0)
    elif q < 11.0:
        v = 1.0
    elif q < 19.0:
        v = 1.0 - smoothstep((q - 11.0) / 8.0)
    else:
        v = 0.0
    return v, v


def _melt(p: float):
    """融化：强度整体缓慢滑落再缓缓拉起，没有明显节拍。"""
    q = p % 1.0
    v = 1.0 - 0.75 * smoothstep(q)
    v += 0.06 * math.sin(TAU * q * 5.0)
    return clamp01(v), clamp01(v - 0.12)


def _float(p: float):
    """失重：缓慢漂浮，几乎无节拍，适合长时间挂着。"""
    q = p % 1.0
    a = 0.5 - 0.5 * math.cos(TAU * q)
    b = 0.5 - 0.5 * math.cos(TAU * q * 1.5 + 1.1)
    return 0.22 + 0.55 * a, 0.22 + 0.55 * b


# ---------------------------------------------------------------- 特殊


def _ladder(p: float):
    """递进：台阶式加速，每一级都比上一级更快更强。"""
    q = p % 1.0
    seg = min(4, int(q * 5))
    local = (q * 5) - int(q * 5)
    freq = 2.0 + seg * 2.5
    amp = 0.55 + 0.11 * seg
    v = amp * soft_square((local * freq) % 1.0, 10.0)
    return clamp01(v), clamp01(v)


def _spark(p: float):
    """电火花：极短随机爆点，比电脉冲更疏更不可预测。"""
    v = 0.0
    for c, w, a in _SPARK_POINTS:
        v = max(v, bump(p, c, w) * a)
    return v, v * 0.7


def _drip(p: float):
    """滴落：一记清脆落点 + 长静默，然后来一记轻的。"""
    q = p % 1.0
    v = exp_tap(q, 0.0, 26.0, span=0.35)
    v = max(v, 0.55 * exp_tap(q, 0.26, 20.0, span=0.5))
    return v, v * 0.45


# ---------------------------------------------------------------- 电刺激思路
#
# 借鉴 DG-LAB 郊狼（TENS 电刺激）的波形设计经验。它的开源文档里有一条关键观察：
# 「人体对频率变化的感受较慢，频率过快变化无法形成节奏感；
#   而脉冲宽度的频繁变化可以创造多样的感觉。」
# 郊狼靠脉宽调制做「推力」感，我们用幅度包络 + 占空比做等价的事。


def _push(p: float):
    """推力：强度缓慢爬升到顶，然后突然全部收回 —— 郊狼的「推力」波形思路。

    感受上像被一遍遍推着走，而不是被震。
    """
    q = p % 1.0
    if q < 0.72:
        k = q / 0.72
        v = 0.10 + 0.90 * (k ** 1.7)
    else:
        v = 0.0
    return v, v * 0.92


def _dualband(p: float):
    """频段切换：在「慢而重」和「快而细」两个节奏之间硬切。

    郊狼的双频切换波形 —— 靠节奏的突变制造冲击感。
    """
    q = p % 1.0
    if q < 0.5:
        # 慢而重：一拍一下
        local = (q / 0.5 * 2.0) % 1.0
        v = 0.35 + 0.65 * soft_square(local, 9.0)
        return v, v * 0.55
    # 快而细：密集短脉冲
    local = ((q - 0.5) / 0.5 * 12.0) % 1.0
    v = 0.30 + 0.70 * soft_square(local, 12.0)
    return v * 0.8, v


def _glide(p: float):
    """渐快：一圈之内节奏从慢平滑加快到快（郊狼的「节内渐变」）。

    公式上让相位按二次曲线推进，所以越往后越密。
    """
    q = p % 1.0
    warp = q * q * 2.4 + q * 0.6          # 非线性时间轴
    v = soft_square(warp % 1.0, 9.0)
    env = 0.55 + 0.45 * q
    v *= env
    return v, v * 0.9


# ---------------------------------------------------------------- 彩蛋


def _577(p: float):
    """为作者 577 定制的长叙事波形 —— 一圈约 24 秒，走过完整的六幕。

    把整库的手段串成一条线：
      ① 铺垫    渐强呼吸，把节奏拉起来
      ② 挑逗    三次「逼近临界再抽走」，一次比一次高
      ③ 涌动    两马达反相推移 + 拍频起伏
      ④ 加速    脉冲越来越密（郊狼的节内渐变）
      ⑤ 边缘    高位维持 + 高频微颤（TENS 的 edge 思路）
      ⑥ 收束    全功率短促爆发，然后干净地停下
    """
    q = p % 1.0

    # ① 铺垫 0.00~0.18 —— 渐强呼吸
    if q < 0.18:
        k = q / 0.18
        v = 0.12 + 0.46 * smoothstep(k)
        v += 0.06 * math.sin(TAU * k * 2.0)
        return v, v * 0.85

    # ② 挑逗 0.18~0.46 —— 三次逼近再抽走，峰值递增
    if q < 0.46:
        k = (q - 0.18) / 0.28
        seg = min(2, int(k * 3))
        local = k * 3 - seg
        peak = 0.62 + 0.11 * seg              # 0.62 / 0.73 / 0.84
        base = 0.20 + 0.05 * seg
        if local < 0.62:
            v = base + (peak - base) * smoothstep(local / 0.62) ** 0.8
        elif local < 0.74:
            v = peak                                # 停一拍
        else:
            v = base * 0.7 * (1.0 - smoothstep((local - 0.74) / 0.26))
        return v, v * (0.78 + 0.07 * seg)

    # ③ 涌动 0.46~0.62 —— 左右反相推移 + 拍频
    if q < 0.62:
        k = (q - 0.46) / 0.16
        swing = 0.5 + 0.5 * math.sin(TAU * k * 2.0)
        beat = 0.62 + 0.38 * (0.5 + 0.5 * math.sin(TAU * k * 7.0))
        env = (0.55 + 0.30 * smoothstep(k)) * beat
        return env * (0.35 + 0.65 * swing), env * (0.35 + 0.65 * (1.0 - swing))

    # ④ 加速 0.62~0.78 —— 脉冲越来越密
    if q < 0.78:
        k = (q - 0.62) / 0.16
        warp = k * k * 9.0 + k * 3.0
        v = soft_square(warp % 1.0, 10.0)
        env = 0.55 + 0.36 * smoothstep(k)
        v *= env
        return v, v * 0.88

    # ⑤ 边缘 0.78~0.92 —— 高位维持 + 高频微颤
    if q < 0.92:
        k = (q - 0.78) / 0.14
        hold = 0.88 + 0.06 * math.sin(TAU * k * 9.0)
        hold *= 1.0 - 0.10 * smoothstep(k)
        return hold, hold * 0.93

    # ⑥ 收束 0.92~1.00 —— 短促爆发后干净归零
    k = (q - 0.92) / 0.08
    if k < 0.26:
        v = 0.75 + 0.25 * math.sin(TAU * k * 14.0)
    elif k < 0.42:
        v = 1.0
    else:
        v = 1.0 - smoothstep((k - 0.42) / 0.58)
    return clamp01(v), clamp01(v * (0.9 if k < 0.42 else 0.7))


def _random(p: float):
    """随机乱震：每 1/8 圈换一个目标值，之间线性过渡，双马达用不同序列。"""
    n = 8
    q = (p % 1.0) * n
    i = int(q)
    local = smoothstep(q - i)
    a = lerp(hash01(i), hash01(i + 1), local)
    b = lerp(hash01(i + 977), hash01(i + 978), local)
    return a, b


def _morse(p: float):
    v = _morse_sample(p % 1.0)
    return v, v


def _chaos(p: float):
    """混沌：多频叠加，完全不规律但连续。"""
    q = p % 1.0
    v = (
        0.5
        + 0.22 * math.sin(TAU * q * 3.0)
        + 0.16 * math.sin(TAU * q * 7.0 + 1.3)
        + 0.12 * math.sin(TAU * q * 13.0 + 2.7)
    )
    w = (
        0.5
        + 0.22 * math.sin(TAU * q * 5.0 + 0.7)
        + 0.16 * math.sin(TAU * q * 11.0 + 2.1)
        + 0.12 * math.sin(TAU * q * 17.0)
    )
    return clamp01(v), clamp01(w)


# ================================================================ 注册表

WAVEFORMS: dict[str, Waveform] = {}


def _register(w: Waveform) -> None:
    WAVEFORMS[w.key] = w


# 基础
_register(_w("steady", "常震", "基础", "恒定满幅，最基础的持续震动", 1.0, MEDIUM, _steady))
_register(_w("breath", "呼吸", "基础", "正弦渐强渐弱，最柔和，适合长时间挂机", 4.0, MILD, _breath))
_register(_w("sine", "正弦波", "基础", "标准正弦起伏", 2.0, MILD, _sine))
_register(_w("saw", "锯齿", "基础", "线性爬升后瞬间归零，有周期性拉扯感", 1.5, MEDIUM, _saw))
_register(_w("depth", "深度按摩", "基础", "低频大幅揉压，带常驻底噪", 4.5, MEDIUM, _depth))

# 按摩手法
_register(_w("knead", "揉捏", "按摩手法", "左右交替挤压，模拟人手抓揉（约 25 次/分）", 2.4, MEDIUM, _knead))
_register(_w("shiatsu", "推拿", "按摩手法", "双马达相位错开 120°，掌根推压感", 3.0, MEDIUM, _shiatsu))
_register(_w("tap", "敲击", "按摩手法", "短促脉冲 + 指数衰减，约 0.5s 一次", 0.5, STRONG, _tap))
_register(_w("hammer", "捶打", "按摩手法", "更慢更重的冲击，力度峰值高", 1.0, STRONG, _hammer))
_register(_w("press", "按压", "按摩手法", "缓慢加压 → 保持 → 释放", 3.6, MILD, _press))
_register(_w("scrape", "刮痧", "按摩手法", "单向拖拽，右马达快速扫过", 2.2, MEDIUM, _scrape))
_register(_w("acu", "针灸", "按摩手法", "规律三点短促针刺，点穴感", 1.5, EXTREME, _acu))

# 节奏冲击
_register(_w("pulse", "脉冲", "节奏冲击", "50% 占空比方波，干脆有力", 0.6, MEDIUM, _pulse))
_register(_w("fastpulse", "快脉冲", "节奏冲击", "高频方波串，密集震颤", 0.22, STRONG, _fast_pulse))
_register(_w("drumroll", "连击", "节奏冲击", "由弱到强的 14 连高速冲击，打桩机感", 1.2, STRONG, _drumroll))
_register(_w("triple", "三连击", "节奏冲击", "左 · 右 · 双 三段重击后休息", 1.4, STRONG, _triple))
_register(_w("gallop", "狂奔", "节奏冲击", "长-短-短骑乘节奏，像马蹄", 0.9, STRONG, _gallop))
_register(_w("burst", "渐强爆发", "节奏冲击", "脉冲越来越密越来越强，最后砸下去", 3.0, EXTREME, _burst))
_register(_w("storm", "暴风", "节奏冲击", "双马达异频高速抖动，压迫感极强", 2.0, EXTREME, _storm))

# 波形起伏
_register(_w("wave", "波浪", "波形起伏", "左右 180° 反相，强度来回推移", 2.5, MEDIUM, _wave))
_register(_w("tide", "潮汐", "波形起伏", "长周期不对称缓涨缓落", 7.0, MILD, _tide))
_register(_w("surf", "海浪", "波形起伏", "快涨慢落，一次一次的推力", 5.0, MEDIUM, _surf))
_register(_w("ripple", "涟漪", "波形起伏", "一串由强到弱、越来越密的连续波", 2.4, MEDIUM, _ripple))
_register(_w("step", "阶梯", "波形起伏", "一级级往上爬，然后突然落回", 4.0, MEDIUM, _step))
_register(_w("ramp", "上升", "波形起伏", "线性渐强到顶后瞬间归零", 3.0, MEDIUM, _ramp))
_register(_w("butterfly", "蝴蝶", "波形起伏", "左右高速交替 + 强弱包络", 1.6, STRONG, _butterfly))
_register(_w("vibrato", "颤动", "波形起伏", "高频小幅调制叠加在持续输出上", 1.0, MEDIUM, _vibrato))

# 刺激
_register(_w("heartbeat", "心跳", "刺激", "咚-咚—停顿，双脉冲心跳包络", 1.2, MEDIUM, _heartbeat))
_register(_w("throb", "搏动", "刺激", "比心跳更重更快的持续搏动", 0.7, STRONG, _throb))
_register(_w("cardio", "心动加速", "刺激", "一圈内节拍越来越快，然后重置", 3.2, STRONG, _cardio))
_register(_w("electro", "电脉冲", "刺激", "极短高频爆点，针刺感最强", 0.9, EXTREME, _electro))
_register(_w("twitch", "抽搐", "刺激", "不规则多段短促抽动", 1.5, EXTREME, _twitch))
_register(_w("tease", "逗弄", "刺激", "缓慢逼到临界，突然全部收回", 3.0, STRONG, _tease))
_register(_w("climax", "巅峰爆发", "刺激", "长时间蓄力，末段全功率乱震", 5.0, EXTREME, _climax))

# 特殊
_register(_w("random", "随机", "特殊", "随机保持 + 平滑过渡，完全不可预测", 1.0, STRONG, _random))
_register(_w("chaos", "混沌", "特殊", "多频叠加，不规律但连续", 2.0, STRONG, _chaos))
_register(_w("morse", "摩斯码", "特殊", "以摩斯电码节奏震动（默认 SOS）", 2.43, MEDIUM, _morse))
_register(_w("ladder", "递进", "特殊", "台阶式加速，一级比一级快、比一级强", 3.0, STRONG, _ladder))
_register(_w("spark", "电火花", "特殊", "极短随机爆点，比电脉冲更疏、更不可预测", 1.6, EXTREME, _spark))
_register(_w("drip", "滴落", "特殊", "一记清脆落点 + 长静默，然后一记轻的", 1.4, MEDIUM, _drip))
_register(_w("push", "推力", "特殊",
             "强度缓慢爬升到顶然后突然全部收回，像被一遍遍推着走。"
             "思路来自电刺激设备的脉宽调制（郊狼的「推力」波形）", 2.8, STRONG, _push))
_register(_w("dualband", "频段切换", "特殊",
             "在「慢而重」和「快而细」两个节奏之间硬切，靠节奏突变制造冲击", 1.8, STRONG, _dualband))
_register(_w("glide", "渐快", "特殊",
             "一圈之内节奏从慢平滑加快到快，越往后越密（电刺激设备的「节内渐变」）",
             3.2, MEDIUM, _glide))

# 玩具模式
_register(_w("fireworks", "烟花", "玩具模式", "一圈里随机炸开多次，疏密不一（Lovense fireworks 思路）",
             2.6, STRONG, _fireworks))
_register(_w("earthquake", "地震", "玩具模式", "不规则剧烈抖动，双马达各走各的随机序列（Lovense earthquake）",
             2.2, EXTREME, _earthquake))
_register(_w("spank", "拍打", "玩具模式", "一记干脆的拍击 + 长静默，比敲击更重更疏", 1.1, STRONG, _spank))
_register(_w("suction", "吸吮", "玩具模式", "缓慢拉起 → 急促释放，模拟负压节奏", 2.4, MEDIUM, _suction))
_register(_w("thrust", "抽送", "玩具模式", "推入快、退出慢的规律推拉", 0.9, STRONG, _thrust))
_register(_w("shake", "摇头", "玩具模式", "左右快速摆动，像拨浪鼓", 1.3, STRONG, _shake))
_register(_w("creep", "蠕动", "玩具模式", "缓慢爬行的强度变化，几乎察觉不到切换点", 5.0, MILD, _creep))
_register(_w("rattle", "抖动", "玩具模式", "高频小幅断续，像牙齿打颤", 1.8, MEDIUM, _rattle))
_register(_w("dj", "变频率", "玩具模式", "一圈内三段变速（慢→快→极快），像 DJ 搓碟", 3.6, STRONG, _dj))
_register(_w("purr", "咕噜", "玩具模式", "猫呼噜式的低频颤动，持续带颗粒感", 1.4, MILD, _purr))

# 节律引导
_register(_w("calm", "镇静节律", "节律引导",
             "慢速心跳，默认约 55 BPM。用速度滑杆可调 30~110 BPM —— "
             "慢于自身静息心率的节律有助于降唤醒、缓解紧张（Doppel 研究）",
             1.09, MILD, _calm))
_register(_w("energize", "提神节律", "节律引导",
             "快速心跳，默认约 109 BPM。速度调到 1.4x 约 150 BPM，用于唤醒/提神",
             0.55, MEDIUM, _energize))
_register(_w("breath478", "4-7-8 呼吸", "节律引导",
             "呼吸引导：吸气 4s → 屏息 7s → 呼气 8s，一圈 19s。"
             "震起来吸气，最强时屏息，弱下去时呼气",
             19.0, MILD, _breath478))
_register(_w("melt", "融化", "节律引导", "强度整体缓慢滑落再缓缓拉起，没有明显节拍", 6.0, MILD, _melt))
_register(_w("float", "失重", "节律引导", "缓慢漂浮，几乎无节拍，适合长时间挂着", 8.0, MILD, _float))

# 彩蛋
_register(_w("egg577", "577", "彩蛋",
             "作者 577 的专属波形。一圈约 24 秒，走完六幕："
             "铺垫 → 挑逗 → 涌动 → 加速 → 边缘 → 收束。"
             "整库的手段串成一条线，建议强度留到 70% 以上再点。",
             24.0, EXTREME, _577))


CATEGORY_ORDER = ("基础", "按摩手法", "节奏冲击", "波形起伏", "刺激",
                  "玩具模式", "节律引导", "特殊", "彩蛋")


def waveforms_by_category() -> list[tuple[str, list[Waveform]]]:
    out: list[tuple[str, list[Waveform]]] = []
    for cat in CATEGORY_ORDER:
        items = [w for w in WAVEFORMS.values() if w.category == cat]
        if items:
            out.append((cat, items))
    return out


# ================================================================ 自定义曲线


CurvePoints = Sequence[tuple[float, float]]


def eval_curve(points: CurvePoints, phase: float) -> float:
    """在归一化时间轴上对控制点做线性插值，首尾自动闭合循环。

    points: [(t, v), ...]，t 与 v 均在 0~1。t 无需排序、无需覆盖 0 和 1。
    """
    pts = sorted(points)
    n = len(pts)
    if n == 0:
        return 0.0
    if n == 1:
        return clamp01(pts[0][1])

    p = phase % 1.0
    for i in range(n):
        t0, v0 = pts[i]
        t1, v1 = pts[(i + 1) % n]
        if i == n - 1:
            t1 += 1.0
            if p < t0:
                p += 1.0
        if t0 <= p <= t1:
            span = t1 - t0
            if span <= 1e-9:
                return clamp01(v1)
            return clamp01(v0 + (v1 - v0) * ((p - t0) / span))
    return clamp01(pts[0][1])


DEFAULT_CURVE: list[tuple[float, float]] = [
    (0.0, 0.10),
    (0.22, 1.00),
    (0.42, 0.25),
    (0.62, 0.85),
    (0.80, 0.15),
]


# ================================================================ 随机搭配


@dataclass
class RandomPreset:
    """一次「随机搭配」的结果。字段名和 EngineParams 对齐，可以直接 update_params。"""

    waveform: str
    waveform_b: str
    mix: float
    speed: float
    floor: float
    phase_shift: float
    smoothing: float
    beam_enabled: bool
    beam_position: float
    beam_width: float
    beam_sweep: bool
    beam_sweep_rate: float
    beam_beat_hz: float
    beam_polarity: str
    sharpen: float
    noise_floor: float
    anti_adapt: float
    duty: float

    def to_params(self) -> dict:
        return {
            "waveform": self.waveform,
            "waveform_b": self.waveform_b,
            "mix": self.mix,
            "speed": self.speed,
            "floor": self.floor,
            "phase_shift": self.phase_shift,
            "smoothing": self.smoothing,
            "beam_enabled": self.beam_enabled,
            "beam_position": self.beam_position,
            "beam_width": self.beam_width,
            "beam_sweep": self.beam_sweep,
            "beam_sweep_rate": self.beam_sweep_rate,
            "beam_beat_hz": self.beam_beat_hz,
            "beam_polarity": self.beam_polarity,
            "sharpen": self.sharpen,
            "noise_floor": self.noise_floor,
            "anti_adapt": self.anti_adapt,
            "duty": self.duty,
        }


def random_preset(rng: random.Random | None = None, *, spicy: bool = False,
                  beam_allowed: bool = True) -> RandomPreset:
    """随机搭配一套完整的震动参数。

    spicy=True 时只在「刺激 / 极刺激」档位里挑波形，适合直接上强度。
    mix>0 时会额外挑一个波形做混合，混出原库里没有的新节奏。
    """
    rng = rng or random
    pool = [w for w in WAVEFORMS.values() if w.key != "custom"]
    if spicy:
        hot = [w for w in pool if w.intensity in (STRONG, EXTREME)]
        if hot:
            pool = hot

    main = rng.choice(pool)
    other = rng.choice(pool)
    while other.key == main.key and len(pool) > 1:
        other = rng.choice(pool)

    blend = rng.random()
    mixed = blend < 0.45          # 45% 概率做双波形混合
    use_beam = beam_allowed and rng.random() < 0.7

    return RandomPreset(
        waveform=main.key,
        waveform_b=other.key if mixed else "",
        mix=round(rng.uniform(0.25, 0.6), 2) if mixed else 0.0,
        speed=round(rng.uniform(0.6, 1.8), 2),
        floor=round(rng.choice([0.0, 0.0, 0.08, 0.15, 0.25]) if rng.random() < 0.6
                    else rng.uniform(0.0, 0.35), 2),
        phase_shift=round(rng.choice([0.0, 0.25, 0.5, 0.5, 0.75]), 2),
        smoothing=round(rng.uniform(0.0, 0.45), 2),
        beam_enabled=use_beam,
        beam_position=round(rng.uniform(-0.85, 0.85), 2),
        beam_width=round(rng.uniform(0.15, 0.75), 2),
        beam_sweep=use_beam and rng.random() < 0.5,
        beam_sweep_rate=round(rng.uniform(0.10, 0.85), 2),
        beam_beat_hz=round(rng.choice([0.0, 0.0, 1.5, 2.5, 4.0, 6.0]), 1)
                     if use_beam and rng.random() < 0.55 else 0.0,
        beam_polarity=rng.choice(["in", "in", "out"]),
        sharpen=round(rng.uniform(0.4, 1.0), 2) if rng.random() < 0.75 else 0.0,
        noise_floor=round(rng.uniform(0.25, 1.0), 2) if rng.random() < 0.40 else 0.0,
        anti_adapt=round(rng.uniform(0.3, 1.0), 2) if rng.random() < 0.60 else 0.0,
        duty=round(rng.choice([1.0, 1.0, 1.0, 0.7, 0.5, 0.35]), 2),
    )

