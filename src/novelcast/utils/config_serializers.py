from typing import Any
from hashlib import sha256


def format_value(value: Any) -> str:

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def build_key_value_lines(
    settings: dict,
    *,
    skip_keys: set[str] | None = None,
    header: str | None = None,
) -> list[str]:

    skip_keys = skip_keys or set()

    lines = []

    if header:
        lines.append(f"[{header}]")
        lines.append("")

    for key, value in settings.items():
        if key in skip_keys:
            continue

        formatted = format_value(value)
        lines.append(f"{key}:{formatted}")

    lines.append("")
    return lines


def compute_lines_hash(lines: list[str]) -> str:
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()