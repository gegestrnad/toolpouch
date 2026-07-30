"""Dependency providers — one per ecosystem (spec §6).

The DependencyManager UI collects statuses from all providers and shows
them in a single unified table with an Ecosystem column.
"""
from __future__ import annotations

from typing import Protocol


class DependencyProvider(Protocol):
    """Each provider knows how to scan one ecosystem and install missing
    packages for that ecosystem.

    ``scan`` returns a list of ``DependencyStatus``-shaped dicts (we use
    dicts here rather than the dataclass to keep the protocol boundary
    clean — the UI is the only consumer).

    ``install`` is a no-op for the ``none`` ecosystem and for ecosystems
    where the user has no installer available.
    """

    ecosystem: str

    def scan(self, tool) -> list[dict]: ...

    def install(self, missing: list[dict]) -> tuple[int, str]:
        """Install the given missing specs. Returns ``(success_count, log_text)``."""
        ...
