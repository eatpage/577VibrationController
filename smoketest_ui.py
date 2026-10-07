"""界面冒烟测试：离屏渲染截图，确认布局没塌、没报错。

用法：
    QT_QPA_PLATFORM=offscreen python smoketest_ui.py [输出图片前缀]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.rumble_engine import RumbleEngine  # noqa: E402
from ui import theme  # noqa: E402
from ui.fonts import resolve_family  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ui_preview")
OUT_MAIN = BASE.with_name(BASE.stem + ".png")
OUT_BEAM = BASE.with_name(BASE.stem + "_beam.png")
OUT_CURVE = BASE.with_name(BASE.stem + "_curve.png")
OUT_TAB = BASE.with_name(BASE.stem + "_tab{n}.png")

app = QApplication(sys.argv)
app.setStyle("Fusion")
family = resolve_family() or "Microsoft YaHei UI"
app.setStyleSheet(theme.stylesheet(family))
app.setFont(QFont(family, 9))

engine = RumbleEngine(tick_hz=125)
window = MainWindow(engine)
window.resize(1340, 940)
window.show()

steps: list = []


def step(name, fn):
    steps.append((name, fn))


def run_next():
    if not steps:
        finish()
        return
    name, fn = steps.pop(0)
    try:
        fn()
    except Exception:
        import traceback
        print(f"[step] {name} 失败")
        traceback.print_exc()
    QTimer.singleShot(700, run_next)


def shot_main():
    window.grab().save(str(OUT_MAIN))
    print(f"[ok] 主界面 -> {OUT_MAIN.resolve()}")


def enable_features():
    window.btn_beam.setChecked(True)
    window.btn_sweep.setChecked(True)
    window.s_beat_hz.set_value(3.2)
    window.s_beam_width.set_value(0.3)
    window._randomize(announce=True)
    window.btn_beam.setChecked(True)
    window.s_beam_pos.set_value(-0.35)
    window._push_params()
    engine.set_running(True)
    print(f"[i] 随机后 波形={window._current_wave} 波束={window.btn_beam.isChecked()} "
          f"位置={window.s_beam_pos.value():.2f}")


def start_listen():
    window.beam_panel.set_listening(True)
    print(f"[i] 聆听 running={window.player.running} err={window.player.error!r}")


def shot_beam_tab():
    window.tabs.setCurrentIndex(3)
    out = Path(str(OUT_TAB).format(n=2))
    window.grab().save(str(out))
    print(f"[ok] 虚拟波束页 -> {out.resolve()}")


def shot_waveparams_tab():
    window.tabs.setCurrentIndex(1)
    out = Path(str(OUT_TAB).format(n=1))
    window.grab().save(str(out))
    print(f"[ok] 波形参数页 -> {out.resolve()}")


def shot_enhance_tab():
    window.tabs.setCurrentIndex(2)
    out = Path(str(OUT_TAB).format(n=3))
    window.grab().save(str(out))
    print(f"[ok] 体感增强页 -> {out.resolve()}")


def shot_audio_tab():
    window.tabs.setCurrentIndex(5)
    out = Path(str(OUT_TAB).format(n=4))
    window.grab().save(str(out))
    print(f"[ok] 音频跟随页 -> {out.resolve()}")


def shot_beam():
    window.tabs.setCurrentIndex(0)
    window.grab().save(str(OUT_BEAM))
    print(f"[ok] 波束+随机 -> {OUT_BEAM.resolve()}")
    print(f"[i] 引擎 L={engine.left_raw} R={engine.right_raw} "
          f"beam_pos={engine.beam_position:+.2f} 声像L={engine.env_l:.2f}")
    print(f"[i] 播放器电平={window.player.level}")


def shot_curve():
    window.tabs.setCurrentIndex(4)
    window.grab().save(str(OUT_CURVE))
    print(f"[ok] 曲线页 -> {OUT_CURVE.resolve()}")


def finish():
    engine.set_running(False)
    window.player.stop()
    window.capture.stop()
    print(f"[ok] 收尾 running={engine.is_running()} L={engine.left_raw} R={engine.right_raw}")
    window.close()
    app.quit()


step("主界面截图", shot_main)
step("开启波束+随机搭配", enable_features)
step("开启聆听波束", start_listen)
step("波束+随机 截图", shot_beam)
step("波形参数页截图", shot_waveparams_tab)
step("体感增强页截图", shot_enhance_tab)
step("虚拟波束页截图", shot_beam_tab)
step("音频跟随页截图", shot_audio_tab)
step("曲线页截图", shot_curve)

QTimer.singleShot(900, run_next)
sys.exit(app.exec())
