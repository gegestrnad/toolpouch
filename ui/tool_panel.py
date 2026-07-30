"""Tool panel — dynamic form + Run/Stop + progress + colored log console.

THREADING PATTERN (spec §5 — CRITICAL):

CustomTkinter (like all Tkinter) is NOT thread-safe for widget updates
from a background thread. The ``ToolRunner`` reads subprocess stdout on
a worker thread and fires callbacks. Those callbacks MUST NOT touch CTk
widgets directly — they only ``queue.put(...)`` items. The UI thread
polls the queue every 50ms via ``self.after(50, self._drain_queue)``
and applies the updates.

This is the single most common CustomTkinter bug class. DO NOT shortcut
it by calling ``self.log_text.insert(...)`` from the worker thread even
if "it works in testing" — it will randomly deadlock or corrupt widget
state in real use. Spec §5 footgun callout.
"""
from __future__ import annotations

import os
import queue
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from core.tool_runner import ToolRunner
from ui.script_types import script_badge, script_language_name

if TYPE_CHECKING:
    from ui.app import App


# Try to import tkinterdnd2 — optional. If missing, drag-and-drop is
# simply disabled; everything else works. The spec §5 calls for dnd2
# for folder/file fields, but it's not worth crashing the app over.
try:
    from tkinterdnd2 import DND_FILES  # type: ignore[import-not-found]
    _HAS_DND = True
except Exception:  # pragma: no cover
    _HAS_DND = False


class ToolPanel(ctk.CTkFrame):
    """Right column. Owns one ``ToolRunner`` instance and rebuilds its
    form whenever ``show_tool`` is called with a new tool."""

    def __init__(self, master, app: "App") -> None:
        super().__init__(master, fg_color=("gray96", "gray12"), corner_radius=0)
        self.app = app
        self.current_tool = None

        # The runner. Callbacks feed the queues below; the UI thread
        # drains them via .after().
        self.runner = ToolRunner(config=app.config)
        self.runner.on_log = self._on_log
        self.runner.on_progress = self._on_progress
        self.runner.on_status = self._on_status
        self.runner.on_finished = self._on_finished

        self._log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._progress_queue: queue.Queue[int] = queue.Queue()
        self._status_queue: queue.Queue[str] = queue.Queue()
        self._finished_queue: queue.Queue[bool] = queue.Queue()

        # Form field references, rebuilt per tool.
        self._fields: dict[str, _Field] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # the log console row grows

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        # Title row: [PY] Tool Name ............ (badge on the left)
        title_row = ctk.CTkFrame(self.header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(1, weight=1)

        # Script-type badge (e.g. "PY", "PS1", "BAT", "JS").
        # Color-coded by language; set in show_tool() per tool.
        self.badge_label = ctk.CTkLabel(
            title_row, text="",
            width=44, height=26,
            corner_radius=4,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ffffff",
            fg_color="#6b7280",
        )
        self.badge_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.title_label = ctk.CTkLabel(title_row, text="", font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.grid(row=0, column=1, sticky="w")

        self.desc_label = ctk.CTkLabel(self.header, text="", text_color="gray60", wraplength=700, anchor="w", justify="left")
        self.desc_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Form + Run row
        self.form_host = ctk.CTkFrame(self, fg_color="transparent")
        self.form_host.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="ew")
        self.form_host.grid_columnconfigure(1, weight=1)

        # Log console + progress
        self.log_host = ctk.CTkFrame(self, fg_color="transparent")
        self.log_host.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="nsew")
        self.log_host.grid_columnconfigure(0, weight=1)
        self.log_host.grid_rowconfigure(2, weight=1)

        # Progress bar + status + Run/Stop button row.
        ctrl_row = ctk.CTkFrame(self.log_host, fg_color="transparent")
        ctrl_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctrl_row.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(ctrl_row, height=14)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(ctrl_row, text="idle", width=80, text_color="gray60")
        self.status_label.grid(row=0, column=1, padx=(0, 8))

        self.run_btn = ctk.CTkButton(ctrl_row, text="Run", width=80, command=self._on_run, fg_color="#16a34a", hover_color="#15803d")
        self.run_btn.grid(row=0, column=2, padx=(0, 4))
        self.stop_btn = ctk.CTkButton(ctrl_row, text="Stop", width=80, command=self._on_stop, fg_color="#dc2626", hover_color="#b91c1c", state="disabled")
        self.stop_btn.grid(row=0, column=3)

        # Clear log button row.
        log_header = ctk.CTkFrame(self.log_host, fg_color="transparent")
        log_header.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        log_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_header, text="Output", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_header, text="Copy", width=55, height=22, command=self._copy_log, fg_color="transparent", border_width=1).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkButton(log_header, text="Save...", width=65, height=22, command=self._save_log, fg_color="transparent", border_width=1).grid(row=0, column=2, padx=(0, 4))
        ctk.CTkButton(log_header, text="Clear", width=55, height=22, command=self._clear_log, fg_color="transparent", border_width=1).grid(row=0, column=3)

        self.log_text = ctk.CTkTextbox(self.log_host, wrap="word", font=ctk.CTkFont(family="Consolas" if os.name == "nt" else "Monospace", size=12))
        self.log_text.grid(row=2, column=0, sticky="nsew")
        # Per-tag foreground colors. Set here AND refreshed in
        # ``apply_theme_colors`` so theme switches recolor them.
        self._configure_log_tags()
        self.log_text.configure(state="disabled")
        # Ctrl+A selects all log text (disabled widgets don't always honor this).
        self.log_text.bind("<Control-a>", lambda e: (self.log_text.tag_add("sel", "1.0", "end-1c"), "break"))

        # Start the UI-thread polling loop.
        self._drain_loop()
        # Separate scroll-refresh loop: instead of calling ``see("end")``
        # on every single log line (which forces a Tk re-layout each
        # time), we accumulate "needs scroll" and flush it every 100ms.
        # This is the main perf win for high-volume output.
        self._scroll_dirty = False
        self._scroll_loop()

    # ------------------------------------------------------------------ log tags
    def _configure_log_tags(self) -> None:
        # Color values chosen for legibility on BOTH dark and light
        # themes — these are fixed (not theme-driven) because they
        # encode semantic meaning (success/warn/error), not styling.
        # CTkTextbox exposes the underlying tk.Text widget via ._textbox.
        try:
            t = self.log_text._textbox  # type: ignore[attr-defined]
            t.tag_config("ok", foreground="#22c55e")
            t.tag_config("warn", foreground="#eab308")
            t.tag_config("error", foreground="#ef4444")
            t.tag_config("info", foreground="#a1a1aa")
        except Exception:
            pass

    # ------------------------------------------------------------------ show tool / placeholder
    def show_placeholder(self) -> None:
        self.current_tool = None
        # Clear form
        for child in self.form_host.winfo_children():
            child.destroy()
        self._fields = {}
        self.title_label.configure(text="Select a tool")
        self.badge_label.configure(text="", fg_color="transparent")
        self.desc_label.configure(text="Pick a tool from the sidebar to get started.")
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="idle")

    def show_tool(self, tool) -> None:
        self.current_tool = tool
        # Clear + rebuild form
        for child in self.form_host.winfo_children():
            child.destroy()
        self._fields = {}

        self.title_label.configure(text=tool.name)
        # Set the script-type badge (e.g. "PY" on blue, "JS" on yellow).
        label, color = script_badge(tool.script_path, tool.runtime)
        lang_name = script_language_name(tool.script_path, tool.runtime)
        self.badge_label.configure(text=label, fg_color=color)

        desc = tool.description
        # Append the full language name + script filename to the desc so
        # the user has full context at a glance.
        script_name = tool.script_path.name if tool.script_path else "(no script)"
        runtime_note = f"  ·  {lang_name}  ·  {script_name}"
        if tool.runtime:
            runtime_note += f"  ·  runtime override: {tool.runtime}"
        if tool.errors:
            desc += "\n⚠ " + " | ".join(tool.errors)
        self.desc_label.configure(text=desc + runtime_note)

        if not tool.script_exists:
            self.run_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            return

        # Build one row per param.
        for i, param in enumerate(tool.params):
            field = _build_field(self.form_host, param)
            field.grid(row=i, column=0, columnspan=2, padx=0, pady=4, sticky="ew")
            self._fields[param.id] = field

        # Always at least one row so the layout doesn't collapse.
        if not tool.params:
            ctk.CTkLabel(self.form_host, text="This tool takes no parameters.", text_color="gray60").grid(row=0, column=0, columnspan=2, padx=0, pady=8, sticky="w")

        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="idle")

    # ------------------------------------------------------------------ run / stop
    def _on_run(self) -> None:
        if self.current_tool is None:
            return
        if self.runner.is_running():
            return

        # Build args. Skip empty optional params entirely (don't pass
        # ``--id ""``).
        args: list[str] = []
        for pid, field in self._fields.items():
            value = field.get_value().strip()
            if not value:
                if field.param.required:
                    self._append_log_line(f"[ERROR] Required parameter missing: {field.param.label}", "error")
                    return
                continue
            # Multi-value fields (files/folders) split on newline →
            # multiple --id value pairs. argparse with nargs='+' or
            # action='append' will see them all.
            if field.param.type in ("files", "folders"):
                for piece in value.split("\n"):
                    piece = piece.strip()
                    if piece:
                        args.append(f"--{pid}")
                        args.append(piece)
            else:
                args.append(f"--{pid}")
                args.append(value)

        # Clear log for the new run (matches v2 behavior).
        self._clear_log()
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="starting...")

        tool_name = self.current_tool.name
        self.runner.run(self.current_tool, args, tool_name=tool_name)
        # Add to recents immediately so "Recently Used" sort updates.
        self.app.config.add_recent_tool(self.current_tool.folder.name)

    def _on_stop(self) -> None:
        self.runner.stop()
        self.stop_btn.configure(state="disabled")
        self.run_btn.configure(state="normal")
        self.status_label.configure(text="stopping...")

    def stop_if_running(self) -> None:
        if self.runner.is_running():
            self.runner.stop()

    def is_running(self) -> bool:
        """True if a tool subprocess is currently running. Used by
        App.switch_theme to refuse theme changes mid-run."""
        return self.runner.is_running()

    # ------------------------------------------------------------------ callbacks (worker thread!)
    # These run on the ToolRunner's reader thread. They MUST be fast and
    # MUST NOT touch CTk widgets. They only put items on queues.
    def _on_log(self, line: str, level: str) -> None:
        self._log_queue.put((line, level))

    def _on_progress(self, pct: int) -> None:
        self._progress_queue.put(pct)

    def _on_status(self, status: str) -> None:
        self._status_queue.put(status)

    def _on_finished(self, success: bool) -> None:
        self._finished_queue.put(success)

    # ------------------------------------------------------------------ UI thread drain
    def _update_run_button(self) -> None:
        """Enable/disable the Run button based on current state.
        Extracted to avoid repeating this expression 4× in _drain_loop."""
        can_run = bool(self.current_tool and self.current_tool.script_exists) and not self.runner.is_running()
        self.run_btn.configure(state="normal" if can_run else "disabled")

    def _drain_loop(self) -> None:
        """Polls all four queues every 50ms and applies updates to
        widgets. Runs on the UI thread."""
        # Guard: stop the loop if the panel was destroyed (e.g. during
        # theme switch). Without this, the loop keeps running forever
        # silently failing on destroyed widgets.
        if not self.winfo_exists():
            return
        # Drain log (cap per-tick to avoid UI freeze on huge bursts).
        # Batch all lines into ONE textbox state toggle + insert + state
        # toggle — this is ~4× faster than toggling per line.
        n_logged = 0
        batch: list[tuple[str, str]] = []
        while n_logged < 500:
            try:
                line, level = self._log_queue.get_nowait()
            except queue.Empty:
                break
            batch.append((line, level))
            n_logged += 1
        if batch:
            self._append_log_batch(batch)

        # Drain progress (last value wins).
        while True:
            try:
                pct = self._progress_queue.get_nowait()
            except queue.Empty:
                break
            self.progress_bar.set(pct / 100.0)

        # Drain status (last value wins).
        while True:
            try:
                status = self._status_queue.get_nowait()
            except queue.Empty:
                break
            self.status_label.configure(text=status)
            if status == "running":
                self.run_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
            elif status in ("idle", "done", "error"):
                self.stop_btn.configure(state="disabled")
                self._update_run_button()

        # Drain finished (only one expected per run).
        while True:
            try:
                success = self._finished_queue.get_nowait()
            except queue.Empty:
                break
            self._update_run_button()
            self.stop_btn.configure(state="disabled")
            if success:
                self._append_log_line("[OK] Tool finished successfully.", "ok")
            else:
                self._append_log_line("[ERROR] Tool finished with errors (non-zero exit).", "error")

        self.after(50, self._drain_loop)

    def _scroll_loop(self) -> None:
        """Separate loop that scrolls the log to bottom every 100ms IF
        new content was added. Avoids forcing a Tk re-layout on every
        single ``insert`` call, which was the main perf bottleneck for
        high-volume output."""
        if not self.winfo_exists():
            return
        if self._scroll_dirty:
            try:
                self.log_text.see("end")
            except Exception:
                pass
            self._scroll_dirty = False
        self.after(100, self._scroll_loop)

    # ------------------------------------------------------------------ log widget
    def _append_log_line(self, line: str, level: str) -> None:
        """Single-line append. For batch appends (multiple lines at once),
        prefer ``_append_log_batch`` — it toggles the textbox state only
        once instead of once per line."""
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n", level)
            # Cap buffer at ~5000 lines to avoid unbounded memory growth
            # on long-running tools that spam output.
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 5000:
                self.log_text.delete("1.0", f"{line_count - 5000}.0")
            self.log_text.configure(state="disabled")
            # Don't call see("end") here — set the dirty flag and let
            # _scroll_loop handle it on its own 100ms cadence.
            self._scroll_dirty = True
        except Exception:
            pass

    def _append_log_batch(self, batch: list[tuple[str, str]]) -> None:
        """Append multiple lines in one textbox-state-toggle cycle.

        This is the main perf path for the drain loop — instead of
        calling ``configure(state="normal")`` + ``insert`` +
        ``configure(state="disabled")`` for every single line (3 widget
        calls × N lines), we toggle once, insert all N lines, toggle
        once. For a 500-line burst this drops from ~1500 widget calls
        to ~502.
        """
        if not batch:
            return
        try:
            self.log_text.configure(state="normal")
            for line, level in batch:
                self.log_text.insert("end", line + "\n", level)
            # Cap buffer at ~5000 lines. Only trim once per batch, not
            # once per line.
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 5000:
                self.log_text.delete("1.0", f"{line_count - 5000}.0")
            self.log_text.configure(state="disabled")
            self._scroll_dirty = True
        except Exception:
            pass

    def _clear_log(self) -> None:
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

    def _copy_log(self) -> None:
        """Copy the entire log to the system clipboard."""
        try:
            text = self.log_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass

    def _save_log(self) -> None:
        """Save the log to a file chosen by the user."""
        from tkinter import filedialog
        try:
            path = filedialog.asksaveasfilename(
                title="Save log",
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            )
            if path:
                text = self.log_text.get("1.0", "end-1c")
                Path(path).write_text(text, encoding="utf-8")
                self._append_log_line(f"[OK] Log saved to: {path}", "ok")
        except Exception as e:
            self._append_log_line(f"[ERROR] Failed to save log: {e}", "error")


# =========================================================================== field
class _Field(ctk.CTkFrame):
    """One form row. Holds a label, the input widget(s), and knows how
    to retrieve the current value as a string for argv building."""

    def __init__(self, master, param) -> None:
        super().__init__(master, fg_color="transparent")
        self.param = param
        self.grid_columnconfigure(1, weight=1)

        # Label
        label_text = param.label + (" *" if param.required else "")
        ctk.CTkLabel(self, text=label_text, width=160, anchor="w").grid(row=0, column=0, padx=(0, 8), sticky="w")

        # Value widget per type
        if param.type == "dropdown":
            options = param.options or ["(no options)"]
            self.entry = ctk.CTkOptionMenu(self, values=options, height=30)
            if param.default and param.default in options:
                self.entry.set(param.default)
            else:
                self.entry.set(options[0])
            self.entry.grid(row=0, column=1, sticky="ew")
        else:
            self.entry = ctk.CTkEntry(self, placeholder_text=param.placeholder or "", height=30)
            if param.default:
                self.entry.insert(0, param.default)
            self.entry.grid(row=0, column=1, sticky="ew")

            # Browse button for file/folder/save/files/folders
            if param.type in ("folder", "folders", "file", "files", "save"):
                browse_btn = ctk.CTkButton(self, text="Browse...", width=90, height=30, command=self._on_browse)
                browse_btn.grid(row=0, column=2, padx=(6, 0))
                # Drag-and-drop onto the entry (if tkinterdnd2 available).
                # IMPORTANT: DnD must be registered on the underlying
                # ``tkinter.Entry`` (``CTkEntry._entry``), NOT on the
                # CTkEntry wrapper itself — CTk widgets aren't real Tk
                # widgets and don't accept DnD registration directly.
                # The DnD-enabled root (see ui/app.py) must already be
                # initialized for this to work; if it isn't, the
                # ``drop_target_register`` call raises and we silently
                # skip DnD for this field.
                if _HAS_DND:
                    try:
                        target = getattr(self.entry, "_entry", self.entry)
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self._on_drop)
                    except Exception:
                        pass

    # ------------------------------------------------------------------ value
    def get_value(self) -> str:
        if self.param.type == "dropdown":
            return self.entry.get()
        return self.entry.get()

    # ------------------------------------------------------------------ browse
    def _on_browse(self) -> None:
        t = self.param.type
        if t == "folder":
            path = filedialog.askdirectory(title=self.param.label, mustexist=True)
            if path:
                self.entry.delete(0, "end")
                self.entry.insert(0, path)
        elif t == "folders":
            # Tk's askdirectory doesn't support multi-select natively;
            # open successive dialogs until user cancels.
            paths: list[str] = []
            while True:
                path = filedialog.askdirectory(title=f"{self.param.label} ({len(paths)+1} selected, Cancel to finish)", mustexist=True)
                if not path:
                    break
                paths.append(path)
            if paths:
                self.entry.delete(0, "end")
                self.entry.insert(0, "\n".join(paths))
        elif t == "file":
            path = filedialog.askopenfilename(title=self.param.label, filetypes=[("All files", "*.*")])
            if path:
                self.entry.delete(0, "end")
                self.entry.insert(0, path)
        elif t == "files":
            paths = filedialog.askopenfilenames(title=self.param.label, filetypes=[("All files", "*.*")])
            if paths:
                self.entry.delete(0, "end")
                self.entry.insert(0, "\n".join(paths))
        elif t == "save":
            path = filedialog.asksaveasfilename(title=self.param.label, defaultextension="", filetypes=[("All files", "*.*")])
            if path:
                self.entry.delete(0, "end")
                self.entry.insert(0, path)

    def _on_drop(self, event) -> None:
        # DnD gives us paths in Tcl-list form: {C:\path with space\a.txt} {C:\b.txt}
        # ``_split_drop`` parses that into a Python list.
        paths = _split_drop(event.data)
        if not paths:
            return
        if self.param.type in ("files", "folders") and len(paths) > 1:
            self.entry.delete(0, "end")
            self.entry.insert(0, "\n".join(paths))
        else:
            self.entry.delete(0, "end")
            self.entry.insert(0, paths[0])


def _build_field(master, param) -> _Field:
    return _Field(master, param)


def _split_drop(data: str) -> list[str]:
    """Parse a Tk DnD drop payload into a list of filesystem paths.

    DnD paths come in Tcl-list syntax with paths potentially wrapped in
    extra braces if they contain spaces. This helper handles the common
    cases. (For exotic cases the user can paste manually into the entry.)
    """
    if not data:
        return []
    # Windows uses {C:\path\file.txt} for paths with spaces; POSIX uses
    # plain strings. Tcl's list parser handles both uniformly.
    try:
        import tkinter
        parts = tkinter.tk.splitlist(data)  # type: ignore[attr-defined]
        return [str(p).strip("{}") for p in parts if p]
    except Exception:
        # Last-resort fallback: split on whitespace.
        return [p.strip().strip("{}") for p in data.split() if p]
