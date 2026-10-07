"""运行时国际化。

以**中文原文**作为 key（gettext 风格）。静态界面文案不需要在代码里逐个包函数，
构建完界面后调用 `translate_tree()` 遍历控件树统一替换即可；
动态拼接的文案用 `tr()` 显式翻译。
"""

from __future__ import annotations

from typing import Optional

LANGUAGES: tuple[tuple[str, str], ...] = (
    ("zh", "中文"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("ru", "Русский"),
)

DEFAULT_LANGUAGE = "zh"

_current = DEFAULT_LANGUAGE


def available() -> tuple[tuple[str, str], ...]:
    return LANGUAGES


def language_name(code: str) -> str:
    for key, name in LANGUAGES:
        if key == code:
            return name
    return code


def current() -> str:
    return _current


def set_language(code: str) -> None:
    global _current
    if any(k == code for k, _ in LANGUAGES):
        _current = code


def _table() -> dict:
    if _current == DEFAULT_LANGUAGE:
        return {}
    from . import lang_en, lang_ja, lang_ko, lang_ru

    return {
        "en": lang_en.TABLE,
        "ja": lang_ja.TABLE,
        "ko": lang_ko.TABLE,
        "ru": lang_ru.TABLE,
    }.get(_current, {})


def tr(text: Optional[str], **kwargs) -> str:
    """把中文原文翻译成当前语言。没有对应译文时原样返回。"""
    if not text:
        return text or ""
    out = text
    if _current != DEFAULT_LANGUAGE:
        out = _table().get(text, text)
    if kwargs:
        try:
            out = out.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return out


def has(text: str) -> bool:
    """当前语言下是否有这条译文。"""
    if _current == DEFAULT_LANGUAGE:
        return True
    return text in _table()


# ==================================================================== 控件树翻译


def translate_tree(root) -> None:
    """遍历控件树，把能查到的文案替换掉。查不到的保持原样。"""
    if _current == DEFAULT_LANGUAGE:
        return

    from PySide6.QtWidgets import (
        QAbstractButton,
        QComboBox,
        QGroupBox,
        QLabel,
        QTabWidget,
        QWidget,
    )

    for widget in root.findChildren(QWidget):
        if isinstance(widget, QLabel):
            widget.setText(tr(widget.text()))
        elif isinstance(widget, QAbstractButton):
            widget.setText(tr(widget.text()))
        elif isinstance(widget, QGroupBox):
            widget.setTitle(tr(widget.title()))
        elif isinstance(widget, QTabWidget):
            for i in range(widget.count()):
                widget.setTabText(i, tr(widget.tabText(i)))
        elif isinstance(widget, QComboBox):
            for i in range(widget.count()):
                widget.setItemText(i, tr(widget.itemText(i)))

        tip = widget.toolTip()
        if tip:
            widget.setToolTip(tr(tip))

    # QTabWidget 的页面不是 QObject 子级，需要单独递归
    for tabs in root.findChildren(QTabWidget):
        for i in range(tabs.count()):
            page = tabs.widget(i)
            if page is not None:
                translate_tree(page)
