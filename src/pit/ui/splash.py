"""Startup splash screen that loads the local evaluator model before the main app.

Shows a clean GUI window while the DeBERTa model is loading into memory
(first run: loads from bundled_model dir; subsequent runs are instant from OS cache).
The user sees a progress indicator but never interacts with CLI or model details.
"""

import threading
import tkinter as tk
from tkinter import ttk

from pit.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG_DARK,
    COLOR_SAFE,
    COLOR_BROKEN,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_TITLE,
    apply_theme,
)


class ModelLoadSplash(tk.Tk):
    """Startup splash that silently loads the local evaluator model.

    Usage:
        splash = ModelLoadSplash(classifier)
        success = splash.run()   # blocks until model ready, then closes itself
        # launch main app next
    """

    _DOTS = ["   ", ".  ", ".. ", "..."]

    def __init__(self, classifier) -> None:
        super().__init__()
        self._classifier = classifier
        self._success: bool | None = None
        self._dot_idx = 0

        self.title("Prompt Injection Tester — Starting…")
        self.geometry("520x300")
        self.resizable(False, False)
        apply_theme(self)
        self.configure(bg=COLOR_BG_DARK)
        # Centre on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 300) // 2
        self.geometry(f"520x300+{x}+{y}")

        self._build_ui()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg=COLOR_BG_DARK)
        outer.pack(expand=True, fill="both", padx=30, pady=30)

        tk.Label(
            outer,
            text="🛡️  Prompt Injection Tester",
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_PRIMARY,
            font=FONT_TITLE,
        ).pack(pady=(0, 4))

        tk.Label(
            outer,
            text="Local Security Evaluator  •  100% Private",
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED,
            font=FONT_BODY,
        ).pack(pady=(0, 24))

        self._progress = ttk.Progressbar(outer, mode="indeterminate", length=460)
        self._progress.pack(pady=(0, 12))
        self._progress.start(12)

        self._lbl_status = tk.Label(
            outer,
            text="Initializing local evaluator model",
            bg=COLOR_BG_DARK, fg=COLOR_ACCENT,
            font=FONT_BODY_BOLD,
            wraplength=460, justify="center",
        )
        self._lbl_status.pack(pady=(0, 8))

        self._lbl_sub = tk.Label(
            outer,
            text="This may take a moment on first run.",
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8),
            wraplength=460, justify="center",
        )
        self._lbl_sub.pack()

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(self) -> bool:
        """Load model in background thread, run Tk event loop, return success."""
        threading.Thread(target=self._load_worker, daemon=True).start()
        self._animate_dots()
        self.mainloop()
        return self._success is True

    # ── Private ────────────────────────────────────────────────────────────────

    def _load_worker(self) -> None:
        """Background thread: load from bundled dir or HF cache."""
        def status_cb(msg: str) -> None:
            try:
                self.after(0, lambda m=msg: self._set_sub(m))
            except tk.TclError:
                pass

        if self._classifier._is_loaded:
            self._finish(success=True)
            return

        from pit.evaluator.bundled import _bundled_model_dir, DEFAULT_MODEL_NAME
        bundled = _bundled_model_dir(DEFAULT_MODEL_NAME)
        if bundled:
            status_cb("Loading evaluator model from local files…")
            ok = self._classifier.load_model()
        else:
            status_cb(f"Downloading {DEFAULT_MODEL_NAME} from Hugging Face…")
            ok = self._classifier.download_model(status_callback=status_cb)

        self._finish(success=ok)

    def _finish(self, success: bool) -> None:
        self._success = success
        try:
            self.after(0, self._on_done)
        except tk.TclError:
            pass

    def _on_done(self) -> None:
        self._progress.stop()
        if self._success:
            self._progress.configure(mode="determinate", value=100)
            self._lbl_status.config(
                text="✓  Evaluator ready  —  launching app…",
                fg=COLOR_SAFE,
            )
            self._lbl_sub.config(text="Subsequent starts will be instant.")
            self.after(700, self.destroy)
        else:
            self._progress.configure(mode="determinate", value=0)
            self._lbl_status.config(
                text="⚠  Model not loaded — app will use fallback heuristics.",
                fg=COLOR_BROKEN,
            )
            self._lbl_sub.config(
                text="You can still run tests. Results may be less accurate."
            )
            self.after(2000, self.destroy)

    def _set_sub(self, msg: str) -> None:
        try:
            short = msg if len(msg) <= 80 else msg[:77] + "…"
            self._lbl_sub.config(text=short)
        except tk.TclError:
            pass

    def _animate_dots(self) -> None:
        if self._success is not None:
            return
        self._dot_idx = (self._dot_idx + 1) % len(self._DOTS)
        dots = self._DOTS[self._dot_idx]
        try:
            current = self._lbl_status.cget("text")
            if "ready" not in current.lower() and "⚠" not in current:
                base = current.rstrip(" .")
                self._lbl_status.config(text=base + dots)
            self.after(400, self._animate_dots)
        except tk.TclError:
            pass
