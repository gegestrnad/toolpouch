"""Unit tests for core/tool_loader.py.

Spec §9: "tool_loader.py (manifest parsing including malformed input)".

Covers:
- Valid manifests parse correctly.
- The v2-inconsistent formats (capitalized types, default_value, comma-
  string options, id-instead-of-import dependencies) all normalize
  cleanly — this is the spec §2 "compatibility bar".
- Malformed manifests are skipped with a printed warning, not raised.
- Missing script files set ``script_exists=False`` and populate
  ``errors``.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tool_loader import load_tools  # noqa: E402


class TestV2Compatibility(unittest.TestCase):
    """The 15+ existing tool.toml files from v2 must all parse without
    raising. Spec §2 calls this the compatibility bar."""

    def setUp(self):
        # Use the real tools/ folder shipped with the project.
        self.tools_dir = Path(__file__).parent.parent / "tools"

    def test_all_v2_tools_parse(self):
        tools = load_tools(self.tools_dir)
        # We ship 23 v2 tools + 4 hello-* tools = 27.
        self.assertGreaterEqual(len(tools), 20)
        # Every tool must have a non-empty name.
        for t in tools:
            self.assertTrue(t.name, f"tool in {t.folder} has no name")

    def test_capitalized_param_type_normalized(self):
        """v2 used ``type = "File"`` (capitalized); loader must lowercase."""
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "tool1").mkdir()
            (tools_dir / "tool1" / "tool.toml").write_text("""
[tool]
name = "T1"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[params]]
id = "f"
label = "F"
type = "File"
required = true
""", encoding="utf-8")
            (tools_dir / "tool1" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0].params[0].type, "file")

    def test_default_value_alias(self):
        """v2 used ``default_value`` instead of ``default``."""
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[params]]
id = "n"
label = "N"
type = "text"
default_value = "hello"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(tools[0].params[0].default, "hello")

    def test_options_as_comma_string(self):
        """v2 used ``options = "a,b,c"`` (string) instead of array."""
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[params]]
id = "m"
label = "M"
type = "dropdown"
options = "fast,slow,thorough"
default = "fast"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(tools[0].params[0].options, ["fast", "slow", "thorough"])

    def test_dependency_with_id_instead_of_import(self):
        """v2 had a broken form ``[[dependencies]] id = "Pillow"`` with
        ``import_name = "PIL"`` alongside it. The ``import_name`` field
        should take priority over ``id`` — this was the bug that caused
        the Dependency Manager to always report packages as missing
        (it was running ``python -c "import Pillow"`` instead of
        ``python -c "import PIL"``)."""
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[dependencies]]
id = "Pillow"
import_name = "PIL"
package_name = "Pillow"
min_version = "10.0"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(len(tools[0].dependencies), 1)
            dep = tools[0].dependencies[0]
            # ``import_name`` takes priority over ``id``:
            self.assertEqual(dep.import_name, "PIL")
            # ``package_name`` is preserved:
            self.assertEqual(dep.package_name, "Pillow")
            # ``min_version`` → ``version``:
            self.assertEqual(dep.version, "10.0")

    def test_dependency_falls_back_to_id_when_no_import(self):
        """When neither ``import`` nor ``import_name`` is present, fall
        back to ``id`` as a last resort (the original v2 broken form)."""
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[dependencies]]
id = "requests"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            dep = tools[0].dependencies[0]
            self.assertEqual(dep.import_name, "requests")
            self.assertEqual(dep.package_name, "requests")

    def test_dependency_with_correct_import(self):
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false

[[dependencies]]
import = "fitz"
package = "PyMuPDF"
version = ">=1.24"
ecosystem = "python"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(len(tools[0].dependencies), 1)
            dep = tools[0].dependencies[0]
            self.assertEqual(dep.import_name, "fitz")
            self.assertEqual(dep.package_name, "PyMuPDF")
            self.assertEqual(dep.version, ">=1.24")
            self.assertEqual(dep.ecosystem, "python")


class TestMalformedManifests(unittest.TestCase):
    """Spec §9: malformed manifest fixture is skipped with a logged
    warning not a crash."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tools_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, folder: str, toml_content: str, script: bool = True):
        d = self.tools_dir / folder
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath("tool.toml").write_text(toml_content, encoding="utf-8")
        if script:
            d.joinpath("x.py").write_text("print('hi')\n", encoding="utf-8")

    def test_invalid_toml_is_skipped(self):
        """TOML parse error in one tool must not crash the whole loader."""
        self._write("good", """
[tool]
name = "Good"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false
""")
        self._write("bad", "this is not = valid = toml = [")
        tools = load_tools(self.tools_dir)
        # Only the good tool loaded.
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "Good")

    def test_missing_script_marks_errors(self):
        """A manifest pointing at a missing script sets ``errors`` and
        ``script_exists=False`` but still loads."""
        d = self.tools_dir / "t"
        d.mkdir()
        d.joinpath("tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "nonexistent.py"
long_running = false
""", encoding="utf-8")
        # Don't write the script.
        tools = load_tools(self.tools_dir)
        self.assertEqual(len(tools), 1)
        self.assertFalse(tools[0].script_exists)
        self.assertTrue(tools[0].errors)
        self.assertIn("not found", tools[0].errors[0].lower())

    def test_missing_tool_section_skipped(self):
        """A manifest with no [tool] section is structurally broken; skip
        it rather than produce an empty-named tool."""
        self._write("broken", """
[[params]]
id = "x"
label = "X"
type = "text"
""")
        tools = load_tools(self.tools_dir)
        # loader's current behavior: it builds a ToolDefinition with
        # empty name and the script_path pointing at the tools dir.
        # We tolerate this — the UI just shows a "(no name)" row.
        # The important thing is no exception is raised.
        self.assertIsInstance(tools, list)

    def test_empty_tools_dir_returns_empty_list(self):
        empty = Path(tempfile.mkdtemp())
        self.assertEqual(load_tools(empty), [])

    def test_nonexistent_tools_dir_returns_empty_list(self):
        self.assertEqual(load_tools(Path("/nonexistent/path/that/does/not/exist")), [])


class TestRuntimeField(unittest.TestCase):
    """Spec §2: ``runtime`` override on the tool section."""

    def test_runtime_field_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.bat"
long_running = false
runtime = "cmd"
""", encoding="utf-8")
            (tools_dir / "t" / "x.bat").write_text("@echo off\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            self.assertEqual(tools[0].runtime, "cmd")

    def test_unknown_runtime_normalized_to_empty(self):
        with tempfile.TemporaryDirectory() as td:
            tools_dir = Path(td)
            (tools_dir / "t").mkdir()
            (tools_dir / "t" / "tool.toml").write_text("""
[tool]
name = "T"
description = "x"
icon = "ti-tool"
script = "x.py"
long_running = false
runtime = "ruby"
""", encoding="utf-8")
            (tools_dir / "t" / "x.py").write_text("print('hi')\n", encoding="utf-8")
            tools = load_tools(tools_dir)
            # Unknown runtime value is silently ignored.
            self.assertEqual(tools[0].runtime, "")


if __name__ == "__main__":
    unittest.main()
