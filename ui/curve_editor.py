"""自定义波形曲线编辑器 —— 手绘「时间-强度」曲线并循环播放。

左键空白处新增控制点并拖动 · 左键拖动已有控制点 · 右键删除控制点。
首尾自动闭合，保证无缝循环。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import theme

HIT_RADIUS = 9.0
MIN_POINTS = 2


class CurveEditor(QWidget):
    pointsChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._points: list[list[float]] = [[0.0, 0.10], [0.22, 1.0], [0.42, 0.25], [0.62, 0.85], [0.80, 0.15]]
        self._drag_index: Optional[int] = None
        self._phase = 0.0
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ---------------------------------------------------------- 数据

    def points(self) -> list[tuple[float, float]]:
        return [(float(t), float(v)) for t, v in sorted(self._points)]

    def set_points(self, points) -> None:
        cleaned: list[list[float]] = []
        for item in points or []:
            try:
                t = float(item[0])
                v = float(item[1])
            except Exception:
                continue
            cleaned.append([max(0.0, min(1.0, t)), max(0.0, min(1.0, v))])
        self._points = cleaned
        self.update()
        self.pointsChanged.emit()

    def reset_flat(self, level: float = 0.6) -> None:
        self._points = [[0.0, level], [0.5, level]]
        self.update()
        self.pointsChanged.emit()

    def clear_all(self) -> None:
        self._points = []
        self.update()
        self.pointsChanged.emit()

    def set_phase(self, phase: float) -> None:
        self._phase = phase % 1.0
        self.update()

    # ---------------------------------------------------------- 几何

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(30.0, 12.0, -12.0, -24.0)

    def _to_pixel(self, t: float, v: float) -> QPointF:
        plot = self._plot_rect()
        return QPointF(plot.left() + t * plot.width(), plot.bottom() - v * plot.height())

    def _to_value(self, pos: QPointF) -> tuple[float, float]:
        plot = self._plot_rect()
        if plot.width() <= 0 or plot.height() <= 0:
            return 0.0, 0.0
        t = (pos.x() - plot.left()) / plot.width()
        v = (plot.bottom() - pos.y()) / plot.height()
        return max(0.0, min(1.0, t)), max(0.0, min(1.0, v))

    def _find_point(self, pos: QPointF) -> Optional[int]:
        best: Optional[int] = None
        best_d = HIT_RADIUS
        for i, (t, v) in enumerate(self._points):
            p = self._to_pixel(t, v)
            d = ((p.x() - pos.x()) ** 2 + (p.y() - pos.y()) ** 2) ** 0.5
            if d <= best_d:
                best_d = d
                best = i
        return best

    # ---------------------------------------------------------- 交互

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        if not self._plot_rect().adjusted(-6, -6, 6, 6).contains(pos):
            return

        if event.button() == Qt.MouseButton.RightButton:
            idx = self._find_point(pos)
            if idx is not None and len(self._points) > MIN_POINTS:
                del self._points[idx]
                self.update()
                self.pointsChanged.emit()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._find_point(pos)
            if idx is None:
                t, v = self._to_value(pos)
                self._points.append([t, v])
                idx = len(self._points) - 1
                self.pointsChanged.emit()
            self._drag_index = idx
            self._move_point(idx, pos)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_index is not None:
            self._move_point(self._drag_index, event.position())
        else:
            idx = self._find_point(event.position())
            self.setCursor(
                Qt.CursorShape.OpenHandCursor if idx is not None else Qt.CursorShape.CrossCursor
            )

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_index is not None:
            self._drag_index = None
            self._points.sort(key=lambda item: item[0])
            self.update()
            self.pointsChanged.emit()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            idx = self._find_point(event.position())
            if idx is not None and len(self._points) > MIN_POINTS:
                del self._points[idx]
                self.update()
                self.pointsChanged.emit()

    def _move_point(self, index: int, pos: QPointF) -> None:
        if index is None or not (0 <= index < len(self._points)):
            return
        t, v = self._to_value(pos)
        self._points[index][0] = t
        self._points[index][1] = v
        self.update()

    def wheelEvent(self, event) -> None:
        # 滚轮微调选中点的高度，便于精调
        idx = self._find_point(event.position())
        if idx is None:
            super().wheelEvent(event)
            return
        delta = 0.02 if event.angleDelta().y() > 0 else -0.02
        self._points[idx][1] = max(0.0, min(1.0, self._points[idx][1] + delta))
        self.update()
        self.pointsChanged.emit()

    # ---------------------------------------------------------- 绘制

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        outer = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        painter.setPen(QPen(QColor(theme.BORDER), 1.0))
        painter.setBrush(QColor(theme.PANEL))
        painter.drawRoundedRect(outer, 10.0, 10.0)

        plot = self._plot_rect()
        if plot.width() <= 4 or plot.height() <= 4:
            return

        # 网格
        painter.setPen(QPen(QColor(theme.GRID), 1.0))
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = plot.bottom() - plot.height() * frac
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = plot.left() + plot.width() * frac
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        # 轴标签
        font = QFont(self.font())
        font.setPointSizeF(max(8.0, font.pointSizeF() - 1.0))
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT_MUTED))
        for frac, text in ((1.0, "100%"), (0.5, " 50%"), (0.0, "  0%")):
            y = plot.bottom() - plot.height() * frac
            painter.drawText(QPointF(plot.left() - 28.0, y + 4.0), text)
        painter.drawText(
            QPointF(plot.left(), plot.bottom() + 15.0), "循环起点"
        )
        end_text = "循环终点"
        painter.drawText(
            QPointF(plot.right() - painter.fontMetrics().horizontalAdvance(end_text), plot.bottom() + 15.0),
            end_text,
        )

        # 采样参考曲线（每像素采样，还原真实插值形状）
        pts = self.points()
        if len(pts) >= 1:
            poly = QPolygonF()
            steps = max(2, int(plot.width()))
            from core.waveforms import eval_curve

            for i in range(steps + 1):
                t = i / steps
                v = eval_curve(pts, t)
                poly.append(self._to_pixel(t, v))

            fill = QPolygonF(poly)
            fill.append(QPointF(plot.right(), plot.bottom()))
            fill.append(QPointF(plot.left(), plot.bottom()))
            fill_color = QColor(theme.ACCENT)
            fill_color.setAlpha(30)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawPolygon(fill)

            pen = QPen(QColor(theme.ACCENT), 2.0)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(poly)

        # 播放头
        px = plot.left() + plot.width() * self._phase
        head_pen = QPen(QColor(theme.ACCENT_PRESSED), 1.2, Qt.PenStyle.DashLine)
        painter.setPen(head_pen)
        painter.drawLine(QPointF(px, plot.top()), QPointF(px, plot.bottom()))

        # 控制点
        for i, (t, v) in enumerate(self._points):
            p = self._to_pixel(t, v)
            active = (i == self._drag_index)
            painter.setPen(QPen(QColor(theme.ACCENT_PRESSED), 2.0))
            painter.setBrush(QColor(theme.ACCENT) if active else QColor("#FFFFFF"))
            painter.drawEllipse(p, 5.0, 5.0)

        if not self._points:
            painter.setPen(QColor(theme.TEXT_MUTED))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "点击空白处添加控制点")
