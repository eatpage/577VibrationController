"""虚拟波束 —— 用两个偏心转子马达做出「体感定位」效果。

【先说清楚物理边界，避免误解】
真正的振动聚焦（在一个内部点汇聚能量）需要大量激振器组成的相控阵列 + 精确相位控制。
手柄只有两个 ERM（偏心转子）马达，间距十几厘米、启停迟滞几十毫秒，
**物理上无法在内部形成聚焦点**。所以本模块做的是三件真实成立的事：

1. 振幅声像（amplitude panning）—— 真实。体感重心在左右握把之间移动。
2. 拍频干涉（beat）—— **真实物理**。两个马达转速略有差异时，
   合成振幅会以 |fL − fR| 的节拍周期性起伏，人会明显感觉到一阵阵的涌动。
3. 同相聚合 / 反相分离 —— 人耳／体感层面的**错觉**。
   同相时（两马达同步）中枢会把两路信号整合成「中间一个更强的振源」；
   反相时（错开半个周期）感知为「两边轮流」。这就是体感版的立体声定位原理

模块对外只暴露纯粹的数学运算，不碰线程和 UI，方便单元测试。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

TAU = math.tau


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else (hi if x > hi else x)


def clamp01(x: float) -> float:
    return clamp(x, 0.0, 1.0)


@dataclass
class BeamParams:
    enabled: bool = False

    # 波束位置：-1.0 = 最左握把，0.0 = 中央聚合，+1.0 = 最右握把
    position: float = 0.0

    # 波束宽度：0 = 极聚焦（一点点偏移就明显偏向一侧），1 = 极弥散（几乎全宽）
    width: float = 0.45

    # 自动扫掠
    sweep_enabled: bool = False
    sweep_rate: float = 0.5        # Hz，来回一趟的速度
    sweep_depth: float = 0.85      # 0~1，扫掠幅度（相对整个行程）

    # 拍频干涉（真实物理现象）
    beat_hz: float = 0.0           # 0 = 关闭；1~6Hz 是体感最明显的区间
    beat_depth: float = 0.75       # 0~1，起伏深度

    # 极性：in = 同相（聚合在中间），out = 反相（两边轮流）
    polarity: str = "in"


class BeamProcessor:
    """把「标量波形值」转成左右两路的增益与拍频包络。"""

    def __init__(self) -> None:
        self._sweep_phase = 0.0

    def reset(self) -> None:
        self._sweep_phase = 0.0

    # ---------------------------------------------------------- 位置

    def effective_position(self, params: BeamParams, dt: float) -> float:
        """当前波束位置（含自动扫掠）。返回值域 [-1, 1]。"""
        pos = clamp(params.position, -1.0, 1.0)

        if params.sweep_enabled:
            self._sweep_phase = (self._sweep_phase + dt * max(0.01, params.sweep_rate)) % 1.0
            # 三角波扫掠：比正弦更有「来回移动」的机械感
            tri = 1.0 - abs(2.0 * self._sweep_phase - 1.0)   # 0..1..0
            offset = (tri * 2.0 - 1.0) * clamp(params.sweep_depth, 0.0, 1.0)
            pos = clamp(pos + offset, -1.0, 1.0)

        return pos

    # ---------------------------------------------------------- 声像增益

    @staticmethod
    def pan_gains(position: float) -> tuple[float, float]:
        """按位置算左右增益。

        位置 = 0（居中）时两路都是 1.0 —— 这就是「聚合」：两路同幅，
        中枢会把它感知为一个更靠中间、更强的振源。
        位置偏向一侧时，另一侧线性衰减到 0。
        """
        x = (clamp(position, -1.0, 1.0) + 1.0) * 0.5    # 0..1
        half = 0.5
        gain_l = clamp01(1.0 - max(0.0, x - 0.5) / half)
        gain_r = clamp01(1.0 - max(0.0, 0.5 - x) / half)
        return gain_l, gain_r

    @staticmethod
    def focus_gains(position: float, width: float) -> tuple[float, float]:
        """带宽度控制的声像增益。width 越小越聚焦。"""
        x = (clamp(position, -1.0, 1.0) + 1.0) * 0.5
        half = 0.04 + clamp01(width) * 0.46
        gain_l = clamp01(1.0 - max(0.0, x - 0.5) / half)
        gain_r = clamp01(1.0 - max(0.0, 0.5 - x) / half)
        return gain_l, gain_r

    # ---------------------------------------------------------- 拍频

    @staticmethod
    def beat_envelope(beat_hz: float, beat_depth: float, t: float) -> float:
        """两个转速略有差异的马达叠加后的合成振幅包络。

        真实的物理拍频：a·cos(2πf₁t) + a·cos(2πf₂t)
                          = 2a·cos(2π((f₁+f₂)/2)t)·cos(2π((f₁−f₂)/2)t)
        第二项就是缓慢的拍频包络。这里直接用它的形状。
        """
        if beat_hz <= 0.01 or beat_depth <= 0.001:
            return 1.0
        wave = 0.5 - 0.5 * math.cos(TAU * beat_hz * t)
        return clamp01(1.0 - clamp01(beat_depth) * wave)

    # ---------------------------------------------------------- 主入口

    def process(
        self,
        wave_l: float,
        wave_r: float,
        params: BeamParams,
        dt: float,
        t: float,
    ) -> tuple[float, float, float]:
        """返回 (左值, 右值, 当前波束位置)。输入输出均为 0~1 的标量。"""
        if not params.enabled:
            return clamp01(wave_l), clamp01(wave_r), params.position

        position = self.effective_position(params, dt)
        gain_l, gain_r = self.focus_gains(position, params.width)
        beat = self.beat_envelope(params.beat_hz, params.beat_depth, t)

        left = clamp01(wave_l * gain_l * beat)
        right = clamp01(wave_r * gain_r * beat)
        return left, right, position

    @staticmethod
    def polarity_phase_shift(params: BeamParams) -> float:
        """极性决定右马达相对左马达的相位偏移（占循环比例）。"""
        return 0.5 if params.polarity == "out" else 0.0
