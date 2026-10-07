"""主窗口。"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import config as cfg_module
from core import audio as audio_mod
from core import i18n, sfx, xinput_backend
from core.i18n import tr
from core.rumble_engine import SOURCE_AUDIO, SOURCE_MIX, SOURCE_WAVEFORM, RumbleEngine
from core.waveforms import WAVEFORMS, random_preset, waveforms_by_category

from . import theme
from . import widgets
from .beam_panel import BeamPanel
from .curve_editor import CurveEditor
from .manual import ManualDialog
from .waveform_view import WaveformView
from .widgets import Card, LabeledSlider, PillButton, StatusDot, WaveButton, refresh_style

APP_TITLE = "手柄震动 · 按摩控制器"
APP_SUBTITLE = "XInput 直驱　·　Xbox 兼容手柄　·　125Hz 持续重发"
AUTHOR = "577"

# 界面里所有滑杆的标题，用来按当前语言统一算一列标题宽度
SLIDER_TITLES = (
    "总强度", "左马达", "右马达", "混合比", "速度", "强度下限", "平滑", "相位差",
    "锐化强度", "漂移量", "底噪强度", "占空比",
    "位置", "聚焦度", "拍频", "扫掠速度",
    "低频→左", "中高→右", "采集灵敏度", "触发阈值", "轮换间隔", "音量",
)

DISCONNECT_HINT = (
    "未检测到手柄。请确认已用 2.4G 接收器或 USB 有线连接；"
    "蓝牙模式走 DInput，无法被 XInput 识别。"
)

NO_MIX = "（不混合）"

SOURCE_CHOICES = [
    ("只放波形", SOURCE_WAVEFORM),
    ("跟随音频", SOURCE_AUDIO),
    ("波形 × 音频", SOURCE_MIX),
]


def _bind_toggle(button: QPushButton, on_text: str, off_text: str) -> None:
    """把一个可选中按钮做成「开/关」两态开关。"""

    def handler(checked: bool) -> None:
        button.setText(tr(on_text if checked else off_text))
        button.setProperty("on", "true" if checked else "false")
        refresh_style(button)

    button.setCheckable(True)
    button.toggled.connect(handler)
    handler(button.isChecked())


def detect_system_language() -> str:
    """首次启动时按系统语言挑一个可用语言，认不出来就用中文。"""
    try:
        from PySide6.QtCore import QLocale

        name = QLocale.system().name().lower()      # 例如 zh_cn / ja_jp / ru_ru
    except Exception:
        return i18n.DEFAULT_LANGUAGE

    prefix = name.split("_")[0]
    mapping = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko", "ru": "ru"}
    return mapping.get(prefix, i18n.DEFAULT_LANGUAGE)


def _wrap_scroll(widget: QWidget) -> QScrollArea:
    """把标签页内容包进滚动区。

    否则当内容高于标签页可视区域时，Qt 会把内部卡片压缩到最小高度以下，
    按钮会被挤成一条线。
    """
    widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    return scroll


class MainWindow(QMainWindow):
    def __init__(self, engine: RumbleEngine) -> None:
        super().__init__()
        self.engine = engine
        self.backend = xinput_backend.get_backend()

        # ---- 音频 ----
        self.hub = audio_mod.AudioHub.instance()
        self.capture = audio_mod.LoopbackCapture()
        self.player = audio_mod.StereoBeamPlayer()
        self._loopback_devices: list[audio_mod.LoopbackDevice] = []

        engine.audio_provider = lambda: (self.capture.state.bass, self.capture.state.mid)
        engine.frame_sink = self.player.set_envelope

        self._wave_buttons: dict[str, WaveButton] = {}
        self._current_wave = "breath"
        self._selected_device = 0
        self._tick_count = 0
        self._last_phase = 0.0
        self._auto_next_at = 0.0

        self.setWindowTitle(f"{APP_TITLE}　·　{cfg_module.APP_NAME}")
        self.setMinimumSize(1260, 820)
        self.resize(1340, 940)

        sfx.player().preload()

        cfg = cfg_module.load()
        saved_lang = cfg.get("language")
        if saved_lang:
            i18n.set_language(str(saved_lang))
        elif i18n.current() == i18n.DEFAULT_LANGUAGE:
            # 首次启动：跟着系统语言走，认不出来就是中文
            i18n.set_language(detect_system_language())

        self._build_ui()
        i18n.translate_tree(self)
        self._wire_signals()
        self._refresh_audio_devices()
        self._apply_config(cfg)
        self._scan_devices(keep_selection=True)

        self.engine.start()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _retranslate(self) -> None:
        """语言变化后，把界面标题等非控件文案也一起刷新。"""
        self.setWindowTitle(f"{tr(APP_TITLE)}　·　{cfg_module.APP_NAME}")

    # ============================================================ 界面搭建

    def _build_ui(self) -> None:
        # 滑杆标题列宽跟语言走：中文三个字，俄语可能十二个字母
        widgets.DEFAULT_TITLE_WIDTH = widgets.measure_title_width(
            self.font(), [tr(t) for t in SLIDER_TITLES]
        )

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)
        outer.addWidget(self._build_header())

        self.beam_panel = BeamPanel()
        outer.addWidget(self.beam_panel)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_left_column(), 0)
        body.addWidget(self._build_right_column(), 1)
        outer.addLayout(body, 1)

    # ------------------------------------------------------------ 顶部栏

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        row = QHBoxLayout(header)
        row.setContentsMargins(16, 11, 14, 11)
        row.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel(APP_TITLE)
        title.setObjectName("AppTitle")
        subtitle = QLabel(APP_SUBTITLE)
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        row.addLayout(title_box)
        row.addStretch(1)

        caption = QLabel("目标设备")
        caption.setObjectName("StatusText")
        row.addWidget(caption)

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        row.addWidget(self.device_combo)

        self.rescan_btn = PillButton("重新扫描")
        row.addWidget(self.rescan_btn)

        self.test_btn = PillButton("测试震动")
        self.test_btn.setToolTip("让手柄震 0.4 秒，用来确认链路通了")
        row.addWidget(self.test_btn)

        self.dot = StatusDot(11)
        row.addWidget(self.dot)

        self.status_label = QLabel("正在检测…")
        self.status_label.setObjectName("StatusText")
        # 用 Minimum 策略：按内容取宽，不被挤到截断
        self.status_label.setSizePolicy(QSizePolicy.Policy.Minimum,
                                        QSizePolicy.Policy.Fixed)
        row.addWidget(self.status_label)

        self.help_btn = PillButton("帮助")
        self.help_btn.set_sound("click")
        row.addWidget(self.help_btn)

        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(96)
        for code, name in i18n.available():
            self.lang_combo.addItem(name, code)
        idx = self.lang_combo.findData(i18n.current())
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        row.addWidget(self.lang_combo)

        return header

    # ------------------------------------------------------------ 左栏

    def _build_left_column(self) -> QWidget:
        column = QWidget()
        column.setFixedWidth(376)
        v = QVBoxLayout(column)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 2, 0)
        iv.setSpacing(9)

        # --- 运行控制 ---
        run_card = Card("运行控制")
        self.start_btn = QPushButton("开 始 震 动")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.setProperty("running", "false")
        self.start_btn.setMinimumHeight(58)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        run_card.add(self.start_btn)

        self.readout = QLabel("待机")
        self.readout.setObjectName("Readout")
        self.readout.setWordWrap(True)
        run_card.add(self.readout)
        iv.addWidget(run_card)

        # --- 强度调节 ---
        strength = Card("强度调节")
        self.s_master = LabeledSlider("总强度", 0.0, 1.0, 0.80,
                                      formatter=lambda x: f"{x * 100:.0f}%",
                                      tooltip="全局缩放系数，乘在左右马达之上")
        self.s_left = LabeledSlider("左马达", 0.0, 1.0, 1.00,
                                    formatter=lambda x: f"{x * 100:.0f}%",
                                    tooltip="左侧大马达：低频重震")
        self.s_right = LabeledSlider("右马达", 0.0, 1.0, 1.00,
                                     formatter=lambda x: f"{x * 100:.0f}%",
                                     tooltip="右侧小马达：高频细震")
        for w in (self.s_master, self.s_left, self.s_right):
            strength.add(w)
        iv.addWidget(strength)

        # --- 随机搭配 ---
        rnd_card = Card("随机搭配")
        r1 = QHBoxLayout()
        r1.setSpacing(7)
        self.btn_random = PillButton("随机一个")
        self.btn_random.set_sound("random")
        self.btn_spicy = PillButton("偏刺激")
        _bind_toggle(self.btn_spicy, "偏刺激：开", "偏刺激：关")
        r1.addWidget(self.btn_random)
        r1.addWidget(self.btn_spicy)
        rnd_card.body().addLayout(r1)

        self.btn_auto = PillButton("自动轮换")
        _bind_toggle(self.btn_auto, "自动轮换：开", "自动轮换：关")
        rnd_card.add(self.btn_auto)

        self.s_auto_interval = LabeledSlider(
            "轮换间隔", 3.0, 60.0, 12.0, decimals=0, suffix="s",
            tooltip="每隔多久换一套随机搭配。切换会自动对齐到波形循环的接缝处",
        )
        rnd_card.add(self.s_auto_interval)
        iv.addWidget(rnd_card)

        warn = QLabel(
            "⚠ 未做功率限制。长时间全功率震动可能让马达过热、缩短寿命、掉电飞快，"
            "建议一轮 15~20 分钟。"
        )
        warn.setObjectName("Warn")
        warn.setWordWrap(True)
        iv.addWidget(warn)

        # --- 配置 ---
        row1 = QHBoxLayout()
        row1.setSpacing(7)
        self.save_btn = PillButton("保存配置")
        self.load_btn = PillButton("载入配置")
        self.reset_btn = PillButton("恢复默认")
        for btn in (self.save_btn, self.load_btn, self.reset_btn):
            row1.addWidget(btn)
        iv.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(7)
        self.export_btn = PillButton("导出预设…")
        self.import_btn = PillButton("导入预设…")
        self.sfx_btn = PillButton("音效：开")
        _bind_toggle(self.sfx_btn, "音效：开", "音效：关")
        self.sfx_btn.setChecked(True)
        for btn in (self.export_btn, self.import_btn, self.sfx_btn):
            row2.addWidget(btn)
        iv.addLayout(row2)

        hint = QLabel("快捷键：空格 开始/停止　·　Esc 立即停止　·　R 随机搭配")
        hint.setObjectName("Hint")
        iv.addWidget(hint)
        iv.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        v.addWidget(scroll)
        return column

    # ------------------------------------------------------------ 波形参数页

    def _build_wave_params_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(14)

        info = QLabel(
            "这里调波形的形状、节奏与手感。所有改动即时生效。"
        )
        info.setObjectName("Hint")
        info.setWordWrap(True)
        v.addWidget(info)

        mix_card = Card("双波形混合")
        row_b = QHBoxLayout()
        row_b.setSpacing(8)
        row_b.addWidget(QLabel("混合波形"))
        self.combo_wave_b = QComboBox()
        self.combo_wave_b.setMinimumWidth(110)
        self.combo_wave_b.addItem(NO_MIX, "")
        for wf in sorted(WAVEFORMS.values(), key=lambda w: (w.category, w.name)):
            self.combo_wave_b.addItem(f"{tr(wf.category)} · {tr(wf.name)}", wf.key)
        row_b.addWidget(self.combo_wave_b, 1)
        mix_card.body().addLayout(row_b)

        self.s_mix = LabeledSlider("混合比", 0.0, 1.0, 0.0,
                                   formatter=lambda x: f"{x * 100:.0f}%",
                                   tooltip="0% = 只用主波形，100% = 只用混合波形。"
                                           "中间值会混出原库里没有的新节奏")
        mix_card.add(self.s_mix)
        v.addWidget(mix_card)

        feel_card = Card("节奏与手感")
        self.s_speed = LabeledSlider("速度", 0.1, 3.0, 1.0, decimals=2, suffix="x",
                                     tooltip="波形循环快慢。1.00x 为原始节奏")
        self.s_floor = LabeledSlider("强度下限", 0.0, 1.0, 0.0,
                                     formatter=lambda x: f"{x * 100:.0f}%",
                                     tooltip="常驻底噪：让马达一直在震，波形叠加在其之上")
        self.s_smooth = LabeledSlider("平滑", 0.0, 1.0, 0.15,
                                      formatter=lambda x: f"{x * 100:.0f}%",
                                      tooltip="输出低通滤波，越大越绵软、启停越柔和")
        self.s_phase = LabeledSlider("相位差", 0.0, 1.0, 0.0,
                                     formatter=lambda x: f"{x * 100:.0f}%",
                                     tooltip="右马达相对左马达的时间偏移，用于左右推移效果")
        for w in (self.s_speed, self.s_floor, self.s_smooth, self.s_phase):
            feel_card.add(w)
        v.addWidget(feel_card)
        v.addStretch(1)
        return page

    # ------------------------------------------------------------ 体感增强页

    def _build_enhance_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(14)

        info = QLabel(
            "四个绕开马达物理短板的手段。默认值已经调好，可以逐项开关对比，"
            "详细说明见「帮助」。"
        )
        info.setObjectName("Hint")
        info.setWordWrap(True)
        v.addWidget(info)

        crisp = Card("起停锐化")
        self.s_sharpen = LabeledSlider(
            "锐化强度", 0.0, 1.0, 0.50,
            formatter=lambda x: f"{x * 100:.0f}%",
            tooltip="让短脉冲变脆。对敲击、拍打、连击、电脉冲最明显。",
        )
        crisp.add(self.s_sharpen)
        v.addWidget(crisp)

        adapt = Card("反适应漂移")
        self.s_anti = LabeledSlider(
            "漂移量", 0.0, 1.0, 0.20,
            formatter=lambda x: f"{x * 100:.0f}%",
            tooltip="防止长时间震动后「震麻了」。挂机时开着。",
        )
        adapt.add(self.s_anti)
        v.addWidget(adapt)

        sr = Card("随机共振底噪")
        self.s_noise = LabeledSlider(
            "底噪强度", 0.0, 1.0, 0.0,
            formatter=lambda x: f"{x * 100:.0f}%",
            tooltip="加一层听不见的微震，让上面的信号更清楚。开一点点就够。",
        )
        sr.add(self.s_noise)
        v.addWidget(sr)

        duty = Card("占空比")
        self.s_duty = LabeledSlider(
            "占空比", 0.12, 1.0, 1.0,
            formatter=lambda x: f"{x * 100:.0f}%",
            tooltip="压缩脉冲宽度。调小会把持续推压变成密集点刺。",
        )
        duty.add(self.s_duty)
        v.addWidget(duty)
        v.addStretch(1)
        return page

    # ------------------------------------------------------------ 波束页

    def _build_beam_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(14)

        info = QLabel(
            "两个马达做不到在内部真正聚焦振动，这里做的是三件真实成立的事："
            "振幅声像（真实）、拍频干涉（真实物理）、同相聚合与反相分离（体感错觉）。"
            "详细说明见「帮助」。"
        )
        info.setObjectName("Hint")
        info.setWordWrap(True)
        v.addWidget(info)

        switch_card = Card("开关")
        self.btn_beam = PillButton("波束")
        _bind_toggle(self.btn_beam, "波束：开", "波束：关")
        switch_card.add(self.btn_beam)
        self.btn_sweep = PillButton("自动扫掠")
        _bind_toggle(self.btn_sweep, "自动扫掠：开", "自动扫掠：关")
        switch_card.add(self.btn_sweep)
        hint2 = QLabel("可以直接在顶部「聆听波束」面板的图上点击或拖动来设定位置。")
        hint2.setObjectName("Hint")
        hint2.setWordWrap(True)
        switch_card.add(hint2)
        v.addWidget(switch_card)

        pos_card = Card("位置与聚焦")
        self.s_beam_pos = LabeledSlider(
            "位置", -1.0, 1.0, 0.0,
            formatter=lambda x: ("居中" if abs(x) < 0.05
                                 else (f"左 {abs(x) * 100:.0f}%" if x < 0
                                       else f"右 {x * 100:.0f}%")),
            tooltip="-100% 全在左握把，0 中央聚合，+100% 全在右握把",
        )
        self.s_beam_width = LabeledSlider(
            "聚焦度", 0.0, 1.0, 0.45,
            formatter=lambda x: f"{100 - x * 100:.0f}%",
            tooltip="数值越大波束越窄、定位越锐利；越小越弥散",
        )
        pos_card.add(self.s_beam_pos)
        pos_card.add(self.s_beam_width)

        b2 = QHBoxLayout()
        b2.setSpacing(8)
        b2.addWidget(QLabel("极性"))
        self.combo_polarity = QComboBox()
        self.combo_polarity.setMinimumWidth(100)
        self.combo_polarity.addItem("同相 · 中央聚合", "in")
        self.combo_polarity.addItem("反相 · 两边轮流", "out")
        b2.addWidget(self.combo_polarity, 1)
        pos_card.body().addLayout(b2)
        v.addWidget(pos_card)

        motion_card = Card("运动与干涉")
        self.s_beat_hz = LabeledSlider(
            "拍频", 0.0, 12.0, 0.0, decimals=1, suffix="Hz",
            tooltip="真实物理干涉：1~6Hz 体感最明显，会感受到一阵阵的涌动",
        )
        self.s_sweep_rate = LabeledSlider(
            "扫掠速度", 0.05, 2.0, 0.5, decimals=2, suffix="Hz",
            tooltip="波束左右来回扫掠的速度",
        )
        motion_card.add(self.s_beat_hz)
        motion_card.add(self.s_sweep_rate)
        v.addWidget(motion_card)
        v.addStretch(1)
        return page

    # ------------------------------------------------------------ 音频页

    def _build_audio_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(14)

        info = QLabel(
            "抓系统全局回放，任何软件在放声音都能跟随。"
            "低频驱动左马达，中高频驱动右马达 —— 按两个马达的物理特性分配。"
        )
        info.setObjectName("Hint")
        info.setWordWrap(True)
        v.addWidget(info)

        src_card = Card("采集")
        self.btn_audio = PillButton("音频跟随")
        _bind_toggle(self.btn_audio, "音频跟随：开", "音频跟随：关")
        src_card.add(self.btn_audio)

        a1 = QHBoxLayout()
        a1.setSpacing(8)
        a1.addWidget(QLabel("模式"))
        self.combo_source = QComboBox()
        self.combo_source.setMinimumWidth(110)
        for name, key in SOURCE_CHOICES:
            self.combo_source.addItem(name, key)
        a1.addWidget(self.combo_source, 1)
        src_card.body().addLayout(a1)

        a2 = QHBoxLayout()
        a2.setSpacing(8)
        a2.addWidget(QLabel("采集源"))
        self.combo_audio_dev = QComboBox()
        self.combo_audio_dev.setMinimumWidth(110)
        self.combo_audio_dev.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo_audio_dev.setMinimumContentsLength(8)
        a2.addWidget(self.combo_audio_dev, 1)
        self.btn_audio_rescan = PillButton("刷新")
        self.btn_audio_rescan.setToolTip("重新枚举 WASAPI Loopback 设备")
        a2.addWidget(self.btn_audio_rescan)
        src_card.body().addLayout(a2)
        v.addWidget(src_card)

        map_card = Card("分频映射")
        self.s_audio_l = LabeledSlider("低频→左", 0.0, 3.0, 1.0, decimals=2, suffix="x",
                                       tooltip="20~120Hz 低频能量驱动左马达的增益")
        self.s_audio_r = LabeledSlider("中高→右", 0.0, 3.0, 1.0, decimals=2, suffix="x",
                                       tooltip="120~4000Hz 中高频能量驱动右马达的增益")
        self.s_audio_sens = LabeledSlider("采集灵敏度", 0.5, 8.0, 2.2, decimals=1, suffix="x",
                                          tooltip="对采集到的音频能量整体放大的倍数")
        self.s_audio_th = LabeledSlider("触发阈值", 0.0, 0.8, 0.04, decimals=2,
                                        tooltip="低于该能量的声音不驱动震动，用来滤掉底噪")
        for w in (self.s_audio_l, self.s_audio_r, self.s_audio_sens, self.s_audio_th):
            map_card.add(w)

        self.audio_meter = QLabel("采集未开启")
        self.audio_meter.setObjectName("Readout")
        self.audio_meter.setWordWrap(True)
        map_card.add(self.audio_meter)
        v.addWidget(map_card)

        tip = QLabel(
            "「波形 × 音频」模式下，波形会先被音频能量调制 —— 相当于用音乐给按摩节奏打拍子。"
        )
        tip.setObjectName("Hint")
        tip.setWordWrap(True)
        v.addWidget(tip)
        v.addStretch(1)
        return page

    # ------------------------------------------------------------ 右栏

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        v = QVBoxLayout(column)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        self.view = WaveformView()
        self.view.set_source(self.engine.preview_history)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.view.setMinimumHeight(168)
        v.addWidget(self.view)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_wave_library(), "波形库")
        self.tabs.addTab(_wrap_scroll(self._build_wave_params_tab()), "波形参数")
        self.tabs.addTab(_wrap_scroll(self._build_enhance_tab()), "体感增强")
        self.tabs.addTab(_wrap_scroll(self._build_beam_tab()), "虚拟波束")
        self.tabs.addTab(self._build_curve_tab(), "自定义曲线")
        self.tabs.addTab(_wrap_scroll(self._build_audio_tab()), "音频跟随")
        self._curve_tab_index = 4
        v.addWidget(self.tabs, 1)

        return column

    def _build_wave_library(self) -> QWidget:
        container = QWidget()
        container.setObjectName("WaveLibrary")
        v = QVBoxLayout(container)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(11)

        for category, items in waveforms_by_category():
            title = QLabel(tr(category))
            title.setObjectName("CategoryTitle")
            v.addWidget(title)

            grid = QGridLayout()
            grid.setSpacing(7)
            for i, wf in enumerate(items):
                btn = WaveButton(
                    wf.key, tr(wf.name),
                    f"{tr(wf.desc)}\n"
                    f"{tr('循环 {p:g}s　·　强度 {i}', p=wf.period, i=tr(wf.intensity))}",
                )
                btn.clicked.connect(lambda _c=False, k=wf.key: self._select_waveform(k))
                self._wave_buttons[wf.key] = btn
                grid.addWidget(btn, i // 5, i % 5)
            v.addLayout(grid)

        title = QLabel("自定义")
        title.setObjectName("CategoryTitle")
        v.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(7)
        custom_btn = WaveButton("custom", tr("手绘曲线"), tr("使用「自定义曲线」标签页里手绘的波形"))
        custom_btn.clicked.connect(lambda _c=False: self._select_waveform("custom"))
        self._wave_buttons["custom"] = custom_btn
        grid.addWidget(custom_btn, 0, 0)
        v.addLayout(grid)

        v.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        return scroll

    def _build_curve_tab(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        info = QLabel(
            "左键空白处加点并拖动　·　右键或双击删除控制点　·　滚轮在点上微调高度。"
            "曲线首尾自动闭合，无限循环。"
        )
        info.setObjectName("Hint")
        info.setWordWrap(True)
        v.addWidget(info)

        self.curve_editor = CurveEditor()
        v.addWidget(self.curve_editor, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("循环时长"))
        self.curve_duration = QDoubleSpinBox()
        self.curve_duration.setRange(0.5, 30.0)
        self.curve_duration.setSingleStep(0.5)
        self.curve_duration.setDecimals(1)
        self.curve_duration.setSuffix(" 秒")
        self.curve_duration.setValue(4.0)
        row.addWidget(self.curve_duration)

        self.curve_flat_btn = PillButton("重置为直线")
        self.curve_clear_btn = PillButton("清空")
        row.addWidget(self.curve_flat_btn)
        row.addWidget(self.curve_clear_btn)
        row.addStretch(1)

        self.curve_use_btn = PillButton("使用这条曲线")
        self.curve_use_btn.setObjectName("Primary")
        row.addWidget(self.curve_use_btn)
        v.addLayout(row)
        return page

    # ============================================================ 信号连接

    def _wire_signals(self) -> None:
        self.start_btn.clicked.connect(self._toggle_running)
        self.rescan_btn.clicked.connect(lambda: self._scan_devices(keep_selection=True))
        self.test_btn.clicked.connect(self._test_pulse)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        for widget in (self.s_master, self.s_left, self.s_right, self.s_speed,
                       self.s_floor, self.s_smooth, self.s_phase, self.s_mix):
            widget.valueChanged.connect(self._on_slider_changed)

        # 体感增强
        for widget in (self.s_sharpen, self.s_noise, self.s_anti, self.s_duty):
            widget.valueChanged.connect(self._on_slider_changed)

        # 波束
        for widget in (self.s_beam_pos, self.s_beam_width, self.s_beat_hz, self.s_sweep_rate):
            widget.valueChanged.connect(self._on_slider_changed)
        self.btn_beam.toggled.connect(self._on_slider_changed)
        self.btn_sweep.toggled.connect(self._on_slider_changed)
        self.combo_polarity.currentIndexChanged.connect(self._on_slider_changed)
        self.beam_panel.scope.positionDragged.connect(self._on_beam_dragged)
        self.beam_panel.listenToggled.connect(self._on_listen_toggled)
        self.beam_panel.volumeChanged.connect(self._on_volume_changed)
        self.beam_panel.timbreChanged.connect(self._on_timbre_changed)

        # 音频
        self.btn_audio.toggled.connect(self._on_audio_toggled)
        self.combo_source.currentIndexChanged.connect(self._on_source_changed)
        self.btn_audio_rescan.clicked.connect(self._refresh_audio_devices)
        self.combo_audio_dev.currentIndexChanged.connect(self._on_audio_device_changed)
        for widget in (self.s_audio_l, self.s_audio_r, self.s_audio_sens, self.s_audio_th):
            widget.valueChanged.connect(self._on_slider_changed)

        # 随机
        self.btn_random.clicked.connect(lambda: self._randomize(announce=True))
        self.combo_wave_b.currentIndexChanged.connect(self._on_wave_b_changed)

        # 配置
        self.save_btn.clicked.connect(lambda: self._save_config(notify=True))
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.reset_btn.clicked.connect(self._reset_defaults)
        self.export_btn.clicked.connect(self._export_preset)
        self.import_btn.clicked.connect(self._import_preset)
        self.sfx_btn.toggled.connect(lambda checked: setattr(sfx.player(), "enabled", checked))

        # 曲线
        self.curve_editor.pointsChanged.connect(self._on_curve_changed)
        self.curve_duration.valueChanged.connect(self._on_curve_duration)
        self.curve_flat_btn.clicked.connect(lambda: self.curve_editor.reset_flat(0.6))
        self.curve_clear_btn.clicked.connect(self.curve_editor.clear_all)
        self.curve_use_btn.clicked.connect(lambda: self._select_waveform("custom"))

        self.help_btn.clicked.connect(self._show_manual)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)

        QShortcut(QKeySequence("Space"), self, activated=self._toggle_running)
        QShortcut(QKeySequence("Esc"), self, activated=self._stop_now)
        QShortcut(QKeySequence("R"), self, activated=lambda: self._randomize(announce=True))
        QShortcut(QKeySequence("F1"), self, activated=self._show_manual)

    # ============================================================ 语言

    def _show_manual(self) -> None:
        ManualDialog(self).exec()

    def _on_language_changed(self, _index: int) -> None:
        code = self.lang_combo.currentData()
        if not code or code == i18n.current():
            return
        cfg = self._collect_config()
        cfg["language"] = code
        i18n.set_language(code)
        self._rebuild_ui(cfg)

    def _rebuild_ui(self, cfg: dict) -> None:
        """换语言时整棵界面重建 —— 比逐个记录原文再还原稳得多。"""
        self._timer.stop()
        for shortcut in self.findChildren(QShortcut):
            shortcut.setParent(None)
            shortcut.deleteLater()

        self._wave_buttons.clear()
        self._last_phase = 0.0
        self._tick_count = 0

        self.setCentralWidget(QWidget())          # 释放旧界面
        self._build_ui()
        i18n.translate_tree(self)
        self._retranslate()
        self._wire_signals()
        self._refresh_audio_devices()
        self._apply_config(cfg)
        self._scan_devices(keep_selection=True)
        self._timer.start()

    # ============================================================ 基础槽

    def _on_slider_changed(self, *_args) -> None:
        self._push_params()

    def _push_params(self) -> None:
        self.engine.update_params(
            master=self.s_master.value(),
            left_gain=self.s_left.value(),
            right_gain=self.s_right.value(),
            speed=self.s_speed.value(),
            floor=self.s_floor.value(),
            smoothing=self.s_smooth.value(),
            phase_shift=self.s_phase.value(),
            mix=self.s_mix.value(),
            beam_enabled=self.btn_beam.isChecked(),
            beam_position=self.s_beam_pos.value(),
            beam_width=self.s_beam_width.value(),
            beam_sweep=self.btn_sweep.isChecked(),
            beam_sweep_rate=self.s_sweep_rate.value(),
            beam_beat_hz=self.s_beat_hz.value(),
            beam_polarity=self.combo_polarity.currentData() or "in",
            audio_gain_l=self.s_audio_l.value(),
            audio_gain_r=self.s_audio_r.value(),
            audio_threshold=self.s_audio_th.value(),
            sharpen=self.s_sharpen.value(),
            noise_floor=self.s_noise.value(),
            anti_adapt=self.s_anti.value(),
            duty=self.s_duty.value(),
        )
        self.capture.sensitivity = self.s_audio_sens.value()
        timbre = self.beam_panel.timbre_combo.currentData()
        if timbre:
            self.player.set_timbre(timbre)

    def _toggle_running(self) -> None:
        if self.engine.is_running():
            self._stop_now()
        else:
            self.engine.set_running(True)
            self.engine.reset_phase()
            self.start_btn.setText(tr("停 止 震 动"))
            self.start_btn.setProperty("running", "true")
            refresh_style(self.start_btn)
            self._auto_next_at = time.perf_counter() + self.s_auto_interval.value()
            if not self.engine.connected:
                self.readout.setText(
                    f"<b style='color:{theme.WARN}'>已待命</b> —— {DISCONNECT_HINT}"
                )

    def _stop_now(self) -> None:
        self.engine.set_running(False)
        self.start_btn.setText(tr("开 始 震 动"))
        self.start_btn.setProperty("running", "false")
        refresh_style(self.start_btn)

    def _test_pulse(self) -> None:
        if self.engine.is_running():
            self.readout.setText(tr("正在运行中，测试震动已跳过（先停止再测试）"))
            return
        if not self.engine.connected:
            self.readout.setText(f"<b style='color:{theme.WARN}'>未连接</b> —— {DISCONNECT_HINT}")
            return
        self.engine.pulse_once(1.0, 1.0, 0.4)

    # ============================================================ 波形选择

    def _select_waveform(self, key: str) -> None:
        if key not in self._wave_buttons:
            return
        for k, btn in self._wave_buttons.items():
            btn.setChecked(k == key)
        self._current_wave = key
        self.engine.update_params(waveform=key)
        if key == "custom":
            self.tabs.setCurrentIndex(self._curve_tab_index)
            self._on_curve_changed()

    def _on_curve_changed(self) -> None:
        self.engine.update_params(curve_points=tuple(self.curve_editor.points()))
        self.curve_use_btn.setText(tr("正在使用 ✓") if self._current_wave == "custom"
                                   else tr("使用这条曲线"))

    def _on_curve_duration(self, value: float) -> None:
        self.engine.update_params(curve_duration=value)

    def _on_wave_b_changed(self, _index: int) -> None:
        self.engine.update_params(waveform_b=self.combo_wave_b.currentData() or "")

    # ============================================================ 波束

    def _on_beam_dragged(self, position: float) -> None:
        self.s_beam_pos.set_value(position, emit=False)
        if not self.btn_beam.isChecked():
            self.btn_beam.setChecked(True)
        self._push_params()

    def _on_listen_toggled(self, checked: bool) -> None:
        if checked:
            if not self.player.start():
                self.beam_panel.set_status(tr("开启失败") + f"：{self.player.error}", warn=True)
                self.beam_panel.set_listening(False)
                return
            self.beam_panel.set_status(tr("正在播放波束立体声"))
        else:
            self.player.stop()
            self.beam_panel.set_status(tr("未开启"))
        self._update_feedback_guard()

    def _on_volume_changed(self, value: float) -> None:
        self.player.volume = value

    def _on_timbre_changed(self, key: str) -> None:
        if key:
            self.player.set_timbre(key)
            self._update_feedback_guard()

    def _update_feedback_guard(self) -> None:
        """聆听波束 + 音频跟随同时开启会自激回授，这里挖掉载波频段并给出提示。"""
        listening = self.player.running
        following = (self.btn_audio.isChecked()
                     and self.combo_source.currentData() in (SOURCE_AUDIO, SOURCE_MIX))

        if listening and following:
            name, freq, kind = audio_mod.TIMBRES.get(
                self.player.timbre, ("", 0.0, "sine")
            )
            ranges: list[tuple[float, float]] = []
            if kind != "noise" and freq > 0:
                for harmonic in (1, 2, 3):
                    f = freq * harmonic
                    ranges.append((f * 0.86, f * 1.16))
            self.capture.exclude_ranges = ranges
            self.beam_panel.set_status(tr("⚠ 聆听 + 音频跟随同时开启，已挖掉载波频段防回授"), warn=True)
        else:
            self.capture.exclude_ranges = []
            if listening:
                self.beam_panel.set_status(tr("正在播放波束立体声"))
            elif self.engine.is_running():
                self.beam_panel.set_status(tr("手柄震动中（未聆听）"))
            else:
                self.beam_panel.set_status(tr("未开启"))

    # ============================================================ 音频

    def _refresh_audio_devices(self) -> None:
        self._loopback_devices = self.hub.list_loopback_devices()
        self.combo_audio_dev.blockSignals(True)
        self.combo_audio_dev.clear()
        if not self._loopback_devices:
            reason = self.hub.error or "未找到 WASAPI Loopback 设备"
            self.combo_audio_dev.addItem(f"（{reason}）", None)
            self.combo_audio_dev.setEnabled(False)
            self.btn_audio.setEnabled(False)
            self.audio_meter.setText(tr("音频不可用") + f"：{reason}")
        else:
            for dev in self._loopback_devices:
                self.combo_audio_dev.addItem(dev.label, dev.index)
            self.combo_audio_dev.setEnabled(True)
            self.btn_audio.setEnabled(True)
        self.combo_audio_dev.blockSignals(False)

    def _on_audio_device_changed(self, _index: int) -> None:
        idx = self.combo_audio_dev.currentData()
        if idx is None:
            return
        self.capture.device_index = int(idx)
        if self.capture.running:
            self.capture.stop()
            self.capture.start(int(idx))

    def _on_audio_toggled(self, checked: bool) -> None:
        if checked:
            idx = self.combo_audio_dev.currentData()
            if not self.capture.start(int(idx) if idx is not None else None):
                self.audio_meter.setText(tr("开启失败") + f"：{self.capture.state.error}")
                self.btn_audio.setChecked(False)
                return
            # 打开采集却还停在「只放波形」会让人困惑，顺手切到跟随模式
            if (self.combo_source.currentData() or SOURCE_WAVEFORM) == SOURCE_WAVEFORM:
                sidx = self.combo_source.findData(SOURCE_AUDIO)
                if sidx >= 0:
                    self.combo_source.blockSignals(True)
                    self.combo_source.setCurrentIndex(sidx)
                    self.combo_source.blockSignals(False)
                    self.engine.update_params(source=SOURCE_AUDIO)
        else:
            self.capture.stop()
        self._update_feedback_guard()

    def _on_source_changed(self, _index: int) -> None:
        source = self.combo_source.currentData() or SOURCE_WAVEFORM
        self.engine.update_params(source=source)
        if source != SOURCE_WAVEFORM and not self.capture.running:
            self.btn_audio.setChecked(True)
        self._update_feedback_guard()

    # ============================================================ 随机搭配

    def _randomize(self, *, announce: bool = False) -> None:
        preset = random_preset(spicy=self.btn_spicy.isChecked())
        self._apply_random_preset(preset)

        if announce:
            main = WAVEFORMS.get(preset.waveform)
            name = tr(main.name) if main else preset.waveform
            extra = ""
            if preset.waveform_b:
                other = WAVEFORMS.get(preset.waveform_b)
                extra += f" + {tr(other.name) if other else preset.waveform_b}（{tr('混合比')} {preset.mix * 100:.0f}%）"
            if preset.beam_enabled:
                extra += "　·　波束"
                if preset.beam_sweep:
                    extra += "扫掠"
                if preset.beam_beat_hz > 0:
                    extra += f"拍频 {preset.beam_beat_hz:g}Hz"
            self.readout.setText(f"随机搭配：<b>{name}</b>{extra}")
        else:
            self._auto_next_at = time.perf_counter() + self.s_auto_interval.value()

    def _apply_random_preset(self, p) -> None:
        self.s_mix.set_value(p.mix, emit=False)
        idx = self.combo_wave_b.findData(p.waveform_b or "")
        self.combo_wave_b.blockSignals(True)
        self.combo_wave_b.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_wave_b.blockSignals(False)

        self.s_speed.set_value(p.speed, emit=False)
        self.s_floor.set_value(p.floor, emit=False)
        self.s_smooth.set_value(p.smoothing, emit=False)
        self.s_phase.set_value(p.phase_shift, emit=False)
        self.s_sharpen.set_value(p.sharpen, emit=False)
        self.s_noise.set_value(p.noise_floor, emit=False)
        self.s_anti.set_value(p.anti_adapt, emit=False)
        self.s_duty.set_value(p.duty, emit=False)

        self.btn_beam.setChecked(p.beam_enabled)
        self.s_beam_pos.set_value(p.beam_position, emit=False)
        self.s_beam_width.set_value(p.beam_width, emit=False)
        self.btn_sweep.setChecked(p.beam_sweep)
        self.s_sweep_rate.set_value(p.beam_sweep_rate, emit=False)
        self.s_beat_hz.set_value(p.beam_beat_hz, emit=False)
        pidx = self.combo_polarity.findData(p.beam_polarity)
        self.combo_polarity.blockSignals(True)
        self.combo_polarity.setCurrentIndex(pidx if pidx >= 0 else 0)
        self.combo_polarity.blockSignals(False)

        self._select_waveform(p.waveform)
        self._push_params()
        self.engine.update_params(waveform_b=p.waveform_b or "", mix=p.mix)

    # ============================================================ 设备

    def _on_device_changed(self, _index: int) -> None:
        data = self.device_combo.currentData()
        if data is None:
            return
        self._selected_device = int(data)
        self.engine.set_device(self._selected_device)

    def _scan_devices(self, *, keep_selection: bool = True) -> None:
        if not self.backend.available:
            self.device_combo.clear()
            self.device_combo.addItem(tr("缺少 XInput 运行库"), -1)
            self.device_combo.setEnabled(False)
            self.rescan_btn.setEnabled(False)
            self.test_btn.setEnabled(False)
            self._set_status(theme.OFF, tr("缺少 XInput 运行库"))
            self.readout.setText(tr("无法加载 XInput 运行库") + f"：{self.backend.load_error}")
            return

        infos = self.backend.enumerate()
        target = self._selected_device if keep_selection else 0

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for info in infos:
            if info.connected:
                key = ("槽位 {i}　Xbox 兼容手柄　[无线]" if info.wireless
                       else "槽位 {i}　Xbox 兼容手柄　[有线]")
                label = tr(key, i=info.index)
                if not info.supports_ffb:
                    label += tr("（无震动支持）")
            else:
                label = tr("槽位 {i}　——　未连接", i=info.index)
            self.device_combo.addItem(label, info.index)
        idx = self.device_combo.findData(target)
        self.device_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.device_combo.blockSignals(False)

        self._selected_device = target
        self.engine.set_device(target)
        self._refresh_status()

    def _refresh_status(self) -> None:
        connected = self.engine.connected
        running = self.engine.is_running()
        if not connected:
            self._set_status(theme.OFF, tr("未连接"))
        elif running:
            self._set_status(theme.OK, tr("已连接 · 震动中"))
        else:
            self._set_status(theme.WARN, tr("已连接 · 待机"))

    def _set_status(self, color: str, text: str) -> None:
        self.dot.set_color(color)
        self.status_label.setText(text)

    # ============================================================ 定时刷新

    def _on_tick(self) -> None:
        self._tick_count += 1
        running = self.engine.is_running()
        params = self.engine.params()

        self.view.set_state(running, self.engine.left_raw, self.engine.right_raw)
        self.view.update()

        self.beam_panel.scope.set_state(
            position=self.engine.beam_position if params.beam_enabled else 0.0,
            width_ratio=params.beam_width,
            level_l=self.engine.env_l,
            level_r=self.engine.env_r,
            active=params.beam_enabled and running,
            listening=self.player.running,
            audio_l=self.engine.audio_bass,
            audio_r=self.engine.audio_mid,
        )
        self.beam_panel.scope.update()

        if self._current_wave == "custom":
            self.curve_editor.set_phase(self.engine.phase_value)

        # 自动轮换：优先在波形循环的接缝处切换，避免切一半
        if self.btn_auto.isChecked() and running:
            phase = self.engine.phase_value
            if self._last_phase > 0.8 and phase < 0.2 and time.perf_counter() >= self._auto_next_at:
                self._randomize(announce=False)
            self._last_phase = phase

        if self._tick_count % 6:
            return

        self._refresh_status()
        self.test_btn.setEnabled(not running and self.backend.available)

        if not self.backend.available:
            self._update_audio_meter()
            return
        if not self.engine.connected:
            if running:
                self.readout.setText(
                    f"<b style='color:{theme.WARN}'>{tr('等待手柄接入…')}</b><br>"
                    f"{tr(DISCONNECT_HINT)}"
                )
            else:
                self.readout.setText(tr(DISCONNECT_HINT))
            self._update_audio_meter()
            return

        left_pct = self.engine.left_raw / 65535.0 * 100.0
        right_pct = self.engine.right_raw / 65535.0 * 100.0
        hz = f"{self.engine.measured_hz:.0f}Hz" if self.engine.measured_hz else "—"
        state = tr("震动中") if running else tr("待机")

        beam_txt = ""
        if params.beam_enabled and running:
            pos = self.engine.beam_position
            if abs(pos) < 0.06:
                where = tr("居中")
            elif pos < 0:
                where = f"{tr('偏左')} {abs(pos) * 100:.0f}%"
            else:
                where = f"{tr('偏右')} {pos * 100:.0f}%"
            beam_txt = f"　{tr('波束')} <b>{where}</b>"

        self.readout.setText(
            f"<b>{state}</b>　{tr('波形')} <b>{self._wave_name()}</b>　"
            f"{tr('节拍')} {hz}{beam_txt}<br>"
            f"{tr('左马达')} <b>{self.engine.left_raw:>5d}</b> ({left_pct:.0f}%)　"
            f"{tr('右马达')} <b>{self.engine.right_raw:>5d}</b> ({right_pct:.0f}%)"
        )
        self._update_audio_meter()

    def _wave_name(self) -> str:
        if self._current_wave == "custom":
            return tr("手绘曲线")
        wf = WAVEFORMS.get(self._current_wave)
        base = tr(wf.name) if wf else "—"
        other_key = self.combo_wave_b.currentData()
        if other_key:
            other = WAVEFORMS.get(other_key)
            if other:
                return f"{base}+{tr(other.name)}"
        return base

    def _update_audio_meter(self) -> None:
        st = self.capture.state
        if not self.capture.running:
            self.audio_meter.setText(tr("采集未开启"))
            return
        if st.error:
            self.audio_meter.setText(tr("采集异常") + f"：{st.error}")
            return
        self.audio_meter.setText(
            f"低频 {st.bass * 100:>3.0f}%　中高 {st.mid * 100:>3.0f}%　高频 {st.high * 100:>3.0f}%"
            f"　（原始 {st.raw_bass:.3f} / {st.raw_mid:.3f}）"
        )

    # ============================================================ 配置

    def _collect_config(self) -> dict[str, Any]:
        return {
            "version": cfg_module.CONFIG_VERSION,
            "last_device_index": self._selected_device,
            "auto_restore": True,
            "params": {
                "master": self.s_master.value(),
                "left_gain": self.s_left.value(),
                "right_gain": self.s_right.value(),
                "speed": self.s_speed.value(),
                "floor": self.s_floor.value(),
                "smoothing": self.s_smooth.value(),
                "phase_shift": self.s_phase.value(),
                "mix": self.s_mix.value(),
                "waveform_b": self.combo_wave_b.currentData() or "",
                "beam_enabled": self.btn_beam.isChecked(),
                "beam_position": self.s_beam_pos.value(),
                "beam_width": self.s_beam_width.value(),
                "beam_sweep": self.btn_sweep.isChecked(),
                "beam_sweep_rate": self.s_sweep_rate.value(),
                "beam_beat_hz": self.s_beat_hz.value(),
                "beam_polarity": self.combo_polarity.currentData() or "in",
                "source": self.combo_source.currentData() or SOURCE_WAVEFORM,
                "audio_gain_l": self.s_audio_l.value(),
                "audio_gain_r": self.s_audio_r.value(),
                "audio_threshold": self.s_audio_th.value(),
                "audio_sensitivity": self.s_audio_sens.value(),
                "sharpen": self.s_sharpen.value(),
                "noise_floor": self.s_noise.value(),
                "anti_adapt": self.s_anti.value(),
                "duty": self.s_duty.value(),
            },
            "waveform": self._current_wave,
            "language": i18n.current(),
            "curve_duration": self.curve_duration.value(),
            "custom_curve": [list(p) for p in self.curve_editor.points()],
            "beam": {
                "volume": self.beam_panel.volume.value(),
                "timbre": self.beam_panel.timbre_combo.currentData() or "rumble",
                "auto_interval": self.s_auto_interval.value(),
                "spicy": self.btn_spicy.isChecked(),
                "sfx": self.sfx_btn.isChecked(),
            },
        }

    def _apply_config(self, data: dict[str, Any]) -> None:
        p = data.get("params") or {}
        self.s_master.set_value(float(p.get("master", 0.80)), emit=False)
        self.s_left.set_value(float(p.get("left_gain", 1.0)), emit=False)
        self.s_right.set_value(float(p.get("right_gain", 1.0)), emit=False)
        self.s_speed.set_value(float(p.get("speed", 1.0)), emit=False)
        self.s_floor.set_value(float(p.get("floor", 0.0)), emit=False)
        self.s_smooth.set_value(float(p.get("smoothing", 0.15)), emit=False)
        self.s_phase.set_value(float(p.get("phase_shift", 0.0)), emit=False)
        self.s_mix.set_value(float(p.get("mix", 0.0)), emit=False)

        idx = self.combo_wave_b.findData(p.get("waveform_b", "") or "")
        self.combo_wave_b.blockSignals(True)
        self.combo_wave_b.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_wave_b.blockSignals(False)

        self.btn_beam.setChecked(bool(p.get("beam_enabled", False)))
        self.s_beam_pos.set_value(float(p.get("beam_position", 0.0)), emit=False)
        self.s_beam_width.set_value(float(p.get("beam_width", 0.45)), emit=False)
        self.btn_sweep.setChecked(bool(p.get("beam_sweep", False)))
        self.s_sweep_rate.set_value(float(p.get("beam_sweep_rate", 0.5)), emit=False)
        self.s_beat_hz.set_value(float(p.get("beam_beat_hz", 0.0)), emit=False)
        pidx = self.combo_polarity.findData(p.get("beam_polarity", "in"))
        self.combo_polarity.blockSignals(True)
        self.combo_polarity.setCurrentIndex(pidx if pidx >= 0 else 0)
        self.combo_polarity.blockSignals(False)

        sidx = self.combo_source.findData(p.get("source", SOURCE_WAVEFORM))
        self.combo_source.blockSignals(True)
        self.combo_source.setCurrentIndex(sidx if sidx >= 0 else 0)
        self.combo_source.blockSignals(False)

        self.s_audio_l.set_value(float(p.get("audio_gain_l", 1.0)), emit=False)
        self.s_audio_r.set_value(float(p.get("audio_gain_r", 1.0)), emit=False)
        self.s_audio_th.set_value(float(p.get("audio_threshold", 0.04)), emit=False)
        self.s_audio_sens.set_value(float(p.get("audio_sensitivity", 2.2)), emit=False)

        self.s_sharpen.set_value(float(p.get("sharpen", 0.50)), emit=False)
        self.s_noise.set_value(float(p.get("noise_floor", 0.0)), emit=False)
        self.s_anti.set_value(float(p.get("anti_adapt", 0.20)), emit=False)
        self.s_duty.set_value(float(p.get("duty", 1.0)), emit=False)

        beam_cfg = data.get("beam") or {}
        volume = float(beam_cfg.get("volume", 0.55))
        self.beam_panel.volume.set_value(volume, emit=False)
        self.player.volume = volume
        timbre = str(beam_cfg.get("timbre", "rumble"))
        self.beam_panel.set_timbre(timbre)
        self.player.set_timbre(timbre)
        self.s_auto_interval.set_value(float(beam_cfg.get("auto_interval", 12.0)), emit=False)
        self.btn_spicy.setChecked(bool(beam_cfg.get("spicy", False)))
        self.sfx_btn.setChecked(bool(beam_cfg.get("sfx", True)))
        sfx.player().enabled = self.sfx_btn.isChecked()

        self.curve_duration.blockSignals(True)
        self.curve_duration.setValue(float(data.get("curve_duration", 4.0)))
        self.curve_duration.blockSignals(False)

        curve = data.get("custom_curve")
        if curve:
            self.curve_editor.set_points(curve)

        self._selected_device = int(data.get("last_device_index", 0))
        self._push_params()
        self.engine.update_params(curve_duration=self.curve_duration.value())
        self._select_waveform(str(data.get("waveform", "breath")))
        self.engine.update_params(waveform_b=self.combo_wave_b.currentData() or "")

    def _save_config(self, *, notify: bool = False) -> bool:
        ok = cfg_module.save(self._collect_config())
        if notify:
            self.readout.setText(
                tr("配置已保存到 ") + str(cfg_module.config_path())
                if ok else tr("配置保存失败")
            )
        return ok

    def _on_load_clicked(self) -> None:
        self._apply_config(cfg_module.load())
        self._scan_devices(keep_selection=True)
        self.readout.setText(tr("已从配置载入") + " " + str(cfg_module.config_path()))

    def _reset_defaults(self) -> None:
        self._apply_config(cfg_module.defaults())
        self.readout.setText(tr("已恢复默认参数"))

    def _export_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("导出预设…"), str(Path.home() / "preset.json"), "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._collect_config(), fh, ensure_ascii=False, indent=2)
            self.readout.setText(tr("已导出") + f" → {path}")
        except Exception as exc:
            QMessageBox.warning(self, tr("导出失败"), str(exc))

    def _import_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("导入预设…"), str(Path.home()), "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError(tr("预设文件格式不正确"))
            self._apply_config(data)
            self._scan_devices(keep_selection=True)
            self.readout.setText(tr("已导入") + f" ← {path}")
        except Exception as exc:
            QMessageBox.warning(self, tr("导入失败"), str(exc))

    # ============================================================ 关闭

    def closeEvent(self, event) -> None:
        try:
            self._timer.stop()
        except Exception:
            pass
        self.engine.set_running(False)
        self._save_config(notify=False)
        self.player.stop()
        self.capture.stop()
        self.engine.shutdown()
        event.accept()
