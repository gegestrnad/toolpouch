"""Sidebar — tool list, search, sort, favorites, theme picker.

Three sub-zones, top to bottom:
  1. Search box + sort dropdown + favorites filter toggle.
  2. Scrollable list of tool cards (one CTkButton per tool; favorite
     tools show a leading star marker).
  3. Action buttons: Add new tool, Import .toolpouch, Dependency Manager,
     About, theme picker.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.tool_importer import ToolImportError, import_tool_package
from ui.script_types import load_icon_image
from ui.theme_manager import THEMES

if TYPE_CHECKING:
    from ui.app import App


# Row color constants — used in both populate() and _refresh_selection_colors().
# Centralized so they can't drift out of sync.
_ROW_SELECTED_FG = ("gray70", "gray30")
_ROW_UNSELECTED_FG = ("gray85", "gray20")
_ROW_HOVER_FG = ("gray75", "gray25")


class Sidebar(ctk.CTkFrame):
    """Left column of the App. Owned by App; receives ``app`` so it can
    call ``app.reload()`` / ``app.show_tool(id)`` after structural
    changes."""

    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color=("gray90", "gray14"), corner_radius=0)
        self.app = app
        self._favorites_only = False
        self._search_term = ""
        self._sort_order = app.config.get("tool_sort_order", "Default")
        self._selected_category = "All"
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        # Header
        header = ctk.CTkLabel(
            self,
            text="Tool Pouch",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        sub = ctk.CTkLabel(self, text=f"{len(self.app.tools)} tools available", text_color="gray60")
        sub.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
        self._count_label = sub

        # Search
        self.search_var = ctk.StringVar(value="")
        self.search_var.trace_add("write", self._on_search_change)
        search = ctk.CTkEntry(
            self,
            textvariable=self.search_var,
            placeholder_text="Search tools...",
            height=32,
        )
        search.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="ew")

        # Sort + favorites + category row
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=3, column=0, padx=20, pady=(0, 8), sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.sort_var = ctk.StringVar(value=self._sort_order)
        sort_menu = ctk.CTkOptionMenu(
            row,
            values=["Default", "Name A-Z", "Name Z-A", "Recently Used"],
            variable=self.sort_var,
            command=self._on_sort_change,
            height=28,
        )
        sort_menu.grid(row=0, column=0, sticky="ew")

        self.fav_btn = ctk.CTkButton(
            row,
            text="★",
            width=32,
            height=28,
            fg_color="transparent",
            border_width=1,
            command=self._toggle_favorites,
        )
        self.fav_btn.grid(row=0, column=1, padx=(6, 0))

        # Category dropdown - populated after tools are loaded
        self.category_var = ctk.StringVar(value="All")
        self.category_menu = ctk.CTkOptionMenu(
            row,
            values=["All"],
            variable=self.category_var,
            command=self._on_category_change,
            height=28,
            width=140,
        )
        self.category_menu.grid(row=0, column=2, padx=(6, 0))

        # Scrollable tool list
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Action buttons at the bottom.
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=5, column=0, padx=10, pady=(0, 8), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(actions, text="+ Add new tool", height=30, command=self._on_add_tool).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(actions, text="Import .toolpouch...", height=30, command=self._on_import_tool).grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(actions, text="Dependency Manager", height=30, command=self._on_open_deps).grid(row=2, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(actions, text="About", height=30, command=self._on_about).grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # Theme picker
        theme_label = ctk.CTkLabel(self, text="Theme", text_color="gray60", font=ctk.CTkFont(size=12))
        theme_label.grid(row=6, column=0, padx=20, pady=(0, 2), sticky="w")
        self.theme_var = ctk.StringVar(value=self.app.current_theme)
        ctk.CTkOptionMenu(
            self,
            values=list(THEMES.keys()),
            variable=self.theme_var,
            command=self.app.switch_theme,
            height=28,
        ).grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

    # ------------------------------------------------------------------ populate
    def populate(self) -> None:
        """Re-render the tool list. Called on first build, after
        structural changes (add/import/delete/favorite toggle), and on
        search/sort changes. Selection-only changes do NOT call this —
        they call ``_refresh_selection_colors`` instead, which is ~30x
        faster because it doesn't destroy+rebuild the buttons.
        """
        # Clear existing
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._tool_buttons: dict[str, ctk.CTkButton] = {}
        # Hold references to PhotoImage objects so Tk doesn't GC them.
        # Without this, the icons would disappear after garbage collection.
        self._icon_images: dict[str, object] = {}

        # Compute filtered + sorted tool list.
        tools = self._filtered_sorted_tools()
        self._count_label.configure(text=f"{len(tools)} of {len(self.app.tools)} tools shown")

        if not tools:
            empty = ctk.CTkLabel(self.list_frame, text="(no tools match)", text_color="gray50")
            empty.grid(row=0, column=0, padx=10, pady=20)
            return

        favorites = set(self.app.config.get("favorite_tools", []))

        for i, tool in enumerate(tools):
            tool_id = tool.folder.name
            is_fav = tool_id in favorites
            star = "★ " if is_fav else "   "
            name_display = f"{star}{tool.name}"
            errors_marker = " ⚠" if tool.errors else ""
            is_selected = tool_id == self.app.current_tool_id

            # Each row is a frame containing an icon label + a text
            # button. The icon uses a PhotoImage loaded from
            # assets/lang_icons/. The button fills the rest of the row.
            row_frame = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", pady=1)
            row_frame.grid_columnconfigure(1, weight=1)

            # Language icon (16x16 PNG).
            icon_img = load_icon_image(tool.script_path, tool.runtime, size=16)
            if icon_img is not None:
                self._icon_images[tool_id] = icon_img  # prevent GC
                icon_label = ctk.CTkLabel(row_frame, image=icon_img, text="", width=20, height=20)
                icon_label.grid(row=0, column=0, padx=(4, 6), pady=0)
                # Clicking the icon should also select the tool.
                icon_label.bind("<Button-1>", lambda e, tid=tool_id: self._on_tool_click(tid))
                icon_label.bind("<Button-3>", lambda e, tid=tool_id: self._show_context_menu(e, tid))

            btn = ctk.CTkButton(
                row_frame,
                text=name_display + errors_marker,
                anchor="w",
                height=30,
                fg_color=_ROW_SELECTED_FG if is_selected else _ROW_UNSELECTED_FG,
                hover_color=_ROW_HOVER_FG,
                text_color=("black", "white"),
                command=lambda tid=tool_id: self._on_tool_click(tid),
            )
            btn.grid(row=0, column=1, sticky="ew")
            self._tool_buttons[tool_id] = btn
            # Right-click for context menu (export/favorite/delete).
            btn.bind("<Button-3>", lambda e, tid=tool_id: self._show_context_menu(e, tid))

    def _refresh_selection_colors(self) -> None:
        """Lightweight: just recolor the existing buttons to highlight
        the new selection. Called by ``select_by_id`` so clicks feel
        instant instead of rebuilding all ~30 buttons each time."""
        for tool_id, btn in getattr(self, "_tool_buttons", {}).items():
            is_selected = tool_id == self.app.current_tool_id
            try:
                btn.configure(
                    fg_color=_ROW_SELECTED_FG if is_selected else _ROW_UNSELECTED_FG
                )
            except Exception:
                pass

    def _filtered_sorted_tools(self) -> list:
        tools = list(self.app.tools)

        # Filter: search term (match name OR description).
        if self._search_term:
            term = self._search_term.lower()
            tools = [
                t for t in tools
                if term in t.name.lower() or term in t.description.lower()
            ]

        # Filter: favorites only.
        if self._favorites_only:
            favs = set(self.app.config.get("favorite_tools", []))
            tools = [t for t in tools if t.folder.name in favs]

        # Filter: category.
        if self._selected_category and self._selected_category != "All":
            tools = [t for t in tools if t.category == self._selected_category]

        # Sort.
        if self._sort_order == "Name A-Z":
            tools.sort(key=lambda t: t.name.lower())
        elif self._sort_order == "Name Z-A":
            tools.sort(key=lambda t: t.name.lower(), reverse=True)
        elif self._sort_order == "Recently Used":
            recents = self.app.config.get("recent_tools", [])
            rank = {tid: i for i, tid in enumerate(recents)}
            tools.sort(key=lambda t: rank.get(t.folder.name, 9999))
        # "Default" = folder order, already sorted by load_tools.

        return tools

    # ------------------------------------------------------------------ selection
    def select_by_id(self, tool_id: str) -> None:
        self.app.show_tool(tool_id)
        # Lightweight repaint — only recolor existing buttons, no rebuild.
        # This is the hot path: every click on a tool goes through here.
        # Rebuilding 27 buttons on every click was the main cause of the
        # "clunky and slow" feel reported by the user.
        self._refresh_selection_colors()

    def _on_tool_click(self, tool_id: str) -> None:
        self.select_by_id(tool_id)

    # ------------------------------------------------------------------ search / sort / favs
    def _on_search_change(self, *_args) -> None:
        self._search_term = self.search_var.get().strip()
        # Debounce: don't rebuild all 36 buttons on every keystroke.
        # Wait 150ms after the last keypress before filtering. This
        # makes typing in the search box feel instant even on slow
        # machines.
        if hasattr(self, "_search_after_id"):
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._search_after_id = self.after(150, self.populate)

    def _on_sort_change(self, value: str) -> None:
        self._sort_order = value
        self.app.config.set("tool_sort_order", value)
        self.app.config.save()
        self.populate()

    def _toggle_favorites(self) -> None:
        self._favorites_only = not self._favorites_only
        self.fav_btn.configure(fg_color=("#facc15" if self._favorites_only else "transparent"))
        self.populate()

    def _on_category_change(self, value: str) -> None:
        self._selected_category = value
        self.populate()

    def update_category_menu(self) -> None:
        """Update the category dropdown with all unique categories from loaded tools."""
        categories = sorted(set(t.category for t in self.app.tools if t.category))
        all_categories = ["All"] + categories
        self.category_menu.configure(values=all_categories)
        # Keep current selection if still valid, otherwise reset to "All"
        if self._selected_category not in all_categories:
            self._selected_category = "All"
            self.category_var.set("All")

    # ------------------------------------------------------------------ context menu
    def _show_context_menu(self, event, tool_id: str) -> None:
        """Right-click context menu using Tk's native ``Menu`` widget.

        Previous implementation used a ``CTkToplevel`` with
        ``overrideredirect(True)``, but that window lost focus
        immediately on creation (before the user could click any
        button), making export/delete silently fail. Tk's built-in
        ``Menu.tk_popup()`` handles focus, dismissal-on-click-away, and
        keyboard navigation correctly — it's the right tool for the job.
        """
        from tkinter import Menu

        tool = self.app.get_tool(tool_id)
        if tool is None:
            return
        is_fav = tool_id in self.app.config.get("favorite_tools", [])

        menu = Menu(self, tearoff=0)
        # Best-effort styling: native menus don't accept CTk colors,
        # but we can set foreground/background for a closer match.
        try:
            is_dark = ctk.get_appearance_mode() == "Dark"
            menu.configure(
                bg="#2a2a3c" if is_dark else "#ffffff",
                fg="#e5e7eb" if is_dark else "#1c1917",
                activebackground="#7c3aed",
                activeforeground="#ffffff",
                borderwidth=0,
            )
        except Exception:
            pass

        fav_label = "★ Remove from favorites" if is_fav else "☆ Add to favorites"
        menu.add_command(label=fav_label, command=lambda: self._toggle_fav_tool(tool_id))
        menu.add_separator()
        menu.add_command(label="Edit tool...", command=lambda: self._edit_tool(tool_id))
        menu.add_command(label="Export as .toolpouch...", command=lambda: self._export_tool(tool_id))
        menu.add_command(label="Delete tool...", command=lambda: self._delete_tool(tool_id))

        # tk_popup grabs input and auto-closes on click-away or Escape.
        menu.tk_popup(event.x_root, event.y_root)

    def _edit_tool(self, tool_id: str) -> None:
        """Open the wizard pre-filled with the tool's existing data.

        The wizard handles saving: on save, it reuses the same folder
        name (``edit_tool_id``) and overwrites the tool.toml + script.
        """
        from ui.wizard_dialog import WizardDialog
        WizardDialog(master=self, app=self.app, edit_tool_id=tool_id)

    def _toggle_fav_tool(self, tool_id: str) -> None:
        favs = self.app.config.get("favorite_tools", [])
        if tool_id in favs:
            favs = [f for f in favs if f != tool_id]
        else:
            favs = [tool_id] + favs
        self.app.config.set("favorite_tools", favs)
        self.app.config.save()
        self.populate()

    # ------------------------------------------------------------------ actions
    def _on_add_tool(self) -> None:
        from ui.wizard_dialog import WizardDialog
        WizardDialog(master=self, app=self.app)
        # When the wizard saves, it calls app.reload() itself.

    def _on_import_tool(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Import .toolpouch package",
            filetypes=[("Tool Pouch packages", "*.toolpouch"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            dest = import_tool_package(Path(path), self.app.tools_dir)
            # If this tool was previously deleted, un-record the deletion
            # so it doesn't get blocked on next seed.
            try:
                import main as main_mod
                main_mod.unrecord_tool_deletion(dest.name)
            except Exception:
                pass
            self.app.reload()
            self.select_by_id(dest.name)
        except ToolImportError as e:
            from tkinter import messagebox
            messagebox.showerror("Import failed", str(e))

    def _on_open_deps(self) -> None:
        from ui.dependency_manager import DependencyManagerWindow
        DependencyManagerWindow(master=self, app=self.app)

    def _on_about(self) -> None:
        from ui.about_page import AboutWindow
        AboutWindow(master=self, app=self.app)

    # ------------------------------------------------------------------ export / delete
    def _export_tool(self, tool_id: str) -> None:
        from tkinter import filedialog, messagebox
        tool = self.app.get_tool(tool_id)
        if tool is None:
            return
        default_name = f"{tool.folder.name}.toolpouch"
        path = filedialog.asksaveasfilename(
            title="Export tool",
            defaultextension=".toolpouch",
            initialfile=default_name,
            filetypes=[("Tool Pouch packages", "*.toolpouch")],
        )
        if not path:
            return
        from core.tool_importer import export_tool_package
        try:
            export_tool_package(tool.folder, Path(path))
            messagebox.showinfo("Exported", f"Tool exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _delete_tool(self, tool_id: str) -> None:
        from tkinter import messagebox
        tool = self.app.get_tool(tool_id)
        if tool is None:
            return
        if not messagebox.askyesno(
            "Delete tool",
            f"Delete tool '{tool.name}'?\nThis removes the folder:\n{tool.folder}\n\nThis cannot be undone.",
        ):
            return
        import shutil
        try:
            shutil.rmtree(tool.folder)
        except Exception as e:
            messagebox.showerror("Delete failed", str(e))
            return
        # Record the deletion so the tool doesn't get re-seeded from the
        # bundle on next launch. Without this, deleted tools reappear
        # after restart because seed_tools() re-copies them.
        try:
            import main as main_mod
            main_mod.record_tool_deletion(tool_id)
        except Exception:
            pass  # not critical — tool is already deleted from disk
        # Remove from favorites/recents so the sidebar doesn't ghost them.
        for key in ("favorite_tools", "recent_tools"):
            lst = self.app.config.get(key, [])
            lst = [t for t in lst if t != tool_id]
            self.app.config.set(key, lst)
        self.app.config.save()
        self.app.reload()
