"""Environment-only secret references for generated and user-created Skills."""

from __future__ import annotations

import os
import re

_REFERENCE = re.compile(r"\$\{secret:([A-Za-z][A-Za-z0-9_-]{0,63})\}")


def environment_name(name: str) -> str:
    return "RPA_SECRET_" + re.sub(r"[^A-Za-z0-9]", "_", name).upper()


def get_secret(name: str, default: str | None = None) -> str | None:
    """Get a local secret from RPA_SECRET_<NAME>; no secret file is created."""
    return os.environ.get(environment_name(name), default)


def expand_secret_references(value):
    """Expand ${secret:name} values recursively, failing closed when unavailable."""
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            secret = get_secret(name)
            if secret is None:
                raise ValueError(f"Missing secret {name!r}. Set {environment_name(name)} locally.")
            return secret

        return _REFERENCE.sub(replace, value)
    if isinstance(value, dict):
        return {key: expand_secret_references(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_secret_references(item) for item in value]
    return value
