from __future__ import annotations

from collections.abc import Iterable


STATUS_ORDER = {
    "ok": 0,
    "warning": 1,
    "critical": 2,
}


def normalize_status(value: str) -> str:
    lowered = (value or "").strip().lower()
    if lowered not in STATUS_ORDER:
        return "critical"
    return lowered


def combine_statuses(values: Iterable[str]) -> str:
    winner = "ok"
    highest = -1
    for value in values:
        normalized = normalize_status(value)
        rank = STATUS_ORDER[normalized]
        if rank > highest:
            winner = normalized
            highest = rank
    return winner


def exit_code_for_status(value: str) -> int:
    normalized = normalize_status(value)
    if normalized == "ok":
        return 0
    if normalized == "warning":
        return 1
    return 2

