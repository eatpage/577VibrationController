"""聆听波束面板 —— 用立体声「听」到波束的位置与移动。

手柄的两个马达天然就是一组立体声：
    左马达的振动包络 → 左声道
    右马达的振动包络 → 右声道
所以把这两路包络渲染成音频播放出来，波束扫到哪边，声音就偏向哪边。
这是本程序里唯一能「立刻用耳朵验证波束」的手段。
"""

from __future__ import annotations

import math
import time
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.audio import TIMBRES
from core.i18n import tr

from . import theme
from .widgets import AnimatedButton, LabeledSlider

BAR_COUNT = 72


class BeamScope(QWidget):
    """波束空间分布 + 左右电平 + 行波动画。

    支持直接在图上点击/拖动来设定波束位置，比拖滑杆直观得多。
    """

    positionDragged = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self.position = 0.0        # -1..1
        self.width_ratio = 0.45    # 0..1
        self.level_l = 0.0
        self.level_r = 0.0
        self.active = False
        self.listening = False
        self.audio_l = 0.0
        self.audio_r = 0.0
        self._t0 = time.perf_counter()
        self._label_left = tr("左握把")
        self._label_mid = tr("中央聚合")
        self._label_right = tr("右握把")
        self._dragging = False

    # ---------------------------------------------------------- 交互

    def _plot_rect(self) -> QRectF:
        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        meter_w = 30.0
        return rect.adjusted(meter_w + 14.0, 14.0, -(meter_w + 14.0), -26.0)

    def _pos_from_x(self, x: float) -> float:
        plot = self._plot_rect()
        if plot.width() <= 1:
            return 0.0
        ratio = (x - plot.left()) / plot.width()
        return max(-1.0, min(1.0, ratio * 2.0 - 1.0))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.positionDragged.emit(self._pos_from_x(event.position().x()))

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self.positionDragged.emit(self._pos_from_x(event.position().x()))

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    # ---------------------------------------------------------- 状态

    def set_state(self, *, position: float, width_ratio: float,
                  level_l: float, level_r: float, active: bool,
                  listening: bool, audio_l: float = 0.0, audio_r: float = 0.0) -> None:
        self.position = position
        self.width_ratio = width_ratio
        self.level_l = level_l
        self.level_r = level_r
        self.active = active
        self.listening = listening
        self.audio_l = audio_l
        self.audio_r = audio_r

    # ---------------------------------------------------------- 绘制

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        painter.setPen(QPen(QColor(theme.BORDER), 1.0))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(rect, 10.0, 10.0)

        meter_w = 30.0
        plot = rect.adjusted(meter_w + 14.0, 14.0, -(meter_w + 14.0), -26.0)
        if plot.width() < 20 or plot.height() < 10:
            return

        self._draw_axis(painter, rect)
        self._draw_energy_field(painter, plot)
        self._draw_meters(painter, rect, meter_w)
        self._draw_beam_marker(painter, plot)

    def _draw_axis(self, painter: QPainter, rect: QRectF) -> None:
        font = QFont(self.font())
        font.setPointSizeF(max(8.0, font.pointSizeF() - 1.0))
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT_MUTED))
        y = rect.bottom() - 8.0
        for text, x, align in (
            (self._label_left, rect.left() + 12.0, Qt.AlignmentFlag.AlignLeft),
            (self._label_mid, rect.center().x(), Qt.AlignmentFlag.AlignHCenter),
            (self._label_right, rect.right() - 12.0, Qt.AlignmentFlag.AlignRight),
        ):
            metrics = painter.fontMetrics()
            w = metrics.horizontalAdvance(text)
            if align == Qt.AlignmentFlag.AlignLeft:
                painter.drawText(QPointF(x, y), text)
            elif align == Qt.AlignmentFlag.AlignRight:
                painter.drawText(QPointF(x - w, y), text)
            else:
                painter.drawText(QPointF(x - w / 2.0, y), text)

    def _draw_energy_field(self, painter: QPainter, plot: QRectF) -> None:
        """横轴 = 手柄上的空间位置，竖条高度 = 该处的振动强度。"""
        center_x = plot.left() + (self.position + 1.0) * 0.5 * plot.width()
        half = plot.width() * (0.10 + self.width_ratio * 0.42)

        drive = max(self.level_l, self.level_r)
        base = plot.bottom()
        t = time.perf_counter() - self._t0

        step = plot.width() / BAR_COUNT
        bar_w = max(1.5, step * 0.62)

        for i in range(BAR_COUNT):
            x = plot.left() + step * (i + 0.5)
            d = (x - center_x) / max(1.0, half)
            shape = math.exp(-d * d * 1.6)

            # 行波动画：让分布看起来是活的
            ripple = 1.0 if not self.active else (
                0.72 + 0.28 * math.sin(t * 5.2 - d * 3.4 + i * 0.08)
            )
            height = shape * ripple * (0.22 + 0.78 * drive) * plot.height()
            height = max(1.6, height)

            # 未启用波束时画一条扁平的基线，表示没有定位
            if not self.active:
                height = 0.10 * plot.height()

            color = QColor(theme.LEFT_COLOR)
            color.setAlpha(int(90 + 140 * shape))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)

            r = QRectF(x - bar_w / 2.0, base - height, bar_w, height)
            painter.drawRoundedRect(r, bar_w * 0.45, bar_w * 0.45)

    def _draw_beam_marker(self, painter: QPainter, plot: QRectF) -> None:
        """波束重心：一圈发光标记。"""
        x = plot.left() + (self.position + 1.0) * 0.5 * plot.width()
        y = plot.top() + plot.height() * 0.34

        radius = 56.0 + 26.0 * (1.0 - self.width_ratio)
        glow = QRadialGradient(QPointF(x, y), radius)
        c0 = QColor(theme.ACCENT)
        c0.setAlpha(120 if self.active else 40)
        c1 = QColor(theme.ACCENT)
        c1.setAlpha(0)
        glow.setColorAt(0.0, c0)
        glow.setColorAt(1.0, c1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(x, y), radius, radius * 0.78)

        head = QColor(theme.ACCENT_PRESSED if self.active else theme.OFF)
        painter.setBrush(head)
        painter.drawEllipse(QPointF(x, y), 5.0, 5.0)

        if self.active:
            painter.setPen(QPen(head, 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

    def _draw_meters(self, painter: QPainter, rect: QRectF, meter_w: float) -> None:
        font = QFont(self.font())
        font.setPointSizeF(max(7.5, font.pointSizeF() - 1.5))
        painter.setFont(font)

        top = rect.top() + 14.0
        bottom = rect.bottom() - 26.0
        height = bottom - top

        for side, x, level, color in (
            ("左", rect.left() + 8.0, self.level_l, theme.LEFT_COLOR),
            ("右", rect.right() - 8.0 - meter_w, self.level_r, theme.RIGHT_COLOR),
        ):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT_SOFT))
            painter.drawRoundedRect(QRectF(x, top, meter_w, height), 4.0, 4.0)

            h = max(0.0, min(1.0, level)) * height
            if h > 0.5:
                grad = QLinearGradient(0.0, bottom, 0.0, top)
                grad.setColorAt(0.0, QColor(color))
                bright = QColor(color)
                bright.setAlpha(220)
                grad.setColorAt(1.0, bright)
                painter.setBrush(grad)
                painter.drawRoundedRect(QRectF(x, bottom - h, meter_w, h), 4.0, 4.0)

            painter.setPen(QColor(theme.TEXT_MUTED))
            metrics = painter.fontMetrics()
            label = tr(side)
            painter.drawText(
                QPointF(x + meter_w / 2.0 - metrics.horizontalAdvance(label) / 2.0,
                        bottom + 13.0),
                label,
            )


class BeamPanel(QFrame):
    """「聆听波束」面板：开关 + 空间可视化 + 音量 + 音色。"""

    listenToggled = Signal(bool)
    volumeChanged = Signal(float)
    timbreChanged = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BeamPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # ---- 标题行 ----
        head = QHBoxLayout()
        head.setSpacing(10)

        title = QLabel("聆听波束")
        title.setObjectName("BeamTitle")
        head.addWidget(title)

        sub = QLabel("双马达立体声　·　左马达→左声道　右马达→右声道　·　用耳朵直接听波束的位置与移动")
        sub.setObjectName("Hint")
        head.addWidget(sub)
        head.addStretch(1)

        self.status = QLabel("未开启")
        self.status.setObjectName("BeamStatus")
        head.addWidget(self.status)

        self.listen_btn = AnimatedButton("开 启 聆 听")
        self.listen_btn.setObjectName("ListenButton")
        self.listen_btn.setCheckable(True)
        self.listen_btn.setProperty("listening", "false")
        self.listen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.listen_btn.setMinimumWidth(148)
        self.listen_btn.toggled.connect(self._on_toggle)
        head.addWidget(self.listen_btn)

        root.addLayout(head)

        # ---- 可视化 ----
        self.scope = BeamScope()
        root.addWidget(self.scope)

        # ---- 控制行 ----
        row = QHBoxLayout()
        row.setSpacing(14)

        self.volume = LabeledSlider(
            "音量", 0.0, 1.0, 0.55,
            formatter=lambda v: f"{v * 100:.0f}%",
            tooltip="聆听波束的播放音量",
        )
        self.volume.valueChanged.connect(self.volumeChanged.emit)
        row.addWidget(self.volume, 1)

        row.addWidget(QLabel("音色"))
        self.timbre_combo = QComboBox()
        self.timbre_combo.setMinimumWidth(140)
        for key, (name, freq, kind) in TIMBRES.items():
            hint = "噪声" if kind == "noise" else f"{freq:.0f}Hz"
            self.timbre_combo.addItem(f"{name}　{hint}", key)
        self.timbre_combo.currentIndexChanged.connect(
            lambda _i: self.timbreChanged.emit(self.timbre_combo.currentData())
        )
        row.addWidget(self.timbre_combo)

        root.addLayout(row)

    # ---------------------------------------------------------- 内部

    def _on_toggle(self, checked: bool) -> None:
        self.listen_btn.setText(tr("关 闭 聆 听") if checked else tr("开 启 聆 听"))
        self.listen_btn.setProperty("listening", "true" if checked else "false")
        from .widgets import refresh_style
        refresh_style(self.listen_btn)
        self.listen_btn.set_sound("listen_on" if checked else "listen_off")
        self.listenToggled.emit(checked)

    # ---------------------------------------------------------- 对外

    def is_listening(self) -> bool:
        return self.listen_btn.isChecked()

    def set_listening(self, value: bool) -> None:
        self.listen_btn.setChecked(value)

    def set_status(self, text: str, warn: bool = False) -> None:
        self.status.setText(text)
        self.status.setProperty("warn", "true" if warn else "false")
        from .widgets import refresh_style
        refresh_style(self.status)

    def set_timbre(self, key: str) -> None:
        idx = self.timbre_combo.findData(key)
        if idx >= 0:
            self.timbre_combo.blockSignals(True)
            self.timbre_combo.setCurrentIndex(idx)
            self.timbre_combo.blockSignals(False)
