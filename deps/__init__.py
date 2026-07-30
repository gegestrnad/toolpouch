"""Provider registry: maps ecosystem name → module."""
from __future__ import annotations

from deps import (
    none_provider,
    node_provider,
    powershell_provider,
    python_provider,
)


PROVIDERS = {
    "python": python_provider,
    "node": node_provider,
    "powershell": powershell_provider,
    "none": none_provider,
}


def scan_all(tool) -> list[dict]:
    """Run every provider against ``tool`` and concat results. A tool's
    dependencies can span ecosystems (rare but allowed by the schema)."""
    out: list[dict] = []
    for prov in PROVIDERS.values():
        try:
            out.extend(prov.scan(tool))
        except Exception as e:
            # A provider crashing must never kill the whole scan.
            print(f"[deps] {prov.__name__}.scan failed: {e}")
    return out


def install_for_ecosystem(ecosystem: str, missing: list[dict]) -> tuple[int, str]:
    prov = PROVIDERS.get(ecosystem, none_provider)
    return prov.install(missing)
