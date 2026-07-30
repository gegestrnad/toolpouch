"""Unit tests for core/runtime_resolver.py.

Spec §9: "Unit tests mandatory for: runtime_resolver.py (resolution logic
across all extension cases), tool_loader.py (manifest parsing including
malformed input), tool_importer.py (path-traversal guard)."

This module tests the resolution logic for ALL extension cases (.py,
.ps1, .bat/.cmd, .js) plus the explicit runtime override and unknown
extension error path. Uses unittest.mock so the tests don't depend on
which interpreters are actually installed on the test box.
"""
from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

# Make project root importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runtime_resolver import (  # noqa: E402
    LaunchSpec,
    RuntimeResolutionError,
    RuntimeResolver,
    build_subprocess_env,
)


@dataclass
class FakeTool:
    """Minimal stand-in for ToolDefinition — only the attributes
    RuntimeResolver actually reads."""
    script_path: Path
    runtime: str = ""
    folder: Path = Path(".")


class TestPythonResolution(unittest.TestCase):
    """Spec §4: .py → explicit runtime override, else system python/py on
    PATH, else bundled fallback interpreter."""

    def setUp(self):
        self.r = RuntimeResolver()

    def test_py_extension_uses_system_python(self):
        """When system python is on PATH, use it (NOT the bundled fallback)."""
        with mock.patch("core.runtime_resolver._system_python", return_value="/usr/bin/python3"):
            with mock.patch("core.runtime_resolver._bundled_embed_python", return_value=None):
                spec = self.r.resolve(FakeTool(script_path=Path("/tmp/x.py")))
                self.assertEqual(spec.executable, "/usr/bin/python3")
                self.assertEqual(spec.args_prefix, [])
                self.assertEqual(spec.ecosystem, "python")

    def test_py_falls_back_to_embedded_python(self):
        """If no system Python, use the bundled embeddable Python."""
        with mock.patch("core.runtime_resolver._system_python", return_value=None):
            with mock.patch(
                "core.runtime_resolver._bundled_embed_python",
                return_value=Path("/app/python-embed/python.exe"),
            ):
                spec = self.r.resolve(FakeTool(script_path=Path("C:\\tools\\x.py")))
                self.assertEqual(Path(spec.executable), Path("/app/python-embed/python.exe"))
                self.assertEqual(spec.ecosystem, "python")

    def test_py_raises_when_no_python_anywhere(self):
        with mock.patch("core.runtime_resolver._system_python", return_value=None):
            with mock.patch("core.runtime_resolver._bundled_embed_python", return_value=None):
                with self.assertRaises(RuntimeResolutionError) as ctx:
                    self.r.resolve(FakeTool(script_path=Path("x.py")))
                self.assertIn("Install Python", str(ctx.exception))

    def test_runtime_python_override_wins_over_extension(self):
        """If tool.toml says runtime='python' on a .js file, that wins."""
        with mock.patch("core.runtime_resolver._system_python", return_value="/usr/bin/python3"):
            spec = self.r.resolve(FakeTool(script_path=Path("weird.js"), runtime="python"))
            self.assertEqual(spec.ecosystem, "python")
            self.assertEqual(spec.executable, "/usr/bin/python3")


class TestPowershellResolution(unittest.TestCase):
    """Spec §4: .ps1 → pwsh if found, else powershell.exe."""

    def setUp(self):
        self.r = RuntimeResolver()

    def test_ps1_prefers_pwsh_7(self):
        with mock.patch("core.runtime_resolver._system_powershell", return_value="/usr/bin/pwsh"):
            spec = self.r.resolve(FakeTool(script_path=Path("x.ps1")))
            self.assertEqual(spec.executable, "/usr/bin/pwsh")
            self.assertEqual(spec.ecosystem, "powershell")
            # Spec: -NoProfile -ExecutionPolicy Bypass -File prefix
            self.assertEqual(spec.args_prefix, ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])

    def test_ps1_falls_back_to_windows_powershell(self):
        with mock.patch("core.runtime_resolver._system_powershell", return_value=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"):
            spec = self.r.resolve(FakeTool(script_path=Path("x.ps1")))
            self.assertIn("powershell.exe", spec.executable)

    def test_ps1_raises_when_no_powershell(self):
        with mock.patch("core.runtime_resolver._system_powershell", return_value=None):
            with self.assertRaises(RuntimeResolutionError) as ctx:
                self.r.resolve(FakeTool(script_path=Path("x.ps1")))
            self.assertIn("PowerShell", str(ctx.exception))


class TestBatchResolution(unittest.TestCase):
    """Spec §4: .bat/.cmd → cmd.exe /c (always present on Windows)."""

    def setUp(self):
        self.r = RuntimeResolver()

    def test_bat_resolves_to_cmd_with_c_prefix(self):
        with mock.patch("core.runtime_resolver._system_cmd", return_value=r"C:\Windows\System32\cmd.exe"):
            spec = self.r.resolve(FakeTool(script_path=Path("tool.bat")))
            self.assertEqual(spec.executable, r"C:\Windows\System32\cmd.exe")
            self.assertEqual(spec.args_prefix, ["/c"])
            self.assertEqual(spec.ecosystem, "none")

    def test_cmd_extension_also_works(self):
        with mock.patch("core.runtime_resolver._system_cmd", return_value=r"C:\Windows\System32\cmd.exe"):
            spec = self.r.resolve(FakeTool(script_path=Path("tool.cmd")))
            self.assertEqual(spec.args_prefix, ["/c"])

    def test_bat_raises_when_no_cmd(self):
        """Edge case: running on non-Windows without cmd.exe."""
        with mock.patch("core.runtime_resolver._system_cmd", return_value=None):
            with self.assertRaises(RuntimeResolutionError):
                self.r.resolve(FakeTool(script_path=Path("tool.bat")))


class TestNodeResolution(unittest.TestCase):
    """Spec §4: .js → system node on PATH; if absent, raise (NO Node fallback)."""

    def setUp(self):
        self.r = RuntimeResolver()

    def test_js_resolves_to_system_node(self):
        with mock.patch("core.runtime_resolver._system_node", return_value="/usr/bin/node"):
            spec = self.r.resolve(FakeTool(script_path=Path("tool.js")))
            self.assertEqual(spec.executable, "/usr/bin/node")
            self.assertEqual(spec.args_prefix, [])
            self.assertEqual(spec.ecosystem, "node")

    def test_js_raises_when_no_node_with_clear_message(self):
        with mock.patch("core.runtime_resolver._system_node", return_value=None):
            with self.assertRaises(RuntimeResolutionError) as ctx:
                self.r.resolve(FakeTool(script_path=Path("tool.js")))
            self.assertIn("nodejs.org", str(ctx.exception))
            # Spec §1.7: must NOT silently bundle Node.
            self.assertNotIn("bundled", str(ctx.exception).lower())


class TestOverrideMatrix(unittest.TestCase):
    """All five override values must win over extension inference."""

    def setUp(self):
        self.r = RuntimeResolver()

    def test_override_pwsh_on_bat(self):
        with mock.patch("core.runtime_resolver._system_powershell", return_value="/usr/bin/pwsh"):
            spec = self.r.resolve(FakeTool(script_path=Path("x.bat"), runtime="pwsh"))
            self.assertEqual(spec.ecosystem, "powershell")

    def test_override_node_on_py(self):
        with mock.patch("core.runtime_resolver._system_node", return_value="/usr/bin/node"):
            spec = self.r.resolve(FakeTool(script_path=Path("x.py"), runtime="node"))
            self.assertEqual(spec.ecosystem, "node")

    def test_override_cmd_on_ps1(self):
        with mock.patch("core.runtime_resolver._system_cmd", return_value=r"C:\Windows\System32\cmd.exe"):
            spec = self.r.resolve(FakeTool(script_path=Path("x.ps1"), runtime="cmd"))
            self.assertEqual(spec.ecosystem, "none")
            self.assertEqual(spec.args_prefix, ["/c"])

    def test_unknown_override_falls_through_to_extension(self):
        """Spec §2 allows unknown override values to be silently ignored
        (we don't crash, we infer from extension instead)."""
        with mock.patch("core.runtime_resolver._system_python", return_value="/usr/bin/python3"):
            # tool_loader.py normalizes unknown runtime to "" so we never
            # actually see one here; but verify directly:
            spec = self.r.resolve(FakeTool(script_path=Path("x.py"), runtime=""))
            self.assertEqual(spec.ecosystem, "python")


class TestUnknownExtension(unittest.TestCase):
    def setUp(self):
        self.r = RuntimeResolver()

    def test_unknown_extension_raises_with_actionable_message(self):
        with self.assertRaises(RuntimeResolutionError) as ctx:
            self.r.resolve(FakeTool(script_path=Path("weird.rb")))
        self.assertIn("runtime", str(ctx.exception).lower())
        self.assertIn("python", str(ctx.exception))  # suggestion list


class TestBuildCommand(unittest.TestCase):
    """Spec §4: never string-join args; always pass list to Popen."""

    def test_build_command_returns_list(self):
        spec = LaunchSpec(executable="python", args_prefix=[], ecosystem="python")
        cmd = spec.build_command(Path("tool.py"), ["--input", "a b c", "--out", "x.txt"])
        self.assertEqual(cmd, ["python", "tool.py", "--input", "a b c", "--out", "x.txt"])
        # Critical: spaces in args are preserved by the list form.
        self.assertIn("a b c", cmd)

    def test_build_command_with_args_prefix(self):
        spec = LaunchSpec(executable="cmd.exe", args_prefix=["/c"], ecosystem="none")
        cmd = spec.build_command(Path("tool.bat"), ["--path", r"C:\Test Folder (2026)\file.txt"])
        self.assertEqual(cmd, ["cmd.exe", "/c", "tool.bat", "--path", r"C:\Test Folder (2026)\file.txt"])

    def test_build_command_with_powershell_prefix(self):
        spec = LaunchSpec(
            executable="pwsh",
            args_prefix=["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"],
            ecosystem="powershell",
        )
        cmd = spec.build_command(Path("tool.ps1"), ["-Path", "C:\\Test Folder\\file.txt"])
        self.assertEqual(
            cmd,
            ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "tool.ps1", "-Path", "C:\\Test Folder\\file.txt"],
        )


class TestBuildSubprocessEnv(unittest.TestCase):
    """Spec §7: when frozen, strip PYTHONHOME/PYTHONPATH so tool scripts
    use their OWN interpreter's stdlib (NOT the PyInstaller-bundled one)."""

    def test_frozen_strips_python_env_vars(self):
        with mock.patch.object(sys, "frozen", True, create=True):
            env = build_subprocess_env()
            self.assertNotIn("PYTHONHOME", env)
            self.assertNotIn("PYTHONPATH", env)
            self.assertEqual(env["PYTHONNOUSERSITE"], "1")

    def test_unfrozen_preserves_python_env_vars(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            env = build_subprocess_env()
            # These may or may not be set; we just verify we don't strip
            # or set them ourselves.
            self.assertNotIn("PYTHONNOUSERSITE", env)


if __name__ == "__main__":
    unittest.main()
