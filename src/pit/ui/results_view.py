"""Results Dashboard and Inspection View."""

from datetime import datetime
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pit.evaluator.models import Verdict
from pit.storage.results import (
    SingleTestResult,
    SuiteSummary,
    TestRunReport,
    export_to_csv,
    export_to_json,
)
from pit.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_BROKEN,
    COLOR_ERROR,
    COLOR_SAFE,
    COLOR_SUSPECT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CODE,
    FONT_SCORE,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from pit.ui.widgets import CardFrame, MetricCard, ReadOnlyText


class ResultsView(tk.Frame):
    """Security testing dashboard with metrics, results table, details panel, and export."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=COLOR_BG_DARK, **kwargs)
        self.summary: SuiteSummary | None = None
        self.results: list[SingleTestResult] = []
        self._results_by_id: dict[str, SingleTestResult] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        # Split into Top (Metrics & Actions), Middle (Results Table), Bottom (Details Inspector)
        top_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        top_frame.pack(fill="x", padx=16, pady=(16, 8))

        # Top row: Title + Export Buttons
        header_row = tk.Frame(top_frame, bg=COLOR_BG_DARK)
        header_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            header_row,
            text="Security Test Results & Analysis",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_PRIMARY,
            font=FONT_TITLE,
        ).pack(side="left")

        # Export buttons
        btn_export_csv = ttk.Button(header_row, text="Export CSV", style="TButton", command=self._export_csv)
        btn_export_csv.pack(side="right", padx=(6, 0))

        btn_export_json = ttk.Button(header_row, text="Export JSON", style="TButton", command=self._export_json)
        btn_export_json.pack(side="right")

        # Metrics Cards Row
        metrics_row = tk.Frame(top_frame, bg=COLOR_BG_DARK)
        metrics_row.pack(fill="x")

        self.card_score = MetricCard(metrics_row, title="Security Score", value="--/100", value_color=COLOR_ACCENT)
        self.card_score.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.card_total = MetricCard(metrics_row, title="Tests Executed", value="0", value_color=COLOR_TEXT_PRIMARY)
        self.card_total.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.card_safe = MetricCard(metrics_row, title="Safe (Resisted)", value="0", value_color=COLOR_SAFE)
        self.card_safe.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.card_suspect = MetricCard(metrics_row, title="Suspected Bypass", value="0", value_color=COLOR_SUSPECT)
        self.card_suspect.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.card_broken = MetricCard(metrics_row, title="Successful Injection", value="0", value_color=COLOR_BROKEN)
        self.card_broken.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.card_error = MetricCard(metrics_row, title="Errors", value="0", value_color=COLOR_ERROR)
        self.card_error.pack(side="left", fill="both", expand=True)

        # PanedWindow: Upper half is table, lower half is detail inspector
        paned = tk.PanedWindow(self, orient="vertical", bg=COLOR_BORDER, sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        # Upper Table Frame
        table_container = tk.Frame(paned, bg=COLOR_BG_CARD)
        paned.add(table_container, minsize=140, height=220)

        cols = ("id", "name", "category", "severity", "latency", "verdict")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID", anchor="w")
        self.tree.heading("name", text="Attack Name", anchor="w")
        self.tree.heading("category", text="Category", anchor="w")
        self.tree.heading("severity", text="Severity", anchor="center")
        self.tree.heading("latency", text="Latency", anchor="e")
        self.tree.heading("verdict", text="Verdict", anchor="center")

        self.tree.column("id", width=80, anchor="w")
        self.tree.column("name", width=280, anchor="w")
        self.tree.column("category", width=180, anchor="w")
        self.tree.column("severity", width=100, anchor="center")
        self.tree.column("latency", width=90, anchor="e")
        self.tree.column("verdict", width=160, anchor="center")

        # Configure color tags for results table
        self.tree.tag_configure("SAFE", foreground=COLOR_SAFE)
        self.tree.tag_configure("SUSPECTED BYPASS", foreground=COLOR_SUSPECT)
        self.tree.tag_configure("SUCCESSFUL INJECTION", foreground=COLOR_BROKEN)
        self.tree.tag_configure("ERROR", foreground=COLOR_ERROR)

        tree_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select_result)

        # Lower Detail Inspector Frame
        self.detail_frame = CardFrame(paned)
        paned.add(self.detail_frame, minsize=180, height=260)
        self._build_detail_inspector(self.detail_frame)

    def _build_detail_inspector(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=COLOR_BG_CARD)
        header.pack(fill="x", pady=(0, 8))

        self.lbl_detail_title = tk.Label(
            header,
            text="Select a test in the table above to inspect full prompt, response, and observable signals.",
            bg=COLOR_BG_CARD,
            fg=COLOR_TEXT_PRIMARY,
            font=FONT_SUBTITLE,
        )
        self.lbl_detail_title.pack(side="left")

        self.lbl_detail_badge = tk.Label(header, text="", bg=COLOR_BG_CARD, font=FONT_BODY_BOLD)
        self.lbl_detail_badge.pack(side="right")

        # Two columns: Left (Prompt & Response), Right (Signals, Reasoning, Metadata)
        split_frame = tk.Frame(parent, bg=COLOR_BG_CARD)
        split_frame.pack(fill="both", expand=True)

        # Left Column: Texts
        left_col = tk.Frame(split_frame, bg=COLOR_BG_CARD)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left_col, text="PROMPT SENT TO TARGET", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.txt_prompt = ReadOnlyText(left_col, height=4)
        self.txt_prompt.pack(fill="both", expand=True, pady=(2, 6))

        tk.Label(left_col, text="TARGET LLM COMPLETE RESPONSE", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.txt_response = ReadOnlyText(left_col, height=4)
        self.txt_response.pack(fill="both", expand=True, pady=(2, 0))

        # Right Column: Evaluation Signals, Reasoning, Risk
        right_col = tk.Frame(split_frame, bg=COLOR_BG_CARD, width=320)
        right_col.pack(side="right", fill="both", padx=(8, 0))

        tk.Label(right_col, text="LOCAL EVALUATION & OBSERVABLE SIGNALS", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.txt_reasoning = ReadOnlyText(right_col, height=9)
        self.txt_reasoning.pack(fill="both", expand=True, pady=(2, 0))

    def update_results(self, summary: SuiteSummary, results: list[SingleTestResult]) -> None:
        """Update metrics, table, and details with new test results."""
        self.summary = summary
        self.results = results
        self._results_by_id = {r.attack_id: r for r in results}

        # Update metric cards
        score_color = COLOR_SAFE if summary.security_score >= 80 else (COLOR_SUSPECT if summary.security_score >= 50 else COLOR_BROKEN)
        self.card_score.lbl_val.config(text=f"{summary.security_score}/100", fg=score_color)
        self.card_total.update_value(str(summary.total))
        self.card_safe.update_value(str(summary.safe))
        self.card_suspect.update_value(str(summary.suspected))
        self.card_broken.update_value(str(summary.broken))
        self.card_error.update_value(str(summary.error))

        # Populate treeview
        self.tree.delete(*self.tree.get_children())
        for r in results:
            tag = r.verdict
            self.tree.insert(
                "",
                "end",
                iid=r.attack_id,
                values=(r.attack_id, r.attack_name, r.category, r.severity.upper(), f"{r.latency:.0f} ms", r.verdict),
                tags=(tag,),
            )

        # Select first result if available
        if results:
            first_id = results[0].attack_id
            self.tree.selection_set(first_id)
            self._display_detail(results[0])

    def _on_select_result(self, event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        attack_id = selected[0]
        result = self._results_by_id.get(attack_id)
        if result:
            self._display_detail(result)

    def _display_detail(self, r: SingleTestResult) -> None:
        self.lbl_detail_title.config(text=f"{r.attack_id} - {r.attack_name}  [{r.category} | {r.severity.upper()}]")

        color_map = {
            Verdict.SAFE.value: COLOR_SAFE,
            Verdict.SUSPECTED_BYPASS.value: COLOR_SUSPECT,
            Verdict.SUCCESSFUL_INJECTION.value: COLOR_BROKEN,
            Verdict.ERROR.value: COLOR_ERROR,
        }
        badge_color = color_map.get(r.verdict, COLOR_TEXT_PRIMARY)
        self.lbl_detail_badge.config(
            text=f"  {r.verdict}  |  Risk: {r.risk_score:.0f}/100  |  Conf: {int(r.confidence * 100)}%  ",
            fg=badge_color,
        )

        self.txt_prompt.set_content(r.prompt)
        self.txt_response.set_content(r.response if r.response else (f"[No Response / Error: {r.error}]" if r.error else "[Empty Response]"))

        # Format reasoning and signals
        info_lines = [
            f"Verdict: {r.verdict}",
            f"Risk Score: {r.risk_score:.1f} / 100",
            f"Evaluator Confidence: {int(r.confidence * 100)}%",
            f"Latency: {r.latency} ms",
            f"Timestamp: {r.timestamp}",
            "",
            "Reasoning:",
            f"  {r.reasoning}",
            "",
            "Observable Signals Detected:",
        ]

        if r.signals:
            for s in r.signals:
                status = "✓ Triggered" if s.get("triggered") else "○ Not Triggered"
                name = s.get("name", "")
                desc = s.get("description", "")
                info_lines.append(f"  • [{status}] {name}: {desc}")
        else:
            info_lines.append("  (No specific signals recorded)")

        if r.error:
            info_lines.extend(["", f"Reported Error: {r.error}"])

        self.txt_reasoning.set_content("\n".join(info_lines))

    def _export_json(self) -> None:
        if not self.results or not self.summary:
            messagebox.showinfo("Export", "No test results available to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"pit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not filename:
            return

        report = TestRunReport(summary=self.summary, results=self.results)
        try:
            export_to_json(report, filename)
            messagebox.showinfo("Export Successful", f"Results exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _export_csv(self) -> None:
        if not self.results:
            messagebox.showinfo("Export", "No test results available to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"pit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not filename:
            return

        try:
            export_to_csv(self.results, filename)
            messagebox.showinfo("Export Successful", f"Results exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))
