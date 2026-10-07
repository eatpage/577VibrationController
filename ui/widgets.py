"""自定义控件：涟漪动效按钮、带数值的滑杆、波形按钮、状态灯、卡片。"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core import sfx

from . import theme

# 滑杆标题列宽。各语言标题长度差别很大，由界面在切换语言时统一重算。
DEFAULT_TITLE_WIDTH = 58


class Card(QFrame):
    """带标题的圆角卡片。"""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(9)
        if title:
            label = QLabel(title)
            label.setObjectName("CardTitle")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


# ==================================================================== 动效按钮


class AnimatedButton(QPushButton):
    """点击时从鼠标位置扩散一圈涟漪，并播放合成音效。"""

    default_sound = "click"
    corner_radius = 8.0

    def __init__(self, *args, parent: Optional[QWidget] = None, **kwargs) -> None:
        super().__init__(*args, parent, **kwargs)
        self._progress = 0.0
        self._origin = QPointF(0.0, 0.0)
        self._tint = QColor(theme.ACCENT)
        self._sound_enabled = True
        self._sound_name = type(self).default_sound

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(340)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_progress)
        self._anim.finished.connect(self._on_anim_finished)
        self.pressed.connect(self._on_pressed)

    # -- 可配置 ------------------------------------------------

    def set_sound(self, name: str) -> None:
        self._sound_name = name

    def set_sound_enabled(self, enabled: bool) -> None:
        self._sound_enabled = enabled

    def set_ripple_color(self, color) -> None:
        self._tint = QColor(color)

    # -- 内部 --------------------------------------------------

    def _on_pressed(self) -> None:
        if self._sound_enabled:
            sfx.player().play(self._sound_name)
        local = self.mapFromGlobal(QCursor.pos())
        self._origin = QPointF(float(local.x()), float(local.y()))
        self._progress = 0.0
        self._anim.stop()
        self._anim.start()

    def _on_progress(self, value) -> None:
        self._progress = float(value)
        self.update()

    def _on_anim_finished(self) -> None:
        self._progress = 0.0
        self.update()

    # -- 绘制 --------------------------------------------------

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not (0.0 < self._progress < 1.0):
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 裁到圆角矩形内，涟漪不会溢出按钮
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            self.corner_radius,
            self.corner_radius,
        )
        painter.setClipPath(path)

        reach = max(self.width(), self.height()) * 1.15
        radius = self._progress * reach

        fill = QColor(self._tint)
        fill.setAlpha(int(140 * (1.0 - self._progress) ** 1.4))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawEllipse(self._origin, radius, radius)

        ring = QColor(self._tint)
        ring.setAlpha(int(90 * (1.0 - self._progress) ** 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(ring, 2.0))
        inner = max(0.1, radius - 2.0)
        painter.drawEllipse(self._origin, inner, inner)


class WaveButton(AnimatedButton):
    """波形选择按钮（可选中）。"""

    default_sound = "wave"
    corner_radius = 9.0

    def __init__(self, key: str, name: str, tooltip: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(name, parent)
        self.key = key
        self.setObjectName("WaveButton")
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)


class PillButton(AnimatedButton):
    """次要动作按钮。"""

    default_sound = "click"
    corner_radius = 8.0


# ==================================================================== 滑杆


def measure_title_width(font, titles) -> int:
    """按当前语言测出合适的一列标题宽度，保证同栏滑杆对齐。"""
    from PySide6.QtGui import QFontMetrics

    fm = QFontMetrics(font)
    widest = max((fm.horizontalAdvance(t) for t in titles), default=0)
    return max(52, widest + 12)


class LabeledSlider(QWidget):
    """一行滑杆：标题 | 滑杆 | 数值。

    内部用 0~1000 的整数刻度，对外暴露浮点值 [minimum, maximum]。

    标题列宽默认取模块级的 `DEFAULT_TITLE_WIDTH` —— 各语言标题长度差很多
    （中文 3 个字，俄语可能 12 个字母），由界面在切换语言时统一算一次，
    这样同一栏里所有滑杆仍然对齐。
    """

    valueChanged = Signal(float)

    def __init__(
        self,
        title: str,
        minimum: float,
        maximum: float,
        value: float,
        *,
        decimals: int = 0,
        suffix: str = "",
        formatter: Optional[Callable[[float], str]] = None,
        title_width: Optional[int] = None,
        tooltip: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.decimals = decimals
        self.suffix = suffix
        self._formatter = formatter
        self._ticks = 1000
        width = DEFAULT_TITLE_WIDTH if title_width is None else title_width

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SliderTitle")
        self.title_label.setFixedWidth(width)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self._ticks)
        self.slider.setSingleStep(5)
        self.slider.setPageStep(50)
        self.slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.value_label = QLabel("")
        self.value_label.setObjectName("SliderValue")
        self.value_label.setFixedWidth(56)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(self.title_label)
        row.addWidget(self.slider, 1)
        row.addWidget(self.value_label)

        if tooltip:
            self.setToolTip(tooltip)

        self.slider.valueChanged.connect(self._on_slider)
        self.slider.sliderPressed.connect(lambda: sfx.player().play("tick"))
        self.slider.sliderReleased.connect(lambda: sfx.player().play("tick"))
        self.set_value(value, emit=False)

    def _on_slider(self, tick: int) -> None:
        self.value_label.setText(self._format(self._from_tick(tick)))
        self.valueChanged.emit(self._from_tick(tick))

    def _from_tick(self, tick: int) -> float:
        return self.minimum + (self.maximum - self.minimum) * (tick / self._ticks)

    def _to_tick(self, value: float) -> int:
        span = self.maximum - self.minimum
        if span <= 0:
            return 0
        ratio = (value - self.minimum) / span
        return int(round(max(0.0, min(1.0, ratio)) * self._ticks))

    def _format(self, value: float) -> str:
        if self._formatter is not None:
            return self._formatter(value)
        return f"{value:.{self.decimals}f}{self.suffix}"

    # -- 公开 API --------------------------------------------

    def value(self) -> float:
        return self._from_tick(self.slider.value())

    def set_value(self, value: float, *, emit: bool = True) -> None:
        tick = self._to_tick(value)
        blocked = self.slider.blockSignals(True)
        self.slider.setValue(tick)
        self.slider.blockSignals(blocked)
        self.value_label.setText(self._format(self._from_tick(tick)))
        if emit:
            self.valueChanged.emit(self._from_tick(tick))


# ==================================================================== 其它


class StatusDot(QWidget):
    """小圆点状态灯。"""

    def __init__(self, diameter: int = 11, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._diameter = diameter
        self._color = QColor(theme.OFF)
        self.setFixedSize(diameter + 4, diameter + 4)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        halo = QColor(self._color)
        halo.setAlpha(60)
        painter.setBrush(halo)
        painter.drawEllipse(0, 0, self._diameter + 4, self._diameter + 4)

        painter.setBrush(self._color)
        painter.drawEllipse(2, 2, self._diameter, self._diameter)


class Separator(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {theme.BORDER}; border: none;")


def refresh_style(widget: QWidget) -> None:
    """改了动态属性之后重新应用样式表。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()
