"""No-op provider for batch / cmd tools that have no ecosystem deps.

Spec §6: "no-op, exists so batch tools have a consistent (empty) row
instead of a special case in the UI."
"""
from __future__ import annotations


ecosystem = "none"


def scan(tool) -> list[dict]:
    return []


def install(missing: list[dict]) -> tuple[int, str]:
    return 0, "[OK] Batch tools have no ecosystem dependencies.\n"
