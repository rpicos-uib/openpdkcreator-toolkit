"""Environment sub-tab (under Settings): generates a real, sourceable
bash script for direct CLI use of the currently-loaded PDK --
``ihp/shell_env.py``'s own ``generate_shell_env_script``, no separate
logic here. A thin GUI wrapper the same way ``tools_view.py`` wraps
``eda_tools.py``: this view only calls that one function and writes
its own returned text to disk; every real path/convention decision
lives there, not here.

**Save Script** writes to ``shell_env/pdk_env.sh`` at this project's
own root (gitignored -- like ``data/``/``saves/``/``export/``, it's
derived, local, and (via an absolute ``PDK_ROOT``) machine-specific,
not shareable content), made executable. **Copy to Clipboard** is a
cheap, real convenience for pasting straight into a terminal without
touching disk at all.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import export as export_mod
from ..ihp import shell_env as shell_env_mod

SHELL_ENV_DIRNAME = "shell_env"
SCRIPT_NAME = "pdk_env.sh"


class EnvironmentView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(
            top,
            text="A real, sourceable shell script for running this PDK's tools directly from the CLI.",
        ).pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(button_row, text="Save Script", command=self._save_script).pack(side="left")
        ttk.Button(button_row, text="Copy to Clipboard", command=self._copy_to_clipboard).pack(
            side="left", padx=(6, 0)
        )

        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor="w", foreground="#2e7d32").pack(
            fill="x", padx=8, pady=(0, 4)
        )

        self.script_text = tk.Text(self, wrap="none", state="disabled", font=("TkFixedFont",))
        self.script_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def refresh(self):
        self.current_script = shell_env_mod.generate_shell_env_script(self.app.pdk_root, SCRIPT_NAME)
        self.script_text.configure(state="normal")
        self.script_text.delete("1.0", "end")
        self.script_text.insert("1.0", self.current_script)
        self.script_text.configure(state="disabled")
        self.status_var.set("")

    def _save_script(self):
        dest_dir = export_mod.PROJECT_ROOT / SHELL_ENV_DIRNAME
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / SCRIPT_NAME
        dest_path.write_text(self.current_script, encoding="utf-8")
        dest_path.chmod(0o755)
        self.status_var.set(f"Saved to {dest_path} -- run: source {dest_path}")

    def _copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.current_script)
        self.status_var.set("Copied to clipboard.")
