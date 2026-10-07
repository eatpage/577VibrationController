"""PyInstaller 打包脚本 —— 产出单文件 exe。

用法：
    python build.py            # 构建
    python build.py --dir      # 构建文件夹版（调试用，启动更快）
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
APP_NAME = "VibrationController"     # 通用英文名，跨语言环境都不会出乱码
ICON = ROOT / "assets" / "app.ico"

# 明确不用的模块，剔掉能省几十 MB
EXCLUDES = [
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtSensors",
    "PySide6.QtSerialPort", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner",
    "PySide6.QtUiTools", "PySide6.QtHelp", "PySide6.QtScxml", "PySide6.QtRemoteObjects",
    "PySide6.QtTextToSpeech", "PySide6.QtVirtualKeyboard", "PySide6.Qt3DCore",
    "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtNetworkAuth", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtStateMachine",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtConcurrent",
    "tkinter", "PIL", "matplotlib", "pandas", "scipy",
]
# 注意：numpy 不能排除 —— 音频分频与音效合成都要用。


def main() -> int:
    if not ICON.exists():
        print("未找到图标，正在生成…")
        import make_icon
        make_icon.main()

    onedir = "--dir" in sys.argv
    args = [
        str(ROOT / "main.py"),
        f"--name={APP_NAME}",
        "--icon=" + str(ICON),
        "--add-data=" + f"{ICON}{';' if sys.platform == 'win32' else ':'}assets",
        "--noconfirm",
        "--clean",
        "--console" if onedir and "--console" in sys.argv else "--windowed",
        "--distpath=" + str(ROOT / "dist"),
        "--workpath=" + str(ROOT / "build"),
        "--specpath=" + str(ROOT),
        "--onefile" if not onedir else "--onedir",
    ]
    for mod in EXCLUDES:
        args.append(f"--exclude-module={mod}")

    print("PyInstaller 参数：")
    for a in args:
        print("   ", a)
    print()

    PyInstaller.__main__.run(args)

    if onedir:
        print("\n[ok] 文件夹版输出： dist/{}".format(APP_NAME))
        return 0

    built = ROOT / "dist" / f"{APP_NAME}.exe"
    if not built.exists():
        print("[FAIL] 未找到构建产物：", built)
        return 1

    # 顺手清掉 PyInstaller 留下的 spec 与工作目录，保持根目录干净
    for junk in (ROOT / f"{APP_NAME}.spec",):
        try:
            if junk.exists():
                junk.unlink()
        except Exception:
            pass

    size = built.stat().st_size / 1024 / 1024
    print(f"\n[ok] 构建产物：{built}  ({size:.1f} MB)")

    # 顺带把说明文档拷进 dist
    for name in ("README.md", "使用手册.md"):
        src = ROOT / name
        if src.exists():
            try:
                shutil.copy2(src, ROOT / "dist" / name)
            except Exception:
                pass

    print("\n双击 exe 即可运行，配置会写在 exe 同目录的 presets.json。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
