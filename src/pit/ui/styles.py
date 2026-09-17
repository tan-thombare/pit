"""Modern styling and theme constants for Tkinter UI."""

import tkinter as tk
from tkinter import ttk

# Modern Dark / Slate Palette
COLOR_BG_DARK = "#0F172A"       # Slate 900
COLOR_BG_CARD = "#1E293B"       # Slate 800
COLOR_BG_INPUT = "#334155"      # Slate 700
COLOR_BORDER = "#475569"        # Slate 600
COLOR_TEXT_PRIMARY = "#F8FAFC"  # Slate 50
COLOR_TEXT_MUTED = "#94A3B8"    # Slate 400
COLOR_ACCENT = "#38BDF8"        # Sky 400
COLOR_ACCENT_HOVER = "#0284C7"  # Sky 600

# Verdict colors
COLOR_SAFE = "#10B981"          # Emerald 500
COLOR_SUSPECT = "#F59E0B"       # Amber 500
COLOR_BROKEN = "#EF4444"        # Red 500
COLOR_ERROR = "#64748B"         # Slate 500

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_SUBTITLE = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 9)
FONT_BODY_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SCORE = ("Segoe UI", 26, "bold")


def apply_theme(root: tk.Tk) -> ttk.Style:
    """Apply modern custom styling to ttk widgets."""
    style = ttk.Style(root)
    
    # Try clam theme as base for maximum customizability across platforms
    available = style.theme_names()
    if "clam" in available:
        style.theme_use("clam")

    root.configure(bg=COLOR_BG_DARK)

    # General Frames
    style.configure("TFrame", background=COLOR_BG_DARK)
    style.configure("Card.TFrame", background=COLOR_BG_CARD, relief="flat")
    
    # Labels
    style.configure("TLabel", background=COLOR_BG_DARK, foreground=COLOR_TEXT_PRIMARY, font=FONT_BODY)
    style.configure("Muted.TLabel", background=COLOR_BG_DARK, foreground=COLOR_TEXT_MUTED, font=FONT_BODY)
    style.configure("Card.TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT_PRIMARY, font=FONT_BODY)
    style.configure("CardMuted.TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT_MUTED, font=FONT_BODY)
    style.configure("Title.TLabel", background=COLOR_BG_DARK, foreground=COLOR_TEXT_PRIMARY, font=FONT_TITLE)
    style.configure("Subtitle.TLabel", background=COLOR_BG_DARK, foreground=COLOR_TEXT_PRIMARY, font=FONT_SUBTITLE)
    style.configure("CardTitle.TLabel", background=COLOR_BG_CARD, foreground=COLOR_TEXT_PRIMARY, font=FONT_SUBTITLE)

    # Buttons
    style.configure(
        "TButton",
        background=COLOR_BG_INPUT,
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor="none",
        padding=(10, 5),
    )
    style.map(
        "TButton",
        background=[("active", COLOR_BORDER), ("disabled", "#1E293B")],
        foreground=[("disabled", "#64748B")],
    )

    style.configure(
        "Accent.TButton",
        background=COLOR_ACCENT,
        foreground="#0F172A",
        font=FONT_BODY_BOLD,
        padding=(12, 6),
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLOR_ACCENT_HOVER), ("disabled", "#334155")],
        foreground=[("disabled", "#64748B")],
    )

    style.configure(
        "Danger.TButton",
        background="#DC2626",
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        padding=(12, 6),
    )
    style.map(
        "Danger.TButton",
        background=[("active", "#B91C1C"), ("disabled", "#334155")],
        foreground=[("disabled", "#64748B")],
    )

    # Notebook Tabs
    style.configure(
        "TNotebook",
        background=COLOR_BG_DARK,
        borderwidth=0,
        tabmargins=[0, 0, 0, 0],
    )
    style.configure(
        "TNotebook.Tab",
        background=COLOR_BG_CARD,
        foreground=COLOR_TEXT_MUTED,
        font=FONT_BODY_BOLD,
        padding=(16, 8),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOR_BG_DARK)],
        foreground=[("selected", COLOR_ACCENT)],
    )

    # Entry & Combobox
    style.configure(
        "TEntry",
        fieldbackground=COLOR_BG_INPUT,
        foreground=COLOR_TEXT_PRIMARY,
        insertcolor=COLOR_TEXT_PRIMARY,
        padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground=COLOR_BG_INPUT,
        background=COLOR_BG_INPUT,
        foreground=COLOR_TEXT_PRIMARY,
        arrowcolor=COLOR_TEXT_PRIMARY,
        padding=4,
    )

    # Progressbar
    style.configure(
        "TProgressbar",
        troughcolor=COLOR_BG_INPUT,
        background=COLOR_ACCENT,
        thickness=8,
    )

    # Treeview (Results table)
    style.configure(
        "Treeview",
        background=COLOR_BG_CARD,
        foreground=COLOR_TEXT_PRIMARY,
        fieldbackground=COLOR_BG_CARD,
        font=FONT_BODY,
        rowheight=26,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=COLOR_BG_INPUT,
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY_BOLD,
        padding=(6, 4),
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", "#0369A1")],
        foreground=[("selected", "#FFFFFF")],
    )

    return style
