"""Target AI Application & Local Evaluator Configuration View."""

import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from pit.config.models import (
    AUTH_PRESET_DEFAULTS,
    APIConfig,
    AppConfig,
    AuthPreset,
    ProviderType,
)
from pit.evaluator.classifier import (
    DEFAULT_MODEL_NAME,
    PromptGuardClassifier,
)
from pit.providers import create_provider
from pit.ui.styles import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_BG_DARK,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_BROKEN,
    COLOR_SAFE,
    COLOR_SUSPECT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_CODE,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from pit.ui.widgets import CardFrame, LabeledEntry

# ── Provider preset definitions ───────────────────────────────────────────────
# Each entry: (display_label, ProviderType, base_url, model, request_template,
#              response_path, auth_preset, auth_header, auth_value_template)
PROVIDER_PRESETS = [
    (
        "OpenAI  (GPT-4o, GPT-4o-mini …)",
        ProviderType.OPENAI,
        "https://api.openai.com/v1",
        "gpt-4o-mini",
        '{"model": "{{model}}", "messages": [{"role": "system", "content": "{{system_prompt}}"}, {"role": "user", "content": "{{prompt}}"}], "temperature": 0, "max_tokens": 512}',
        "choices.0.message.content",
        AuthPreset.BEARER_TOKEN,
        "Authorization",
        "Bearer {{api_key}}",
    ),
    (
        "Anthropic  (Claude 3.x / claude-3-5-haiku …)",
        ProviderType.ANTHROPIC,
        "https://api.anthropic.com/v1",
        "claude-3-5-haiku-20241022",
        '{"model": "{{model}}", "messages": [{"role": "user", "content": "{{prompt}}"}], "system": "{{system_prompt}}", "max_tokens": 512}',
        "content.0.text",
        AuthPreset.API_KEY_HEADER,
        "x-api-key",
        "{{api_key}}",
    ),
    (
        "OpenAI-Compatible  (Ollama, vLLM, Groq, LM Studio …)",
        ProviderType.OPENAI_COMPATIBLE,
        "http://localhost:11434/v1",
        "llama3",
        '{"model": "{{model}}", "messages": [{"role": "user", "content": "{{prompt}}"}]}',
        "choices.0.message.content",
        AuthPreset.BEARER_TOKEN,
        "Authorization",
        "Bearer {{api_key}}",
    ),
    (
        "AWS Bedrock  (Claude / Titan via Bedrock Runtime)",
        ProviderType.GENERIC_HTTP,
        "",
        "",
        '{"inputText": "{{prompt}}"}',
        "results.0.outputText",
        AuthPreset.CUSTOM,
        "Authorization",
        "AWS4-HMAC-SHA256 Credential={{api_key}}",
    ),
    (
        "Azure OpenAI",
        ProviderType.OPENAI_COMPATIBLE,
        "https://<your-resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-02-01",
        "gpt-4o",
        '{"messages": [{"role": "user", "content": "{{prompt}}"}], "max_tokens": 512}',
        "choices.0.message.content",
        AuthPreset.CUSTOM,
        "api-key",
        "{{api_key}}",
    ),
    (
        "Google Gemini  (v1beta REST API)",
        ProviderType.GENERIC_HTTP,
        "",
        "",
        '{"contents": [{"parts": [{"text": "{{prompt}}"}]}]}',
        "candidates.0.content.parts.0.text",
        AuthPreset.CUSTOM,
        "x-goog-api-key",
        "{{api_key}}",
    ),
    (
        "Custom AI Application  (chatbot / RAG / any HTTP endpoint)",
        ProviderType.GENERIC_HTTP,
        "",
        "",
        '{"message": "{{prompt}}"}',
        "response",
        AuthPreset.BEARER_TOKEN,
        "Authorization",
        "Bearer {{api_key}}",
    ),
]

_PRESET_LABELS = [p[0] for p in PROVIDER_PRESETS]


class ConfigView(tk.Frame):
    """View allowing security testers to configure the target AI application and local evaluator."""

    def __init__(
        self,
        parent: tk.Widget,
        app_config: AppConfig,
        classifier: PromptGuardClassifier,
        on_config_changed: Callable[[AppConfig], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, bg=COLOR_BG_DARK, **kwargs)
        self.app_config = app_config
        self.classifier = classifier
        self.on_config_changed = on_config_changed

        self._build_ui()
        self.refresh_evaluator_status()

    # ── Top-level layout ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        canvas = tk.Canvas(self, bg=COLOR_BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=COLOR_BG_DARK)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        cw = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        scrollbar.pack(side="right", fill="y", pady=16, padx=(0, 16))

        # Bind mouse-wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._canvas = canvas

        self._build_privacy_banner(self._scroll_frame)
        self._build_target_card(self._scroll_frame)
        self._build_preset_section(self._scroll_frame)
        self._build_advanced_section(self._scroll_frame)
        self._build_evaluator_card(self._scroll_frame)

    # ── Privacy banner ────────────────────────────────────────────────────────

    def _build_privacy_banner(self, parent: tk.Widget) -> None:
        banner = tk.Frame(
            parent,
            bg="#064E3B",
            highlightbackground="#059669",
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        banner.pack(fill="x", pady=(0, 14))

        tk.Label(
            banner, text="🔒 LOCAL PRIVACY GUARANTEE",
            bg="#064E3B", fg="#6EE7B7", font=FONT_BODY_BOLD,
        ).pack(anchor="w")
        tk.Label(
            banner,
            text=(
                "Evaluation is performed 100% locally via a local Hugging Face classifier. "
                "Target application responses are NEVER forwarded to a cloud judging API."
            ),
            bg="#064E3B", fg="#D1FAE5", font=FONT_BODY, wraplength=760, justify="left",
        ).pack(anchor="w", pady=(2, 0))

    # ── Section 1: Target AI Application (primary) ────────────────────────────

    def _build_target_card(self, parent: tk.Widget) -> None:
        card = CardFrame(parent)
        card.pack(fill="x", pady=(0, 4))

        tk.Label(
            card, text="🎯  Target AI Application",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_TITLE,
        ).pack(anchor="w", pady=(0, 2))
        tk.Label(
            card,
            text="Enter your AI application's endpoint URL. Works with any chatbot, RAG pipeline, custom API, or hosted LLM.",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY, wraplength=760, justify="left",
        ).pack(anchor="w", pady=(0, 12))

        form = tk.Frame(card, bg=COLOR_BG_CARD)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        row = 0

        # ── Endpoint URL ──────────────────────────────────────────────────────
        tk.Label(
            form, text="Endpoint URL", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD,
        ).grid(row=row, column=0, sticky="w", pady=(0, 6), padx=(0, 12))

        url_frame = tk.Frame(form, bg=COLOR_BG_CARD)
        url_frame.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        url_frame.columnconfigure(0, weight=1)

        self.endpoint_var = tk.StringVar(value=self.app_config.api.endpoint_url)
        endpoint_entry = ttk.Entry(url_frame, textvariable=self.endpoint_var, font=FONT_CODE)
        endpoint_entry.grid(row=0, column=0, sticky="ew")
        tk.Label(
            url_frame,
            text="e.g.  https://your-chatbot.com/api/chat   or   http://localhost:8000/generate",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        row += 1

        # ── API Key + Auth scheme ─────────────────────────────────────────────
        tk.Label(
            form, text="API Key", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD,
        ).grid(row=row, column=0, sticky="nw", pady=(8, 0), padx=(0, 12))

        auth_outer = tk.Frame(form, bg=COLOR_BG_CARD)
        auth_outer.grid(row=row, column=1, sticky="ew", pady=(8, 0))
        auth_outer.columnconfigure(0, weight=1)

        # Password entry row
        key_row = tk.Frame(auth_outer, bg=COLOR_BG_CARD)
        key_row.pack(fill="x")
        key_row.columnconfigure(0, weight=1)

        self.key_entry = LabeledEntry(key_row, label="", initial_value=self.app_config.api.api_key, is_password=True)
        self.key_entry.lbl.destroy()
        self.key_entry.grid(row=0, column=0, sticky="ew")

        tk.Label(
            key_row, text="Leave blank if no auth needed",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        ).grid(row=1, column=0, sticky="w", pady=(2, 6))

        # Auth preset quick buttons
        preset_btn_frame = tk.Frame(auth_outer, bg=COLOR_BG_CARD)
        preset_btn_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            preset_btn_frame, text="Auth scheme:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY,
        ).pack(side="left", padx=(0, 8))

        self._auth_preset_btns: dict[str, ttk.Button] = {}
        for preset in [AuthPreset.BEARER_TOKEN, AuthPreset.API_KEY_HEADER, AuthPreset.CUSTOM]:
            btn = ttk.Button(
                preset_btn_frame,
                text=preset.value,
                style="TButton",
                command=lambda p=preset: self._apply_auth_preset(p),
            )
            btn.pack(side="left", padx=(0, 6))
            self._auth_preset_btns[preset] = btn

        # Expandable custom auth row (always shown, enabled when Custom)
        custom_auth_frame = tk.Frame(auth_outer, bg=COLOR_BG_INPUT, padx=10, pady=8)
        custom_auth_frame.pack(fill="x")
        custom_auth_frame.columnconfigure(1, weight=1)
        custom_auth_frame.columnconfigure(3, weight=2)

        tk.Label(
            custom_auth_frame, text="Header Name:", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MUTED, font=FONT_BODY,
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.auth_header_var = tk.StringVar(value=self.app_config.api.auth_header_name)
        self.auth_header_entry = ttk.Entry(custom_auth_frame, textvariable=self.auth_header_var, width=22)
        self.auth_header_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        tk.Label(
            custom_auth_frame, text="Value Template:", bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MUTED, font=FONT_BODY,
        ).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.auth_value_var = tk.StringVar(value=self.app_config.api.auth_value_template)
        self.auth_value_entry = ttk.Entry(custom_auth_frame, textvariable=self.auth_value_var)
        self.auth_value_entry.grid(row=0, column=3, sticky="ew")

        tk.Label(
            custom_auth_frame,
            text="Use {{api_key}} as placeholder in the value template",
            bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))

        self._custom_auth_frame = custom_auth_frame
        row += 1

        # ── Request Template ──────────────────────────────────────────────────
        tk.Label(
            form, text="Request Body\nTemplate", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD,
        ).grid(row=row, column=0, sticky="nw", pady=(12, 0), padx=(0, 12))

        tpl_frame = tk.Frame(form, bg=COLOR_BG_CARD)
        tpl_frame.grid(row=row, column=1, sticky="ew", pady=(12, 0))

        self.tpl_text = tk.Text(
            tpl_frame,
            height=4,
            bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="flat", wrap="none", font=FONT_CODE,
            highlightbackground=COLOR_BORDER, highlightthickness=1,
            padx=6, pady=4,
        )
        tpl_scroll = ttk.Scrollbar(tpl_frame, orient="horizontal", command=self.tpl_text.xview)
        self.tpl_text.configure(xscrollcommand=tpl_scroll.set)
        self.tpl_text.insert("1.0", self.app_config.api.request_template)
        self.tpl_text.pack(fill="x")
        tpl_scroll.pack(fill="x")

        tk.Label(
            tpl_frame,
            text="Placeholders:  {{prompt}}  {{system_prompt}}  {{model}}",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(3, 0))
        row += 1

        # ── Response Path + HTTP Method ───────────────────────────────────────
        tk.Label(
            form, text="Response Path", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD,
        ).grid(row=row, column=0, sticky="w", pady=(10, 0), padx=(0, 12))

        resp_frame = tk.Frame(form, bg=COLOR_BG_CARD)
        resp_frame.grid(row=row, column=1, sticky="ew", pady=(10, 0))
        resp_frame.columnconfigure(0, weight=1)

        resp_inner = tk.Frame(resp_frame, bg=COLOR_BG_CARD)
        resp_inner.pack(fill="x")

        self.resp_path_var = tk.StringVar(value=self.app_config.api.response_path)
        ttk.Entry(resp_inner, textvariable=self.resp_path_var, font=FONT_CODE, width=34).pack(side="left", padx=(0, 16))

        tk.Label(resp_inner, text="HTTP Method:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY).pack(side="left", padx=(0, 6))
        self.method_var = tk.StringVar(value=self.app_config.api.http_method or "POST")
        method_combo = ttk.Combobox(
            resp_inner, textvariable=self.method_var,
            values=["POST", "GET", "PUT", "PATCH"],
            state="readonly", width=7,
        )
        method_combo.pack(side="left")

        tk.Label(
            resp_frame,
            text="Dot-notation path into response JSON  (e.g.  choices.0.message.content  or  data.reply)",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(3, 0))
        row += 1

        # ── Test Connection ───────────────────────────────────────────────────
        conn_row = tk.Frame(card, bg=COLOR_BG_CARD)
        conn_row.pack(fill="x", pady=(14, 0))

        self.btn_test = ttk.Button(
            conn_row, text="⚡  Test Connection", style="Accent.TButton",
            command=self._on_test_connection,
        )
        self.btn_test.pack(side="left", padx=(0, 12))

        self.lbl_conn_status = tk.Label(
            conn_row, text="", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY_BOLD,
        )
        self.lbl_conn_status.pack(side="left", fill="x", expand=True)

        # Sync auth preset button highlight on init
        self._highlight_auth_preset(self.app_config.api.auth_preset)

    # ── Section 2: Provider Preset (collapsible) ──────────────────────────────

    def _build_preset_section(self, parent: tk.Widget) -> None:
        self._preset_collapsed = True

        header_frame = tk.Frame(parent, bg=COLOR_BG_DARK, cursor="hand2")
        header_frame.pack(fill="x", pady=(0, 2))

        self._preset_toggle_lbl = tk.Label(
            header_frame,
            text="▶  Use Provider / Platform Preset  (auto-fills endpoint + template)",
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED, font=FONT_BODY_BOLD,
            cursor="hand2",
        )
        self._preset_toggle_lbl.pack(side="left", padx=(2, 0))
        header_frame.bind("<Button-1>", self._toggle_preset_section)
        self._preset_toggle_lbl.bind("<Button-1>", self._toggle_preset_section)

        self._preset_card = CardFrame(parent)
        # Don't pack yet (collapsed)

        tk.Label(
            self._preset_card,
            text="Select a preset to instantly populate the endpoint, request template, response path, and auth scheme above.",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY, wraplength=760,
        ).pack(anchor="w", pady=(0, 10))

        preset_row = tk.Frame(self._preset_card, bg=COLOR_BG_CARD)
        preset_row.pack(fill="x")

        tk.Label(preset_row, text="Preset:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD).pack(side="left", padx=(0, 8))

        self.preset_var = tk.StringVar(value=_PRESET_LABELS[-1])
        self.preset_combo = ttk.Combobox(
            preset_row, textvariable=self.preset_var,
            values=_PRESET_LABELS, state="readonly", width=52,
        )
        self.preset_combo.pack(side="left", padx=(0, 10))

        ttk.Button(
            preset_row, text="Apply Preset →", style="Accent.TButton",
            command=self._on_apply_preset,
        ).pack(side="left")

        warning = tk.Frame(self._preset_card, bg="#1C1917", padx=10, pady=6)
        warning.pack(fill="x", pady=(10, 0))
        tk.Label(
            warning,
            text="⚠  Applying a preset overwrites the Endpoint URL, Request Template, Response Path and Auth scheme — your custom values will be replaced.",
            bg="#1C1917", fg="#FCD34D", font=FONT_BODY, wraplength=760, justify="left",
        ).pack(anchor="w")

    def _toggle_preset_section(self, event=None) -> None:
        self._preset_collapsed = not self._preset_collapsed
        if self._preset_collapsed:
            self._preset_card.pack_forget()
            self._preset_toggle_lbl.config(
                text="▶  Use Provider / Platform Preset  (auto-fills endpoint + template)"
            )
        else:
            self._preset_card.pack(fill="x", pady=(0, 4))
            self._preset_toggle_lbl.config(
                text="▼  Use Provider / Platform Preset  (auto-fills endpoint + template)"
            )

    def _on_apply_preset(self) -> None:
        label = self.preset_var.get()
        for p in PROVIDER_PRESETS:
            if p[0] == label:
                (_, ptype, base_url, model, req_tpl, resp_path,
                 auth_preset, auth_hdr, auth_val_tpl) = p

                self.endpoint_var.set(base_url)
                self.tpl_text.delete("1.0", "end")
                self.tpl_text.insert("1.0", req_tpl)
                self.resp_path_var.set(resp_path)
                self.auth_header_var.set(auth_hdr)
                self.auth_value_var.set(auth_val_tpl)
                self._highlight_auth_preset(auth_preset)

                # Update model/provider metadata silently
                self.app_config.api.model = model
                self.app_config.api.provider = ptype

                self._notify_change()
                self.lbl_conn_status.config(
                    text=f"Preset applied — enter your API key and click 'Test Connection'",
                    fg=COLOR_ACCENT,
                )
                break

    # ── Section 3: Advanced Parameters (collapsible) ──────────────────────────

    def _build_advanced_section(self, parent: tk.Widget) -> None:
        self._adv_collapsed = True

        header_frame = tk.Frame(parent, bg=COLOR_BG_DARK, cursor="hand2")
        header_frame.pack(fill="x", pady=(0, 2))

        self._adv_toggle_lbl = tk.Label(
            header_frame,
            text="▶  Advanced Parameters  (system prompt, temperature, tokens, timeout, custom headers)",
            bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED, font=FONT_BODY_BOLD,
            cursor="hand2",
        )
        self._adv_toggle_lbl.pack(side="left", padx=(2, 0))
        header_frame.bind("<Button-1>", self._toggle_advanced_section)
        self._adv_toggle_lbl.bind("<Button-1>", self._toggle_advanced_section)

        self._adv_card = CardFrame(parent)
        # Don't pack yet (collapsed)

        # System Prompt
        tk.Label(
            self._adv_card, text="System Prompt",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD,
        ).pack(anchor="w", pady=(0, 2))
        self.sys_text = tk.Text(
            self._adv_card,
            height=3,
            bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="flat", wrap="word", font=FONT_BODY,
            highlightbackground=COLOR_BORDER, highlightthickness=1,
            padx=6, pady=4,
        )
        self.sys_text.insert("1.0", self.app_config.api.system_prompt or "")
        self.sys_text.pack(fill="x", pady=(0, 10))

        # Temperature / Max Tokens / Timeout
        params_row = tk.Frame(self._adv_card, bg=COLOR_BG_CARD)
        params_row.pack(fill="x", pady=(0, 10))

        tk.Label(params_row, text="Temperature:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY).pack(side="left", padx=(0, 4))
        self.temp_var = tk.DoubleVar(value=self.app_config.api.temperature)
        ttk.Spinbox(params_row, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var, width=5).pack(side="left", padx=(0, 16))

        tk.Label(params_row, text="Max Tokens:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY).pack(side="left", padx=(0, 4))
        self.max_tokens_var = tk.IntVar(value=self.app_config.api.max_tokens)
        ttk.Spinbox(params_row, from_=16, to=4096, increment=64, textvariable=self.max_tokens_var, width=6).pack(side="left", padx=(0, 16))

        tk.Label(params_row, text="Timeout (s):", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY).pack(side="left", padx=(0, 4))
        self.timeout_var = tk.DoubleVar(value=self.app_config.api.timeout_seconds)
        ttk.Spinbox(params_row, from_=5.0, to=300.0, increment=5.0, textvariable=self.timeout_var, width=5).pack(side="left")

        # Custom Headers
        tk.Label(
            self._adv_card, text="Custom Headers  (one per line,  Header-Name: value)",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY,
        ).pack(anchor="w", pady=(4, 2))
        self.custom_headers_text = tk.Text(
            self._adv_card,
            height=3,
            bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            relief="flat", wrap="none", font=FONT_CODE,
            highlightbackground=COLOR_BORDER, highlightthickness=1,
            padx=6, pady=4,
        )
        existing_headers = "\n".join(
            f"{k}: {v}" for k, v in (self.app_config.api.custom_headers or {}).items()
        )
        self.custom_headers_text.insert("1.0", existing_headers)
        self.custom_headers_text.pack(fill="x")

    def _toggle_advanced_section(self, event=None) -> None:
        self._adv_collapsed = not self._adv_collapsed
        if self._adv_collapsed:
            self._adv_card.pack_forget()
            self._adv_toggle_lbl.config(
                text="▶  Advanced Parameters  (system prompt, temperature, tokens, timeout, custom headers)"
            )
        else:
            self._adv_card.pack(fill="x", pady=(0, 4))
            self._adv_toggle_lbl.config(
                text="▼  Advanced Parameters  (system prompt, temperature, tokens, timeout, custom headers)"
            )

    # ── Section 4: Local Evaluator ────────────────────────────────────────────

    def _build_evaluator_card(self, parent: tk.Widget) -> None:
        card = CardFrame(parent)
        card.pack(fill="x", pady=(12, 16))

        tk.Label(
            card, text="Local Evaluator Status",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_TITLE,
        ).pack(anchor="w", pady=(0, 4))
        tk.Label(
            card,
            text="Hugging Face classifier running 100% locally. Never calls cloud judging LLMs.",
            bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY,
        ).pack(anchor="w", pady=(0, 12))

        model_row = tk.Frame(card, bg=COLOR_BG_CARD)
        model_row.pack(fill="x", pady=(0, 8))
        tk.Label(model_row, text="Active Backend:", bg=COLOR_BG_CARD, fg=COLOR_TEXT_PRIMARY, font=FONT_BODY_BOLD).pack(side="left", padx=(0, 10))
        self.lbl_backend_name = tk.Label(
            model_row, text=self.classifier.model_name,
            bg=COLOR_BG_INPUT, fg=COLOR_ACCENT, font=FONT_CODE, padx=8, pady=3,
        )
        self.lbl_backend_name.pack(side="left")

        self.status_box = tk.Frame(card, bg=COLOR_BG_INPUT, padx=12, pady=10)
        self.status_box.pack(fill="x", pady=(4, 10))
        self.lbl_eval_status = tk.Label(
            self.status_box,
            text="Checking local model status...",
            bg=COLOR_BG_INPUT, fg=COLOR_TEXT_PRIMARY, font=FONT_CODE,
            justify="left", anchor="w",
        )
        self.lbl_eval_status.pack(fill="x")

        btn_row = tk.Frame(card, bg=COLOR_BG_CARD)
        btn_row.pack(fill="x")
        self.btn_download = ttk.Button(
            btn_row, text="Download / Load Model", style="TButton",
            command=self._on_download_model,
        )
        self.btn_download.pack(side="left", padx=(0, 10))
        self.lbl_download_progress = tk.Label(btn_row, text="", bg=COLOR_BG_CARD, fg=COLOR_TEXT_MUTED, font=FONT_BODY)
        self.lbl_download_progress.pack(side="left")

    # ── Auth preset helpers ───────────────────────────────────────────────────

    def _apply_auth_preset(self, preset: str) -> None:
        hdr, val_tpl = AUTH_PRESET_DEFAULTS[preset]
        self.auth_header_var.set(hdr)
        self.auth_value_var.set(val_tpl)
        self._highlight_auth_preset(preset)

    def _highlight_auth_preset(self, preset: str) -> None:
        """Update button styles to reflect the currently active auth preset."""
        for p, btn in self._auth_preset_btns.items():
            if p == preset:
                btn.configure(style="Accent.TButton")
            else:
                btn.configure(style="TButton")

    # ── Evaluator callbacks ───────────────────────────────────────────────────

    def refresh_evaluator_status(self) -> None:
        status = self.classifier.get_status()
        device_str = status.device

        # Update backend label dynamically (it may change after load)
        if hasattr(self, "lbl_backend_name"):
            self.lbl_backend_name.config(text=self.classifier.model_name)

        if status.is_loaded:
            status_text = f"Evaluator: Active\n✓ {status.model_name}\n✓ Loaded into memory (local files)\nDevice: {device_str}"
            fg_color = COLOR_SAFE
            self.btn_download.config(text="✓ Model Active", state="disabled")
        elif status.is_installed:
            status_text = f"Evaluator: Ready\n✓ {status.model_name}\n✓ Model available locally — not yet loaded into memory\nDevice: {device_str}"
            fg_color = COLOR_SAFE
            self.btn_download.config(text="Load Model into Memory", state="normal")
        else:
            status_text = (
                f"Evaluator: Not Found\n"
                f"✗ Model not found. Click 'Download Model' to fetch from Hugging Face.\n"
                f"Device: {device_str} (will use heuristic fallback until downloaded)"
            )
            fg_color = COLOR_SUSPECT
            self.btn_download.config(text="Download Model", state="normal")
        self.lbl_eval_status.config(text=status_text, fg=fg_color)

    def _on_download_model(self) -> None:
        self.btn_download.config(state="disabled")
        self.lbl_download_progress.config(text="Starting download in background...", fg=COLOR_ACCENT)

        def worker():
            def cb(msg: str):
                self.after(0, lambda: self.lbl_download_progress.config(text=msg))
            success = self.classifier.download_model(status_callback=cb)
            self.after(0, lambda: self._on_download_finished(success))

        threading.Thread(target=worker, daemon=True).start()

    def _on_download_finished(self, success: bool) -> None:
        self.btn_download.config(state="normal")
        self.refresh_evaluator_status()
        if success:
            messagebox.showinfo("Success", "Evaluator model downloaded and ready for local inference.")
        else:
            messagebox.showwarning(
                "Notice",
                "Model download did not finish. Evaluator will use deterministic checks and local heuristic fallback.",
            )

    # ── Connection test ───────────────────────────────────────────────────────

    def _on_test_connection(self) -> None:
        self._save_to_config()
        self.btn_test.config(state="disabled")
        self.lbl_conn_status.config(text="Testing connection...", fg=COLOR_ACCENT)

        provider = create_provider(self.app_config.api)

        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(provider.test_connection())
            finally:
                loop.close()
            self.after(0, lambda: self._handle_test_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_test_result(self, result) -> None:
        self.btn_test.config(state="normal")
        if result.success:
            self.lbl_conn_status.config(
                text=f"✓ Connected  |  Latency: {result.latency_ms} ms  |  Reply: {result.details.get('sample_reply', '')[:60]}",
                fg=COLOR_SAFE,
            )
        else:
            self.lbl_conn_status.config(
                text=f"✗ {result.message[:100]}",
                fg=COLOR_BROKEN,
            )

    # ── Persist & notify ──────────────────────────────────────────────────────

    def _save_to_config(self) -> None:
        api = self.app_config.api
        api.endpoint_url = self.endpoint_var.get().strip()
        api.api_key = self.key_entry.get().strip()
        api.auth_header_name = self.auth_header_var.get().strip()
        api.auth_value_template = self.auth_value_var.get().strip()
        api.request_template = self.tpl_text.get("1.0", "end-1c").strip()
        api.response_path = self.resp_path_var.get().strip()
        api.http_method = self.method_var.get().strip()
        api.system_prompt = self.sys_text.get("1.0", "end-1c")

        # Parse custom headers
        raw_headers = self.custom_headers_text.get("1.0", "end-1c").strip()
        custom_headers: dict[str, str] = {}
        for line in raw_headers.splitlines():
            if ":" in line:
                hname, _, hval = line.partition(":")
                custom_headers[hname.strip()] = hval.strip()
        api.custom_headers = custom_headers

        try:
            api.temperature = float(self.temp_var.get())
            api.max_tokens = int(self.max_tokens_var.get())
            api.timeout_seconds = float(self.timeout_var.get())
        except Exception:
            pass

    def _notify_change(self) -> None:
        self._save_to_config()
        if self.on_config_changed:
            self.on_config_changed(self.app_config)
