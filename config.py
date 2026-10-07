"""配置持久化 —— 所有参数存到 exe 同目录的 presets.json。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_NAME = "手柄震动按摩控制器"
CONFIG_FILENAME = "presets.json"
CONFIG_VERSION = 1

_DEFAULTS: dict[str, Any] = {
    "version": CONFIG_VERSION,
    "last_device_index": 0,
    "auto_restore": True,
    "params": {
        # 强度
        "master": 0.80,
        "left_gain": 1.00,
        "right_gain": 1.00,
        # 波形
        "waveform_b": "",
        "mix": 0.00,
        "speed": 1.00,
        "floor": 0.00,
        "smoothing": 0.15,
        "phase_shift": 0.00,
        # 虚拟波束
        "beam_enabled": False,
        "beam_position": 0.00,
        "beam_width": 0.45,
        "beam_sweep": False,
        "beam_sweep_rate": 0.50,
        "beam_beat_hz": 0.00,
        "beam_polarity": "in",
        # 音频跟随
        "source": "waveform",
        "audio_gain_l": 1.00,
        "audio_gain_r": 1.00,
        "audio_threshold": 0.04,
        "audio_sensitivity": 2.20,
        # 体感增强
        "sharpen": 0.50,
        "noise_floor": 0.00,
        "anti_adapt": 0.20,
        "duty": 1.00,
    },
    "waveform": "breath",
    "curve_duration": 4.0,
    "custom_curve": [
        [0.00, 0.10],
        [0.22, 1.00],
        [0.42, 0.25],
        [0.62, 0.85],
        [0.80, 0.15],
    ],
    "beam": {
        "volume": 0.55,
        "timbre": "rumble",
        "auto_interval": 12.0,
        "spicy": False,
        "sfx": True,
    },
}


def app_dir() -> Path:
    """打包成 exe 后取 exe 所在目录，否则取项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return app_dir() / CONFIG_FILENAME


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return json.loads(json.dumps(_DEFAULTS))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("配置根节点不是对象")
        return _deep_merge(_DEFAULTS, data)
    except Exception:
        return json.loads(json.dumps(_DEFAULTS))


def save(data: dict[str, Any]) -> bool:
    data = dict(data)
    data["version"] = CONFIG_VERSION
    path = config_path()
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False


def defaults() -> dict[str, Any]:
    return json.loads(json.dumps(_DEFAULTS))
