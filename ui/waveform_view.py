"""实时输出可视化 —— 把引擎最近的历史样本画成双通道曲线。"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.i18n import tr

from . import theme

Samples = list[tuple[float, float]]


class WaveformView(QWidget):
    """实时曲线：粉线 = 左马达（大），紫线 = 右马达（小）。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._source: Callable[[], Samples] = lambda: []
        self._running = False
        self._left_raw = 0
        self._right_raw = 0
        self.setMinimumHeight(132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---------------------------------------------------------- API

    def set_source(self, fn: Callable[[], Samples]) -> None:
        self._source = fn

    def set_state(self, running: bool, left_raw: int, right_raw: int) -> None:
        self._running = running
        self._left_raw = left_raw
        self._right_raw = right_raw

    # ---------------------------------------------------------- 绘制

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)

        # 背景
        painter.setPen(QPen(QColor(theme.BORDER), 1.0))
        painter.setBrush(QColor(theme.PANEL))
        painter.drawRoundedRect(rect, 10.0, 10.0)

        plot = rect.adjusted(10.0, 22.0, -10.0, -16.0)
        if plot.width() <= 4 or plot.height() <= 4:
            return

        # 网格
        grid_pen = QPen(QColor(theme.GRID), 1.0)
        painter.setPen(grid_pen)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = plot.bottom() - plot.height() * frac
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        samples = self._source() or []
        peak = max((max(pair) for pair in samples), default=0.0)

        if samples and self._running and peak > 0.002:
            self._draw_curve(painter, plot, samples, channel=0)
            self._draw_curve(painter, plot, samples, channel=1)
        elif not self._running:
            painter.setPen(QColor(theme.TEXT_MUTED))
            font = QFont(self.font())
            font.setPointSizeF(max(9.0, font.pointSizeF()))
            painter.setFont(font)
            painter.drawText(
                plot,
                Qt.AlignmentFlag.AlignCenter,
                tr("已停止  ·  点「开始震动」启动"),
            )

        # 顶部图例与实时读数
        self._draw_legend(painter, rect)

    def _draw_curve(self, painter: QPainter, plot: QRectF, samples: Samples, channel: int) -> None:
        n = len(samples)
        if n < 2:
            return

        color = QColor(theme.LEFT_COLOR if channel == 0 else theme.RIGHT_COLOR)
        poly = QPolygonF()
        step = plot.width() / float(n - 1)
        for i, pair in enumerate(samples):
            value = pair[channel]
            poly.append(QPointF(plot.left() + step * i, plot.bottom() - plot.height() * value))

        # 曲线下方的半透明填充
        fill = QPolygonF(poly)
        fill.append(QPointF(plot.right(), plot.bottom()))
        fill.append(QPointF(plot.left(), plot.bottom()))
        fill_color = QColor(color)
        fill_color.setAlpha(28)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill_color)
        painter.drawPolygon(fill)

        # 曲线本体
        pen = QPen(color, 1.8)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(poly)

        # 末端亮点
        if n:
            last = poly.at(n - 1)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(last, 3.2, 3.2)

    def _draw_legend(self, painter: QPainter, rect: QRectF) -> None:
        font = QFont(self.font())
        font.setPointSizeF(max(8.5, font.pointSizeF() - 0.5))
        painter.setFont(font)

        y = rect.top() + 14.0
        x = rect.left() + 12.0
        painter.setPen(Qt.PenStyle.NoPen)
        metrics = painter.fontMetrics()

        # 位置按实际文本宽度推进 —— 俄语标签比中文长得多，固定间距会撞在一起
        for label, color, raw in (
            (tr("左马达"), theme.LEFT_COLOR, self._left_raw),
            (tr("右马达"), theme.RIGHT_COLOR, self._right_raw),
        ):
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(x + 4.0, y - 3.0), 4.0, 4.0)
            painter.setPen(QColor(theme.TEXT))
            text = f"{label}  {raw:>5d} / 65535"
            painter.drawText(QPointF(x + 13.0, y + 1.0), text)
            painter.setPen(Qt.PenStyle.NoPen)
            x += 13.0 + metrics.horizontalAdvance(text) + 22.0

        painter.setPen(QColor(theme.TEXT_MUTED))
        hint = tr("最近约 4.8 秒")
        painter.drawText(
            QPointF(rect.right() - 12.0 - painter.fontMetrics().horizontalAdvance(hint), y + 1.0),
            hint,
        )
