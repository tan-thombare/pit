# Prompt Injection Tester (`pit`)

> A **100% local desktop application** for automated LLM prompt-injection security auditing.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-blueviolet.svg)](https://github.com/astral-sh/uv)
[![Privacy](https://img.shields.io/badge/Privacy-100%25_Local-brightgreen.svg)](#how-it-works)

---

## What is this?

**Prompt Injection Tester (PIT)** is a native desktop application that automatically tests a Large Language Model (LLM) for vulnerabilities to prompt-injection attacks, jailbreaks, data extraction attempts, and other adversarial exploits.

You point it at any LLM API (OpenAI, Anthropic, Ollama, vLLM, or any HTTP endpoint), click **Run**, and it fires a curated suite of attack prompts at the target model. Every response is evaluated **locally on your machine** — no data is ever sent to a cloud judging service.

---

## How It Works

For each attack in the suite, PIT:

1. Sends the attack prompt to your configured target LLM API.
2. Captures the full response.
3. **Locally evaluates** the response using:
   - A local [`protectai/deberta-v3-base-prompt-injection-v2`](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) neural classifier (running on your CPU or GPU).
   - Deterministic rule checks: canary token leakage, forbidden content indicators, refusal keyword matching.
4. Assigns a verdict: **SAFE**, **SUSPECTED BYPASS**, or **SUCCESSFUL INJECTION**.
5. Calculates a risk score (0–100) and overall security score.
6. Displays the full response, signals, reasoning, and latency — all inside the app.

> 🔒 **Zero external telemetry.** The evaluator model runs entirely locally. Your LLM's responses never leave your machine to be judged by a third-party service.

---

## Installation

Requires **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/your-username/prompt-injection-tester.git
cd prompt-injection-tester
uv sync
```

---

## Running the App

```bash
uv run pit
```

**First run:** A splash screen appears while the local DeBERTa evaluator model loads into memory from the bundled files. This takes 20–60 seconds the first time, after which the OS caches the model pages and subsequent starts are fast.

**Every run after that:** The splash appears briefly and the app opens within a few seconds.

---

## The Interface

The app has three tabs:

### Tab 1 — ⚙️ Target & Evaluator

Configure the LLM you want to test:

| Field | Description |
|---|---|
| **Provider preset** | Pick from OpenAI, Anthropic, OpenAI-Compatible, Azure, Bedrock, Gemini, or Generic HTTP |
| **Endpoint URL** | Base URL of the target API (e.g. `http://localhost:11434/v1` for Ollama) |
| **API Key** | Your API key (masked; reveal button available) |
| **Model** | Model name e.g. `gpt-4o-mini`, `llama3`, `claude-3-5-haiku-20241022` |
| **Test Connection** | Sends a quick ping to verify the endpoint responds correctly |

**Advanced Parameters** (collapsible section):
- System prompt, temperature, max tokens, timeout, custom HTTP headers
- Full request JSON template and response extraction path for Generic HTTP providers

**Local Evaluator Status** (bottom of this tab):
- Shows whether the DeBERTa classifier is loaded into memory and which device (CPU/CUDA) it is using.
- If the model somehow isn't loaded, a **Load Model** button is available here — but normally the startup splash handles this automatically.

---

### Tab 2 — 🎯 Attack Suite

Select and run attacks against your target:

- **Search** attacks by keyword (searches ID, name, description, and prompt text).
- **Filter by Category** — e.g. Instruction Override, Jailbreak, System Prompt Extraction, Role Manipulation, etc.
- **Filter by Severity** — Critical, High, Medium, Low.
- **Select All / Deselect All** to quickly pick a subset.
- Individual checkbox toggle per attack row.

Once you've chosen your attacks:

1. Click **▶ RUN SECURITY TEST** — the test runner sends attacks to your target API one by one.
2. A live progress bar and status line show the current attack and running verdict.
3. Click **⏹ Stop Test** at any time to abort the run.

When the suite completes, the app automatically switches to the Results tab.

---

### Tab 3 — 📊 Security Results

After a run completes, view:

| Metric | What it means |
|---|---|
| **Security Score** | 0–100 overall rating. 100 = model resisted all attacks. Each successful injection reduces the score. |
| **Tests Executed** | Total number of attacks that ran |
| **Safe (Resisted)** | Attacks the model correctly refused |
| **Suspected Bypass** | Responses that look suspicious but weren't fully confirmed as injections |
| **Successful Injection** | Attacks where the model clearly followed the injected instruction |
| **Errors** | API errors or timeouts during the run |

**Results Table:** Click any row to see the full details panel below:
- The exact attack prompt sent
- The model's raw response
- All evaluation signals (canary token check, forbidden content, refusal keywords, classifier score)
- Reasoning and confidence
- Latency in milliseconds

**Export:**
- **Export JSON** — Full structured report with all metadata.
- **Export CSV** — Flat table for spreadsheet analysis.

---

## Supported Providers

| Provider | Notes |
|---|---|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-turbo, etc. |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.5 Haiku, etc. |
| **OpenAI-Compatible** | Ollama, vLLM, LM Studio, Groq, OpenRouter — any `/v1/chat/completions` endpoint |
| **Azure OpenAI** | Azure-hosted OpenAI deployments |
| **Google Gemini** | Gemini REST API via `v1beta` |
| **Generic HTTP** | Any LLM API with a configurable request template and response extraction path |

---

## Attack Suite

The built-in suite covers a wide range of adversarial techniques across categories such as:

- Direct instruction override
- System prompt extraction and leaking
- Role manipulation and persona subversion
- Jailbreaks (hypothetical, roleplay, fictional framing)
- Context boundary injection
- Delimiter and markdown injection
- Base64 / encoding obfuscation
- Multi-turn history fabrication
- Authority impersonation
- Indirect instruction attacks
- Data exfiltration attempts
- And many more...

You can also supply a **custom attack suite** by loading your own JSON file that follows the same schema.

---

## Project Structure

```
src/pit/
├── attacks/          # Attack models, built-in suite, filtering
├── config/           # App configuration (persisted to ~/.pit_config.json)
├── evaluator/        # Local DeBERTa classifier + deterministic signal analysis
│   └── bundled_model/  # Pre-bundled model weights (loaded at startup)
├── providers/        # LLM API provider adapters
├── runner/           # Test execution engine (threaded)
├── storage/          # Result models, JSON/CSV export
└── ui/               # Tkinter desktop GUI
    ├── app.py          # Main window, tab assembly
    ├── splash.py       # Startup model-loading screen
    ├── config_view.py  # Tab 1: API configuration
    ├── test_view.py    # Tab 2: Attack selection & execution
    └── results_view.py # Tab 3: Results dashboard
```

---

## Running Tests

```bash
.venv\Scripts\python.exe -m pytest
```
