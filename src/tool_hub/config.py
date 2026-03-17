from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import HubConfig

DEFAULT_CONFIG_ENV = "TOOL_HUB_CONFIG"


def resolve_config_path(explicit_path: str | None = None) -> Path:
    candidate = explicit_path or os.environ.get(DEFAULT_CONFIG_ENV)
    if not candidate:
        raise FileNotFoundError(
            "No config path provided. Pass --config or set TOOL_HUB_CONFIG."
        )

    path = Path(candidate).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    return path


def load_config(explicit_path: str | None = None) -> HubConfig:
    config_path = resolve_config_path(explicit_path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return HubConfig.model_validate(raw)

