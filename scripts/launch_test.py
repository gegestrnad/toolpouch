#!/usr/bin/env python3
"""Launch the App, run for ~3 seconds, then close. Verifies the UI
constructs without errors. Must be run under xvfb-run on headless boxes:
    xvfb-run -a python3 scripts/launch_test.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import customtkinter as ctk
        ctk.set_appearance_mode("dark")
        from ui.theme_manager import apply_theme
        apply_theme("Modern Dark")

        from ui.app import App
        import tempfile
        # Use a temp tools dir with no tools to keep test isolated.
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # Copy the bundled tools so the sidebar has something to show.
            import shutil
            src = ROOT / "tools"
            dest = td_path / "tools"
            shutil.copytree(src, dest)
            app = App(tools_dir=dest, exe_dir=ROOT)
            # Schedule a close after 2s.
            app.after(2000, app.destroy)
            app.mainloop()
            print("App launched and closed cleanly.")
            return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
