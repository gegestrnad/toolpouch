import json
from pathlib import Path
from datetime import datetime
import base64


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".toolpouch"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.log_dir = self.config_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Failed to load config: {e}")
        
        return self._default_config()

    def _default_config(self) -> dict:
        return {
            "theme": "Modern Dark",
            "window.geometry": None,
            "last_tool": None,
            "recent_tools": [],
        }

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default

        # Special-case geometry: decode base64 string to bytes if needed
        if key == "window.geometry" and isinstance(value, str):
            if value.startswith("b64:"):
                try:
                    return base64.b64decode(value[4:])
                except Exception:
                    return default
        return value

    def set(self, key: str, value):
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Special-case geometry: store bytes as base64-encoded string
        if key == "window.geometry" and (isinstance(value, (bytes, bytearray)) or hasattr(value, 'data')):
            try:
                # If it's a Qt QByteArray-like object with .data(), get the bytes
                if hasattr(value, 'data'):
                    raw = bytes(value.data())
                else:
                    raw = bytes(value)
                current[keys[-1]] = "b64:" + base64.b64encode(raw).decode('ascii')
                return
            except Exception:
                # Fallback to str
                current[keys[-1]] = str(value)
                return

        current[keys[-1]] = value

    def save(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")

    def log_execution(self, tool_name: str, success: bool, output: str = ""):
        """Log tool execution for history and debugging."""
        log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "SUCCESS" if success else "FAILED"
        
        try:
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {tool_name} - {status}\n")
                if output:
                    f.write(f"{output}\n")
                f.write("---\n")
        except Exception as e:
            print(f"[ConfigManager] Failed to log execution: {e}")

    def add_recent_tool(self, tool_name: str):
        """Add tool to recent tools list."""
        recent = self.get("recent_tools", [])
        if tool_name in recent:
            recent.remove(tool_name)
        recent.insert(0, tool_name)
        self.set("recent_tools", recent[:10])  # Keep last 10
        self.save()
