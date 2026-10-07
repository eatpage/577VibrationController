"""字体兜底。

正常情况下 Windows 桌面会话里 Qt 能直接枚举到「微软雅黑」，什么都不用做。
但在某些受限环境（沙箱、服务账户、离屏渲染）里系统字体库会是空的，
此时中文会全部渲染成方框。这里做一层兜底：直接按路径加载字体文件。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase

PREFERRED_FAMILIES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "SimSun",
)

# 常见中文字体文件（按优先级）
FONT_FILES = (
    r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",    # 黑体
    r"C:\Windows\Fonts\simsun.ttc",    # 宋体
    r"C:\Windows\Fonts\Deng.ttf",      # 等线
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def resolve_family() -> str:
    """返回一个可用的中文字体族名；实在找不到就返回空串（交给 Qt 自行回退）。"""
    families = set(QFontDatabase.families())

    for name in PREFERRED_FAMILIES:
        if name in families:
            return name

    # 系统字体库为空或缺少中文字体 —— 手动按路径加载
    for path in FONT_FILES:
        if not Path(path).exists():
            continue
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id < 0:
            continue
        loaded = QFontDatabase.applicationFontFamilies(font_id)
        # 优先挑一个已知的中文字体族名
        for name in PREFERRED_FAMILIES:
            if name in loaded:
                return name
        if loaded:
            fallback = loaded[0]
            print(f"[fonts] 已加载备用中文字体 {fallback}（{path}）", file=sys.stderr)
            return fallback

    return ""
