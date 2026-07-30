#!/usr/bin/env python3
"""Smoke test: import everything and try to construct the App without
showing it. Catches import errors, missing files, theme JSON parse
errors, etc. without needing a display.

Run with:
    python3 /home/z/my-project/toolpouch-v3/scripts/smoke_test.py
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# Make sure project root is on path.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"  [OK] {name}")
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()
        return False


def t_imports():
    import core  # noqa: F401
    import core.config  # noqa: F401
    import core.tool_loader  # noqa: F401
    import core.tool_runner  # noqa: F401
    import core.tool_importer  # noqa: F401
    import core.dependency_checker  # noqa: F401
    import core.wizard  # noqa: F401
    import core.runtime_resolver  # noqa: F401
    import deps  # noqa: F401
    import deps.python_provider  # noqa: F401
    import deps.node_provider  # noqa: F401
    import deps.powershell_provider  # noqa: F401
    import deps.none_provider  # noqa: F401
    import ui.theme_manager  # noqa: F401
    import ui.app  # noqa: F401
    import ui.sidebar  # noqa: F401
    import ui.tool_panel  # noqa: F401
    import ui.wizard_dialog  # noqa: F401
    import ui.dependency_manager  # noqa: F401
    import ui.about_page  # noqa: F401


def t_themes_parse():
    from ui.theme_manager import THEMES, theme_path
    for name in THEMES:
        p = theme_path(name)
        assert p is not None, f"theme {name} has no path"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "CTk" in data, f"theme {name} missing CTk key"
        assert "CTkButton" in data, f"theme {name} missing CTkButton"
        assert "CTkTextbox" in data, f"theme {name} missing CTkTextbox"


def t_tool_loader():
    from core.tool_loader import load_tools
    tools = load_tools(ROOT / "tools")
    assert len(tools) >= 20, f"expected ≥20 tools, got {len(tools)}"
    # Every tool must have a name
    for t in tools:
        assert t.name, f"tool in {t.folder} has no name"
        assert t.script_path, f"tool {t.name} has no script_path"


def t_runtime_resolver_python():
    """The .py case should resolve to a system Python on this Linux box."""
    from core.runtime_resolver import RuntimeResolver, LaunchSpec
    from core.tool_loader import load_tools
    tools = load_tools(ROOT / "tools")
    py_tool = next(t for t in tools if t.script_path.suffix == ".py")
    r = RuntimeResolver()
    spec = r.resolve(py_tool)
    assert isinstance(spec, LaunchSpec)
    assert spec.executable, "no executable resolved"
    assert spec.ecosystem == "python"


def t_runtime_resolver_unknown_ext():
    """Unknown extension should raise RuntimeResolutionError."""
    from core.runtime_resolver import RuntimeResolver, RuntimeResolutionError
    from dataclasses import dataclass
    from pathlib import Path

    @dataclass
    class FakeTool:
        script_path: Path
        runtime: str = ""
        folder: Path = Path(".")

    r = RuntimeResolver()
    try:
        r.resolve(FakeTool(script_path=Path("foo.unknownext")))
        raise AssertionError("expected RuntimeResolutionError")
    except RuntimeResolutionError:
        pass  # expected


def t_wizard_round_trip():
    """generate_toml → write_tool → load_tools → parse."""
    import tempfile
    from core.wizard import generate_toml, write_tool
    from core.tool_loader import load_tools

    toml = generate_toml(
        name="Test Tool",
        description="A test tool",
        icon="ti-tool",
        script_filename="test.py",
        long_running=False,
        params=[
            {"id": "input", "label": "Input", "type": "folder", "required": True, "placeholder": "Pick a folder"},
            {"id": "mode", "label": "Mode", "type": "dropdown", "options": ["a", "b"], "default": "a", "required": True},
        ],
        runtime="python",
    )
    with tempfile.TemporaryDirectory() as td:
        tools_dir = Path(td) / "tools"
        # Create a fake script file
        script = Path(td) / "test.py"
        script.write_text("print('hello')\n", encoding="utf-8")
        write_tool(tools_dir, "test_tool", toml, script_source=script)
        tools = load_tools(tools_dir)
        assert len(tools) == 1
        t = tools[0]
        assert t.name == "Test Tool"
        assert t.runtime == "python"
        assert len(t.params) == 2
        assert t.params[0].id == "input"
        assert t.params[0].type == "folder"
        assert t.params[1].type == "dropdown"
        assert t.params[1].options == ["a", "b"]
        assert t.params[1].default == "a"


def main() -> int:
    checks = [
        ("imports", t_imports),
        ("themes parse", t_themes_parse),
        ("tool_loader parses all tools", t_tool_loader),
        ("runtime_resolver .py case", t_runtime_resolver_python),
        ("runtime_resolver unknown ext raises", t_runtime_resolver_unknown_ext),
        ("wizard round-trip", t_wizard_round_trip),
    ]
    print("Running smoke tests...")
    all_ok = True
    for name, fn in checks:
        if not check(name, fn):
            all_ok = False
    print()
    if all_ok:
        print("All smoke tests passed.")
        return 0
    else:
        print("SOME SMOKE TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
