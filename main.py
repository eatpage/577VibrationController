"""手柄震动按摩控制器 —— 启动入口。

用法：
    python main.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

# 保证以任意工作目录启动都能找到 `core` / `ui`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import config as cfg_module  # noqa: E402
from core.rumble_engine import RumbleEngine  # noqa: E402
from ui import theme  # noqa: E402
from ui.fonts import resolve_family  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


def _install_excepthook(app: QApplication) -> None:
    def hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        sys.stderr.write(text)
        try:
            QMessageBox.critical(None, "出现未处理的错误", text[-1500:])
        except Exception:
            pass

    sys.excepthook = hook


def resource_path(relative: str) -> Path:
    """兼容源码运行与 PyInstaller 单文件解包后的资源定位。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def run_frozen_selftest(out_path: Path) -> int:
    """打包后的自检：--windowed 没有控制台，所以把结果写到文件里。

    用法：  手柄震动按摩控制器.exe --selftest
    """
    import traceback

    lines: list[str] = []

    def log(text: str) -> None:
        lines.append(text)

    log(f"frozen = {getattr(sys, 'frozen', False)}")
    log(f"executable = {sys.executable}")

    try:
        import numpy
        log(f"[ok] numpy {numpy.__version__}")
    except Exception as exc:
        log(f"[FAIL] numpy: {exc}")

    try:
        import pyaudiowpatch as pa
        hub_ok = True
        log(f"[ok] pyaudiowpatch {getattr(pa, '__version__', '?')}")
    except Exception as exc:
        hub_ok = False
        log(f"[FAIL] pyaudiowpatch: {exc}")

    if hub_ok:
        try:
            from core.audio import AudioHub
            hub = AudioHub.instance()
            log(f"audio hub available = {hub.available}  err={hub.error!r}")
            out = hub.default_output()
            log(f"default output = {out.name if out else None}")
            devices = hub.list_loopback_devices()
            log(f"loopback devices = {len(devices)}")
            for d in devices[:5]:
                log(f"   - {d.index}  {d.name}  {d.samplerate}Hz")
            hub.terminate()
        except Exception:
            log("[FAIL] 音频枚举异常:\n" + traceback.format_exc())

    try:
        from core import xinput_backend
        backend = xinput_backend.get_backend()
        log(f"[{'ok' if backend.available else 'FAIL'}] xinput dll = {backend.dll_name or '(无)'}")
        for info in backend.enumerate():
            log(f"   - {info.label}")
    except Exception:
        log("[FAIL] XInput 异常:\n" + traceback.format_exc())

    try:
        from core.waveforms import WAVEFORMS, random_preset
        log(f"[ok] 波形数量 = {len(WAVEFORMS)}")
        p = random_preset()
        log(f"[ok] random_preset -> {p.waveform}" + (f" + {p.waveform_b}" if p.waveform_b else ""))
    except Exception:
        log("[FAIL] 波形库异常:\n" + traceback.format_exc())

    try:
        from core import sfx
        data = sfx.render("click")
        log(f"[ok] sfx 合成 = {len(data)} bytes, winsound={sfx.player().available}")
    except Exception:
        log("[FAIL] 音效异常:\n" + traceback.format_exc())

    # Qt 组件必须在 QApplication 之后才能碰 —— 否则 QFontDatabase 会直接 abort 进程
    qt_app = None
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        log(f"[ok] PySide6 导入成功")
        qt_app = QApplication.instance() or QApplication(["selftest"])
        log("[ok] QApplication 创建成功（offscreen）")
    except Exception as exc:
        log(f"[warn] Qt 应用创建失败，跳过字体检查：{exc}")

    if qt_app is not None:
        try:
            from ui.fonts import resolve_family
            log(f"[ok] 解析到字体 = {resolve_family()!r}")
        except Exception:
            log("[FAIL] 字体异常:\n" + traceback.format_exc())
        try:
            from ui import theme
            qss = theme.stylesheet("Microsoft YaHei UI")
            log(f"[ok] 样式表长度 = {len(qss)}")
        except Exception:
            log("[FAIL] 样式表异常:\n" + traceback.format_exc())

    text = "\n".join(lines)
    try:
        out_path.write_text(text, encoding="utf-8")
    except Exception:
        pass
    try:
        print(text)
    except Exception:
        pass
    return 0 if "FAIL" not in text else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return run_frozen_selftest(
            Path(sys.executable).resolve().parent / "selftest_result.txt"
        )

    QApplication.setApplicationName(cfg_module.APP_NAME)
    QApplication.setOrganizationName("XInputVibe")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    family = resolve_family() or "Microsoft YaHei UI"
    app.setStyleSheet(theme.stylesheet(family))

    font = QFont(family, 9)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    icon_path = resource_path("assets/app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    _install_excepthook(app)

    engine = RumbleEngine(tick_hz=125)
    window = MainWindow(engine)
    window.show()

    try:
        return app.exec()
    finally:
        engine.shutdown()


if __name__ == "__main__":
    sys.exit(main())
