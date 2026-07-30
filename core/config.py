"""User configuration store.

Ported from v2 with these changes:
- Dropped the Qt ``QByteArray`` special-case for ``window.geometry``.
  CustomTkinter has no QByteArray equivalent; geometry is stored as a plain
  ``"WxH+X+Y"`` string and re-applied via ``CTk.geometry(...)``.
- Everything else is a straight port: same defaults, same recent-tools cap
  of 10, same per-day log files under ``~/.toolpouch/logs``.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


DEFAULT_THEME = "Modern Dark"


class ConfigManager:
    """Persistent JSON config at ``~/.toolpouch/config.json``.

    Single-instance, intentionally NOT thread-safe — caller is expected to
    touch it from the main UI thread, same as v2.
    """

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".toolpouch"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.log_dir = self.config_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self._config = self._load_config()

    # ------------------------------------------------------------------ load
    def _load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                defaults = self._default_config()
                if isinstance(loaded, dict):
                    defaults.update(loaded)
                return self._normalize_config(defaults)
            except Exception as e:
                print(f"[ConfigManager] Failed to load config: {e}")
        return self._default_config()

    def _default_config(self) -> dict:
        return {
            "theme": DEFAULT_THEME,
            "window.geometry": None,
            "last_tool": None,
            "recent_tools": [],
            "favorite_tools": [],
            "tool_sort_order": "Default",
        }

    def _normalize_config(self, config: dict) -> dict:
        config["recent_tools"] = self._clean_tool_id_list(config.get("recent_tools", []), limit=10)
        config["favorite_tools"] = self._clean_tool_id_list(config.get("favorite_tools", []))
        if config.get("tool_sort_order") not in {"Default", "Name A-Z", "Name Z-A", "Recently Used"}:
            config["tool_sort_order"] = "Default"
        if not isinstance(config.get("theme"), str) or not config["theme"].strip():
            config["theme"] = DEFAULT_THEME
        return config

    def _clean_tool_id_list(self, value, limit: int | None = None) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            tool_id = item.strip()
            if not tool_id or tool_id in seen:
                continue
            cleaned.append(tool_id)
            seen.add(tool_id)
            if limit is not None and len(cleaned) >= limit:
                break
        return cleaned

    # ------------------------------------------------------------------ get/set
    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def set(self, key: str, value) -> None:
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current or not isinstance(current.get(k), dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def save(self) -> None:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, default=str)
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")

    # ------------------------------------------------------------------ logs / recents
    def log_execution(self, tool_name: str, success: bool, output: str = "") -> None:
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {tool_name} - {status}\n")
                if output:
                    f.write(f"{output}\n")
                f.write("---\n")
        except Exception as e:
            print(f"[ConfigManager] Failed to log execution: {e}")

    def add_recent_tool(self, tool_name: str) -> None:
        if not isinstance(tool_name, str) or not tool_name.strip():
            return
        tool_name = tool_name.strip()
        recent = self._clean_tool_id_list(self.get("recent_tools", []))
        if tool_name in recent:
            recent.remove(tool_name)
        recent.insert(0, tool_name)
        self.set("recent_tools", recent[:10])
        self.save()
