"""Root application window.

Three-zone layout matching v2 (sidebar / panel header / panel body) —
spec §5 explicitly says: "this is a UI framework port, not a UX
redesign, keep the layout the user already knows."

Window state persistence (Phase 9): geometry saved as ``"WxH+X+Y"``
string in config.json on close, restored on launch.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from core.config import ConfigManager
from core.tool_loader import load_tools
from ui.sidebar import Sidebar
from ui.tool_panel import ToolPanel
from ui.theme_manager import apply_theme, THEMES


# ---------------------------------------------------------------------------
# DnD-enabled CTk root.
#
# CustomTkinter's plain ``CTk()`` does NOT initialize tkinterdnd2, so
# ``drop_target_register`` calls on child widgets silently fail. The fix
# is to mix in ``TkinterDnD.DnDWrapper`` and call ``TkinterDnD._require(self)``
# in ``__init__`` — this loads the tkdnd Tcl extension into the root
# interpreter, which makes DnD work on all descendants.
#
# If tkinterdnd2 is missing (the import guard in tool_panel.py already
# handles that), we fall back to plain ``ctk.CTk`` so the app still
# launches — DnD is just disabled.
# ---------------------------------------------------------------------------
try:
    from tkinterdnd2 import TkinterDnD  # type: ignore[import-not-found]

    class _DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    _ROOT_BASE = _DnDCTk
except Exception:  # pragma: no cover
    _ROOT_BASE = ctk.CTk


class App(_ROOT_BASE):
    """Root window. Owns the ConfigManager, the loaded tool list, and
    the sidebar/panel children. Knows which tool is currently selected
    so the sidebar and panel stay in sync."""

    def __init__(self, tools_dir: Path, exe_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.tools_dir = Path(tools_dir)
        self.exe_dir = Path(exe_dir) if exe_dir else self.tools_dir.parent
        self.config = ConfigManager()

        # Apply persisted theme BEFORE building widgets so the first paint
        # already uses the right palette.
        self.current_theme = apply_theme(self.config.get("theme", "Modern Dark"))
        self.config.set("theme", self.current_theme)

        # Window chrome.
        self.title("Tool Pouch")
        self._restore_geometry()
        # Icon is set by main.py's _set_window_icon() after App is
        # constructed — it uses find_icon() which checks the user data
        # dir, the PyInstaller bundle, and the install dir. We don't
        # set it here to avoid duplicating the search logic.

        # Min size so the layout doesn't collapse on small windows.
        self.minsize(900, 600)

        # Load tools (refreshable via sidebar "Refresh" button).
        self.tools: list = []
        self._reload_tools()

        # Currently-selected tool folder name (not the ToolDefinition
        # itself — we look it up by id on demand so a reload doesn't
        # leave us holding a stale reference).
        self.current_tool_id: Optional[str] = self.config.get("last_tool")

        # Layout: 280px sidebar + flex panel.
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = Sidebar(master=self, app=self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 0), pady=0)

        self.panel = ToolPanel(master=self, app=self)
        self.panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # Initial selection.
        self.sidebar.populate()
        if self.current_tool_id:
            self.sidebar.select_by_id(self.current_tool_id)
        else:
            self.show_placeholder()

        # Persist window state on close.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Keyboard shortcuts (global bindings).
        self.bind_all("<Control-f>", lambda e: self.sidebar.search.focus_set())
        self.bind_all("<Control-F>", lambda e: self.sidebar.search.focus_set())
        self.bind_all("<Escape>", self._on_escape)
        # Enter to run the currently-selected tool when focus is in the form area.
        self.bind_all("<Return>", self._on_enter)

    def _on_escape(self, event) -> None:
        """Escape: stop running tool, or clear search, or defocus."""
        if self.panel.is_running():
            self.panel._on_stop()
        elif self.sidebar.search_var.get():
            self.sidebar.search_var.set("")
            self.sidebar._on_search_change()
        else:
            self.focus_set()

    def _on_enter(self, event) -> None:
        """Enter: run the current tool (if not running and not in an entry)."""
        # Don't hijack Enter when the user is typing in an entry/option menu.
        widget = event.widget
        if widget is None:
            return
        widget_class = widget.winfo_class()
        if widget_class in ("Entry", "TMenubutton", "TCombobox"):
            return  # let the entry handle it
        if self.panel.current_tool and not self.panel.is_running():
            self.panel._on_run()

    # ------------------------------------------------------------------ tools
    def _reload_tools(self) -> None:
        self.tools = load_tools(self.tools_dir)

    def reload(self) -> None:
        """Public reload — called by Sidebar after add/import/delete."""
        self._reload_tools()
        self.sidebar.populate()
        # If the currently-selected tool disappeared, clear the panel.
        if self.current_tool_id and not any(
            t.folder.name == self.current_tool_id for t in self.tools
        ):
            self.current_tool_id = None
            self.show_placeholder()
        elif self.current_tool_id:
            self.show_tool(self.current_tool_id)

    def get_tool(self, tool_id: str):
        for t in self.tools:
            if t.folder.name == tool_id:
                return t
        return None

    # ------------------------------------------------------------------ selection
    def show_tool(self, tool_id: str) -> None:
        tool = self.get_tool(tool_id)
        if tool is None:
            self.show_placeholder()
            return
        self.current_tool_id = tool_id
        self.config.set("last_tool", tool_id)
        self.config.save()
        self.panel.show_tool(tool)

    def show_placeholder(self) -> None:
        self.current_tool_id = None
        self.panel.show_placeholder()

    # ------------------------------------------------------------------ theme
    def switch_theme(self, display_name: str) -> None:
        """Apply a new theme at runtime.

        CustomTkinter's ``set_default_color_theme`` only affects widgets
        created AFTER the call — existing widgets keep their old colors.
        The only reliable way to recolor an already-built CTk app is to
        destroy and rebuild the children. We save the current selection
        so we can restore it after the rebuild.
        """
        if self.panel.is_running():
            # Refuse to rebuild while a tool is running — destroying the
            # panel mid-run would kill the runner's callback targets.
            from tkinter import messagebox
            messagebox.showwarning(
                "Tool running",
                "Stop the running tool before switching themes.",
            )
            # Revert the dropdown to the actual current theme.
            self.sidebar.theme_var.set(self.current_theme)
            return

        saved_tool_id = self.current_tool_id

        self.current_theme = apply_theme(display_name)
        self.config.set("theme", self.current_theme)
        self.config.save()

        # Tear down + rebuild. The grid_columnconfigure/rowconfigure on
        # self (the root) are preserved across child destruction.
        self.sidebar.destroy()
        self.panel.destroy()
        self.sidebar = Sidebar(master=self, app=self)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.panel = ToolPanel(master=self, app=self)
        self.panel.grid(row=0, column=1, sticky="nsew")

        self.sidebar.populate()
        if saved_tool_id and self.get_tool(saved_tool_id):
            self.sidebar.select_by_id(saved_tool_id)
        else:
            self.show_placeholder()

    # ------------------------------------------------------------------ window state
    def _restore_geometry(self) -> None:
        geom = self.config.get("window.geometry")
        if isinstance(geom, str) and geom:
            try:
                # Validate the format roughly before applying — a bad
                # geometry string would crash Tk.
                if "+" in geom and "x" in geom:
                    self.geometry(geom)
                    return
            except Exception:
                pass
        # Default: 1200x780, centered by Tk.
        self.geometry("1200x780")

    def _save_geometry(self) -> None:
        try:
            geom = self.geometry()  # e.g. "1200x780+100+50"
            self.config.set("window.geometry", geom)
            self.config.save()
        except Exception:
            pass

    def _on_close(self) -> None:
        # Stop any running tool before exiting so we don't leak a child
        # process holding a console window open.
        try:
            self.panel.stop_if_running()
        except Exception:
            pass
        self._save_geometry()
        self.destroy()
