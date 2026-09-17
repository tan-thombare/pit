"""Main application window assembling views, navigation, and persistent state."""


import logging
import tkinter as tk
from tkinter import ttk

from pit.attacks.loader import load_attacks
from pit.attacks.models import Attack
from pit.config.manager import ConfigManager
from pit.config.models import AppConfig
from pit.evaluator.classifier import PromptGuardClassifier
from pit.evaluator.scorer import CompositeEvaluator
from pit.runner.engine import TestEngine
from pit.storage.results import SingleTestResult, SuiteSummary
from pit.ui.config_view import ConfigView
from pit.ui.results_view import ResultsView
from pit.ui.styles import (
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    apply_theme,
)
from pit.ui.test_view import TestView

logger = logging.getLogger(__name__)


class PromptInjectionTesterApp(tk.Tk):
    """Main Prompt Injection Tester Tkinter Desktop Application."""

    def __init__(self, attacks: list[Attack] | None = None, classifier: PromptGuardClassifier | None = None) -> None:
        super().__init__()
        self.title("Prompt Injection Tester (PIT) - Local Security Evaluator")
        self.geometry("1100x760")
        self.minsize(980, 680)

        # Persistence & Core Services
        self.config_manager = ConfigManager()
        self.app_config: AppConfig = self.config_manager.load()

        # Use pre-warmed classifier from splash (model already in memory), or create fresh
        self.classifier = classifier or PromptGuardClassifier(
            model_name=self.app_config.evaluator.model_name,
            preferred_device=self.app_config.evaluator.device,
        )
        self.evaluator = CompositeEvaluator(classifier=self.classifier)
        self.engine = TestEngine()

        self.attacks = attacks if attacks is not None else load_attacks()

        # UI Initialization
        apply_theme(self)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        # Notebook with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: Configuration
        self.config_view = ConfigView(
            self.notebook,
            app_config=self.app_config,
            classifier=self.classifier,
            on_config_changed=self._on_config_changed,
        )
        self.notebook.add(self.config_view, text="  ⚙️ Target & Evaluator  ")

        # Tab 2: Attacks & Test Execution
        self.test_view = TestView(
            self.notebook,
            attacks=self.attacks,
            engine=self.engine,
            evaluator=self.evaluator,
            get_config=lambda: self.app_config,
            on_suite_completed=self._on_suite_completed,
        )
        self.notebook.add(self.test_view, text="  🎯 Attack Suite  ")

        # Tab 3: Results Dashboard
        self.results_view = ResultsView(self.notebook)
        self.notebook.add(self.results_view, text="  📊 Security Results  ")

        # Persistent Bottom Status Bar
        self.status_bar = tk.Frame(self, bg=COLOR_BG_INPUT, height=26, padx=12, pady=4)
        self.status_bar.pack(fill="x", side="bottom")

        self.lbl_status_privacy = tk.Label(
            self.status_bar,
            text="🔒 100% Local Inference • Zero External Judging Telemetry",
            bg=COLOR_BG_INPUT,
            fg="#6EE7B7",
            font=("Segoe UI", 8, "bold"),
        )
        self.lbl_status_privacy.pack(side="left")

        self.lbl_status_target = tk.Label(
            self.status_bar,
            text=self._target_label(),
            bg=COLOR_BG_INPUT,
            fg=COLOR_TEXT_MUTED,
            font=("Segoe UI", 8),
        )
        self.lbl_status_target.pack(side="right")

    def _target_label(self) -> str:
        endpoint = self.app_config.api.effective_endpoint
        if endpoint:
            label = endpoint if len(endpoint) <= 60 else "…" + endpoint[-57:]
            return f"Target: {label}"
        return "Target: (not configured)"

    def _on_config_changed(self, new_config: AppConfig) -> None:
        self.app_config = new_config
        self.config_manager.save(new_config)
        self.lbl_status_target.config(text=self._target_label())

    def _on_suite_completed(self, summary: SuiteSummary, results: list[SingleTestResult]) -> None:
        self.results_view.update_results(summary, results)
        # Automatically switch to Results tab to show dashboard
        self.notebook.select(2)

    def _on_close(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        self.config_manager.save(self.app_config)
        self.destroy()


def launch_app() -> None:
    """Entry point to launch the Tkinter GUI.

    Shows a model-loading splash screen first so the evaluator is warm
    by the time the main window appears. On first run this may take
    30-90 seconds while weights are read from disk into memory; all
    subsequent runs are fast because the OS caches the file pages.
    """
    from pit.evaluator.classifier import PromptGuardClassifier
    from pit.config.manager import ConfigManager
    from pit.ui.splash import ModelLoadSplash

    # Resolve the device / config so we can pre-warm the classifier
    cfg = ConfigManager().load()
    classifier = PromptGuardClassifier(
        model_name=cfg.evaluator.model_name,
        preferred_device=cfg.evaluator.device,
    )

    # Show splash & load model — blocks until done, then splash closes itself
    splash = ModelLoadSplash(classifier)
    splash.run()

    # Launch the main application, passing the already-warmed classifier
    app = PromptInjectionTesterApp(classifier=classifier)
    app.mainloop()
