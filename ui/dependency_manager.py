"""Dependency Manager window (CTkToplevel, modal).

Multi-ecosystem table — one row per (tool, dependency) pair — with an
**Ecosystem** column alongside Tool / Import / Package / Status / Version
/ Notes (spec §6).

- "Re-scan" button rebuilds the table (runs in a worker thread so the
  UI doesn't freeze — scanning 36 tools with subprocess-per-dep takes
  50-200s synchronously).
- "Install all missing" button installs every missing dependency.
- "Install selected" button installs only the checkbox-selected rows.
"""
from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from core.dependency_checker import clear_module_cache
from deps import scan_all, install_for_ecosystem

if TYPE_CHECKING:
    from ui.app import App


class DependencyManagerWindow(ctk.CTkToplevel):
    """Modal window showing all tool dependencies across all ecosystems."""

    def __init__(self, master, app: "App") -> None:
        super().__init__(master)
        self.app = app
        self.transient(master)
        self.grab_set()

        self.title("Dependency Manager")
        self.geometry("1200x620")
        self.minsize(1000, 520)

        # Set our custom icon BEFORE CTk's 200ms timer overrides it.
        from ui.window_icon import set_window_icon
        set_window_icon(self)

        # Worker-thread plumbing. Three queues:
        # - _log_queue: install log lines (from install worker)
        # - _install_done_queue: (n_installed, n_attempted) when install finishes
        # - _rescan_done_queue: list[dict] rows when scan finishes
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._install_done_queue: queue.Queue[tuple[int, int]] = queue.Queue()
        self._rescan_done_queue: queue.Queue[list[dict]] = queue.Queue()

        # Per-row checkbox variables. Keyed by row index in _last_rows.
        self._row_vars: dict[int, ctk.BooleanVar] = {}

        self._build()
        self._start_rescan()

        self._drain_loop()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(12, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Dependencies", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Multi-ecosystem: Python (pip), Node (npm), PowerShell (Install-Module). Check boxes to select individual deps.", text_color="gray60").grid(row=1, column=0, sticky="w")

        # Button row (right-aligned)
        self._btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self._btn_row.grid(row=0, column=0, padx=16, pady=(12, 6), sticky="e")
        self._rescan_btn = ctk.CTkButton(self._btn_row, text="Re-scan", width=90, command=self._start_rescan)
        self._rescan_btn.grid(row=0, column=0, padx=(0, 4))
        ctk.CTkButton(self._btn_row, text="Select all missing", width=140, command=self._select_all_missing, fg_color="transparent", border_width=1).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkButton(self._btn_row, text="Install selected", width=120, command=self._install_selected, fg_color="#2563eb", hover_color="#1d4ed8").grid(row=0, column=2, padx=(0, 4))
        ctk.CTkButton(self._btn_row, text="Install all missing", width=140, command=self._install_all_missing, fg_color="#16a34a", hover_color="#15803d").grid(row=0, column=3)

        # Table host
        self.table_host = ctk.CTkScrollableFrame(self)
        self.table_host.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="nsew")
        self.table_host.grid_columnconfigure(0, weight=1)

        # Log
        self.log_text = ctk.CTkTextbox(self, height=120, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_text.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------ scan (worker thread)
    def _start_rescan(self) -> None:
        """Start a background scan. Clears the table immediately and
        shows a 'Scanning...' placeholder while the worker thread runs.
        """
        # Clear immediately + show loading state
        for child in self.table_host.winfo_children():
            child.destroy()
        self._row_vars.clear()
        ctk.CTkLabel(self.table_host, text="Scanning dependencies... (this may take a moment)", text_color="gray60").grid(row=0, column=0, padx=10, pady=20)
        self._rescan_btn.configure(state="disabled", text="Scanning...")

        # Clear the module cache so fresh installs are detected.
        clear_module_cache()

        threading.Thread(
            target=self._rescan_worker,
            daemon=True,
            name="DepScan",
        ).start()

    def _rescan_worker(self) -> None:
        """Runs on worker thread. Collects statuses across all tools +
        all providers, then pushes the result rows to the UI thread."""
        rows: list[dict] = []
        for tool in self.app.tools:
            rows.extend(scan_all(tool))
        # Sort: missing first, then by tool name, then by import name.
        rows.sort(key=lambda r: (r.get("status") != "missing", r.get("tool_name", ""), r.get("import_name", "")))
        self._rescan_done_queue.put(rows)

    def _render_rows(self, rows: list[dict]) -> None:
        """UI-thread: render the scanned rows into the table."""
        for child in self.table_host.winfo_children():
            child.destroy()
        self._row_vars.clear()

        if not rows:
            ctk.CTkLabel(self.table_host, text="No dependencies declared or detected.", text_color="gray60").grid(row=0, column=0, padx=10, pady=20)
            self._last_rows = []
            return

        self._build_table_header()
        for i, row in enumerate(rows, start=1):
            self._build_table_row(i, row)
        self._last_rows = rows

    def _build_table_header(self) -> None:
        header = ctk.CTkFrame(self.table_host, fg_color=("gray80", "gray25"))
        header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        cols = [
            ("", 0.3),
            ("Tool", 1.5),
            ("Import", 1.0),
            ("Package", 1.2),
            ("Ecosystem", 0.9),
            ("Status", 0.8),
            ("Version", 0.8),
            ("Notes", 1.5),
        ]
        for i, (label, weight) in enumerate(cols):
            header.grid_columnconfigure(i, weight=int(weight * 10))
            ctk.CTkLabel(header, text=label, font=ctk.CTkFont(size=12, weight="bold"), anchor="w").grid(row=0, column=i, padx=8, pady=4, sticky="w")

    def _build_table_row(self, row_idx: int, row: dict) -> None:
        bg = ("gray92", "gray18") if row_idx % 2 == 0 else ("gray96", "gray14")
        frame = ctk.CTkFrame(self.table_host, fg_color=bg, corner_radius=0)
        frame.grid(row=row_idx, column=0, sticky="ew")

        # Checkbox (column 0)
        is_missing = row.get("status") == "missing"
        var = ctk.BooleanVar(value=is_missing)
        self._row_vars[row_idx - 1] = var
        cb = ctk.CTkCheckBox(frame, text="", variable=var, width=20, height=20)
        cb.grid(row=0, column=0, padx=8, pady=4, sticky="w")

        cols = [
            row.get("tool_name", ""),
            row.get("import_name", ""),
            row.get("package_name", ""),
            row.get("ecosystem", ""),
            row.get("status", ""),
            row.get("version", ""),
            row.get("notes", ""),
        ]
        for i, val in enumerate(cols):
            color = None
            if i == 4:
                if val == "installed":
                    color = "#16a34a"
                elif val == "missing":
                    color = "#dc2626"
                else:
                    color = "#6b7280"
            label = ctk.CTkLabel(frame, text=str(val), anchor="w", text_color=color)
            label.grid(row=0, column=i + 1, padx=8, pady=4, sticky="w")

    # ------------------------------------------------------------------ selection helpers
    def _select_all_missing(self) -> None:
        for i, row in enumerate(getattr(self, "_last_rows", [])):
            var = self._row_vars.get(i)
            if var is not None:
                var.set(row.get("status") == "missing")

    def _get_selected_rows(self) -> list[dict]:
        selected = []
        for i, row in enumerate(getattr(self, "_last_rows", [])):
            var = self._row_vars.get(i)
            if var is not None and var.get():
                selected.append(row)
        return selected

    # ------------------------------------------------------------------ install
    def _install_all_missing(self) -> None:
        missing = [r for r in getattr(self, "_last_rows", []) if r.get("status") == "missing"]
        if not missing:
            self._append_log("[OK] No missing dependencies to install.\n")
            return
        self._install_rows(missing, label="all missing")

    def _install_selected(self) -> None:
        selected = self._get_selected_rows()
        if not selected:
            self._append_log("[WARN] No dependencies selected. Check the boxes next to the deps you want to install.\n")
            return
        self._install_rows(selected, label=f"{len(selected)} selected")

    def _install_rows(self, rows: list[dict], label: str) -> None:
        by_eco: dict[str, list[dict]] = {}
        for m in rows:
            eco = m.get("ecosystem", "python")
            by_eco.setdefault(eco, []).append(m)

        self._append_log(f"[OK] Installing {label} dependencies across {len(by_eco)} ecosystem(s)...\n")

        threading.Thread(
            target=self._install_worker,
            args=(by_eco,),
            daemon=True,
            name="DepInstall",
        ).start()

    def _install_worker(self, by_eco: dict[str, list[dict]]) -> None:
        total_installed = 0
        total_attempted = 0
        for eco, items in by_eco.items():
            total_attempted += len(items)
            try:
                n, log = install_for_ecosystem(eco, items)
                total_installed += n
                self._log_queue.put(log)
            except Exception as e:
                self._log_queue.put(f"[ERROR] {eco}: {e}\n")
        self._install_done_queue.put((total_installed, total_attempted))

    # ------------------------------------------------------------------ UI drain
    def _drain_loop(self) -> None:
        # Guard: stop the loop if the window was destroyed.
        if not self.winfo_exists():
            return
        try:
            # Drain scan results
            while True:
                try:
                    rows = self._rescan_done_queue.get_nowait()
                except queue.Empty:
                    break
                self._render_rows(rows)
                self._rescan_btn.configure(state="normal", text="Re-scan")

            # Drain install log
            while True:
                try:
                    log = self._log_queue.get_nowait()
                except queue.Empty:
                    break
                self._append_log(log)

            # Drain install completion
            while True:
                try:
                    n, total = self._install_done_queue.get_nowait()
                except queue.Empty:
                    break
                self._append_log(f"\n[OK] Installed {n}/{total} packages. Re-scanning...\n")
                self._start_rescan()
        except Exception:
            pass
        self.after(100, self._drain_loop)

    def _append_log(self, text: str) -> None:
        if not self.winfo_exists():
            return
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", text)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass
