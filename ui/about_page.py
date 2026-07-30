"""About window (CTkToplevel, modal)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.app import App


APP_VERSION = "3.0.0"


class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master, app: "App") -> None:
        super().__init__(master)
        self.app = app
        self.transient(master)
        self.grab_set()

        self.title("About Tool Pouch")
        self.geometry("480x440")
        self.minsize(440, 420)

        # Set our custom icon BEFORE CTk's 200ms timer overrides it.
        from ui.window_icon import set_window_icon
        set_window_icon(self)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        host = ctk.CTkFrame(self, fg_color="transparent")
        host.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        host.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(host, text="Tool Pouch", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, pady=(0, 4))
        ctk.CTkLabel(host, text=f"Version {APP_VERSION}", text_color="gray60").grid(row=1, column=0, pady=(0, 16))

        body = (
            "A modular, extensible GUI for local utility scripts.\n\n"
            "Drop a new tool folder into Tools/ and it appears in the sidebar "
            "automatically. Each tool declares its parameters in a tool.toml "
            "manifest; Tool Pouch generates the form, launches the script as a "
            "child OS process, and streams its stdout into a colored log console.\n\n"
            "Multi-language: Python (.py), PowerShell (.ps1), Batch (.bat/.cmd), "
            "and JavaScript (.js) tools are all supported.\n\n"
            "Built with CustomTkinter — no Qt, lightweight, Windows-native."
        )
        ctk.CTkLabel(host, text=body, wraplength=420, justify="left").grid(row=2, column=0, pady=(0, 16))

        ctk.CTkLabel(
            host,
            text=(
                "Configuration: ~/.toolpouch/config.json\n"
                "Logs: ~/.toolpouch/logs/\n"
                f"Tools folder: {app.tools_dir}"
            ),
            text_color="gray60",
            justify="left",
            font=ctk.CTkFont(size=11),
        ).grid(row=3, column=0, pady=(0, 16))

        ctk.CTkButton(host, text="Close", width=90, command=self.destroy).grid(row=4, column=0)
