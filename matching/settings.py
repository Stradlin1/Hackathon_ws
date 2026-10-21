"""Runtime settings for the optional integrations.

Manual configuration lives in settings.yaml at the repository root (gitignored).
Every value can also come from an environment variable, which keeps CI and one-off
shell runs working without editing a file.

Precedence: environment variable > settings.yaml > default.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parent.parent / 'settings.yaml'

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            with PATH.open(encoding='utf-8') as handle:
                data = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        _cache = data if isinstance(data, dict) else {}
    return _cache


def _lookup(data: dict, dotted: str):
    node = data
    for part in dotted.split('.'):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def get(dotted: str, default=None, env: str | None = None):
    """Value for a dotted key; the environment variable wins when it is set."""
    if env:
        value = os.environ.get(env)
        if value not in (None, ''):
            return value
    value = _lookup(_load(), dotted)
    return default if value in (None, '') else value


def flag(dotted: str, default: bool = True, env: str | None = None) -> bool:
    """Boolean setting that accepts on/off, true/false, 1/0."""
    value = get(dotted, default, env=env)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ('off', '0', 'false', 'no')


def number(dotted: str, default: float, env: str | None = None) -> float:
    try:
        return float(get(dotted, default, env=env))
    except (TypeError, ValueError):
        return default
