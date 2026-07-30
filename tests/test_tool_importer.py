"""Unit tests for core/tool_importer.py.

Spec §9: "tool_importer.py (path-traversal guard). These three are where
a subtle bug either corrupts data or opens a security hole, not optional
polish."

Spec §5: "keep v2's exact path-traversal guard logic (this is a straight
port, don't weaken it)."

Covers:
- Path-traversal payloads (``../``, absolute paths) are rejected.
- Archives must contain exactly one root folder.
- Archives must contain a ``tool.toml``.
- ``tool.toml``'s ``script`` must point inside the tool folder.
- Round-trip: export → import → re-import with name collision.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tool_importer import (  # noqa: E402
    ToolImportError,
    export_tool_package,
    import_tool_package,
)


class TestImportSafety(unittest.TestCase):
    """Path-traversal / structural-safety guards."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tools_dir = Path(self.tmp.name) / "tools"
        self.tools_dir.mkdir()
        # Build a legit tool folder for round-trip tests.
        self.legit = self.tools_dir / "legit_tool"
        self.legit.mkdir()
        (self.legit / "tool.toml").write_text(
            '[tool]\nname="Legit"\ndescription="x"\nicon="ti-tool"\nscript="x.py"\nlong_running=false\n',
            encoding="utf-8",
        )
        (self.legit / "x.py").write_text("print('hi')\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _make_zip(self, name: str, members: dict[str, str]) -> Path:
        """Helper: build a zip with the given ``{arcname: content}``."""
        path = Path(self.tmp.name) / name
        with zipfile.ZipFile(path, "w") as zf:
            for arcname, content in members.items():
                zf.writestr(arcname, content)
        return path

    def test_path_traversal_rejected(self):
        """Archive with ``../escape.txt`` member must be rejected."""
        path = self._make_zip("bad.toolpouch", {
            "evil/../escape.txt": "boom",
            "evil/tool.toml": '[tool]\nname="E"\nscript="x.py"\n',
            "evil/x.py": "print('x')\n",
        })
        # Rename to .toolpouch — _make_zip uses .zip ext; we need .toolpouch
        target = path.with_suffix(".toolpouch")
        path.rename(target)
        with self.assertRaises(ToolImportError) as ctx:
            import_tool_package(target, self.tools_dir)
        self.assertIn("unsafe", str(ctx.exception).lower())

    def test_absolute_path_rejected(self):
        path = self._make_zip("bad2.toolpouch", {
            "/etc/passwd": "root:x:0:0",
            "evil/tool.toml": '[tool]\nname="E"\nscript="x.py"\n',
            "evil/x.py": "print('x')\n",
        })
        target = path.with_suffix(".toolpouch")
        path.rename(target)
        with self.assertRaises(ToolImportError):
            import_tool_package(target, self.tools_dir)

    def test_multi_root_rejected(self):
        """Archive with two top-level folders must be rejected."""
        path = self._make_zip("multi.toolpouch", {
            "tool1/tool.toml": '[tool]\nname="T1"\nscript="x.py"\n',
            "tool1/x.py": "print(1)\n",
            "tool2/tool.toml": '[tool]\nname="T2"\nscript="x.py"\n',
            "tool2/x.py": "print(2)\n",
        })
        target = path.with_suffix(".toolpouch")
        path.rename(target)
        with self.assertRaises(ToolImportError) as ctx:
            import_tool_package(target, self.tools_dir)
        self.assertIn("exactly one", str(ctx.exception).lower())

    def test_missing_tool_toml_rejected(self):
        path = self._make_zip("notoml.toolpouch", {
            "lonely/x.py": "print('hi')\n",
        })
        target = path.with_suffix(".toolpouch")
        path.rename(target)
        with self.assertRaises(ToolImportError):
            import_tool_package(target, self.tools_dir)

    def test_script_pointing_outside_rejected(self):
        """``tool.toml``'s ``script`` must resolve inside the tool folder.

        The validation does NOT depend on whether the escape target
        exists in the archive — it's a static path-containment check
        done after extraction. So we ship a single-root archive whose
        tool.toml points ``../`` (escape attempt); the importer must
        reject this BEFORE the missing-script check fires.
        """
        path = self._make_zip("escape.toolpouch", {
            "evil/tool.toml": '[tool]\nname="E"\ndescription="x"\nicon="ti-tool"\nscript="../evil2/x.py"\nlong_running=false\n',
            "evil/x.py": "print('x')\n",
        })
        target = path.with_suffix(".toolpouch")
        path.rename(target)
        with self.assertRaises(ToolImportError) as ctx:
            import_tool_package(target, self.tools_dir)
        self.assertIn("outside", str(ctx.exception).lower())

    def test_non_zip_rejected(self):
        """A file with .toolpouch extension but garbage content must fail cleanly."""
        path = Path(self.tmp.name) / "garbage.toolpouch"
        path.write_bytes(b"this is not a zip file")
        with self.assertRaises(ToolImportError) as ctx:
            import_tool_package(path, self.tools_dir)
        self.assertIn("not a valid", str(ctx.exception).lower())

    def test_wrong_extension_rejected(self):
        path = Path(self.tmp.name) / "bad.zip"
        path.write_bytes(b"")
        with self.assertRaises(ToolImportError) as ctx:
            import_tool_package(path, self.tools_dir)
        self.assertIn("extension", str(ctx.exception).lower())


class TestRoundTrip(unittest.TestCase):
    """Spec §5 Phase 5 checkpoint: create → export → delete → re-import."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tools_dir = Path(self.tmp.name) / "tools"
        self.tools_dir.mkdir()
        # Build a tool folder.
        self.tool = self.tools_dir / "my_tool"
        self.tool.mkdir()
        (self.tool / "tool.toml").write_text(
            '[tool]\nname="My Tool"\ndescription="x"\nicon="ti-tool"\nscript="x.py"\nlong_running=false\n\n'
            '[[params]]\nid="input"\nlabel="Input"\ntype="folder"\nrequired=true\n',
            encoding="utf-8",
        )
        (self.tool / "x.py").write_text("import argparse\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_then_import_round_trip(self):
        out = Path(self.tmp.name) / "exported.toolpouch"
        export_tool_package(self.tool, out)
        self.assertTrue(out.exists())

        # Delete original.
        import shutil
        shutil.rmtree(self.tool)
        self.assertFalse(self.tool.exists())

        # Re-import.
        imported = import_tool_package(out, self.tools_dir)
        self.assertTrue(imported.exists())
        self.assertEqual(imported.name, "my_tool")
        self.assertTrue((imported / "tool.toml").exists())
        self.assertTrue((imported / "x.py").exists())

    def test_import_with_name_collision_gets_numbered_suffix(self):
        """Spec §5: name collision gets a numbered suffix (_2, _3, ...)."""
        out = Path(self.tmp.name) / "exported.toolpouch"
        export_tool_package(self.tool, out)
        # Import while original still exists.
        imported = import_tool_package(out, self.tools_dir)
        self.assertEqual(imported.name, "my_tool_2")
        # Original is untouched.
        self.assertTrue(self.tool.exists())


if __name__ == "__main__":
    unittest.main()
