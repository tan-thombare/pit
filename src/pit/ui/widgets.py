"""Custom helper widgets for the Tkinter user interface."""

import tkinter as tk
from tkinter import ttk
from pit.ui.styles import (
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SCORE,
    FONT_SUBTITLE,
)


class CardFrame(tk.Frame):
    """Clean framed container with rounded/flat card appearance and padding."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(
            parent,
            bg=COLOR_BG_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=14,
            pady=12,
            **kwargs,
        )


class MetricCard(CardFrame):
    """Dashboard card showing a metric count and label."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        value: str = "0",
        value_color: str = COLOR_TEXT_PRIMARY,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.lbl_title = tk.Label(
            self,
            text=title.upper(),
            bg=COLOR_BG_CARD,
            fg=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8, "bold"),
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_val = tk.Label(
            self,
            text=value,
            bg=COLOR_BG_CARD,
            fg=value_color,
            font=FONT_SCORE,
        )
        self.lbl_val.pack(anchor="w", pady=(2, 0))

    def update_value(self, value: str) -> None:
        self.lbl_val.config(text=value)


class LabeledEntry(tk.Frame):
    """Horizontal or vertical label + entry field with placeholder support."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        initial_value: str = "",
        is_password: bool = False,
        width: int = 30,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLOR_BG_CARD, **kwargs)
        self.lbl = tk.Label(
            self,
            text=label,
            bg=COLOR_BG_CARD,
            fg=COLOR_TEXT_PRIMARY,
            font=FONT_BODY_BOLD,
        )
        self.lbl.pack(anchor="w", pady=(0, 3))

        self.entry_frame = tk.Frame(self, bg=COLOR_BG_CARD)
        self.entry_frame.pack(fill="x", expand=True)

        self.var = tk.StringVar(value=initial_value)
        self.is_password = is_password
        self._show_state = False

        self.entry = tk.Entry(
            self.entry_frame,
            textvariable=self.var,
            show="*" if is_password else "",
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="flat",
            font=FONT_BODY,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            width=width,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 4))

        if is_password:
            self.btn_toggle = tk.Button(
                self.entry_frame,
                text="👁",
                bg=COLOR_BG_INPUT,
                fg=COLOR_TEXT_MUTED,
                activebackground=COLOR_BORDER,
                activeforeground=COLOR_TEXT_PRIMARY,
                relief="flat",
                command=self._toggle_password,
                font=("Segoe UI", 8),
                padx=6,
            )
            self.btn_toggle.pack(side="right")

    def _toggle_password(self) -> None:
        self._show_state = not self._show_state
        self.entry.config(show="" if self._show_state else "*")
        self.btn_toggle.config(fg=COLOR_TEXT_PRIMARY if self._show_state else COLOR_TEXT_MUTED)

    def get(self) -> str:
        return self.var.get()

    def set(self, val: str) -> None:
        self.var.set(val)


class ReadOnlyText(tk.Frame):
    """Scrollable, read-only dark text display."""

    def __init__(self, parent: tk.Widget, height: int = 6, **kwargs) -> None:
        super().__init__(parent, bg=COLOR_BG_CARD, **kwargs)
        self.text = tk.Text(
            self,
            height=height,
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_PRIMARY,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 9),
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=8,
            pady=6,
        )
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.config(state="disabled")

    def set_content(self, text: str) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.config(state="disabled")
