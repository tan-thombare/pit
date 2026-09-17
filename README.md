# Prompt Injection Tester (`pit`)

> A **100% local desktop application** for automated prompt-injection and security vulnerability testing of **AI Applications, Chatbots, and APIs**.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-blueviolet.svg)](https://github.com/astral-sh/uv)
[![Target](https://img.shields.io/badge/Target-Any_AI_Application_API-orange.svg)](#testing-your-custom-ai-application)
[![Privacy](https://img.shields.io/badge/Privacy-100%25_Local_Evaluation-brightgreen.svg)](#how-it-works)

---

## What is PIT?

**Prompt Injection Tester (PIT)** is a native desktop security tool designed specifically to audit **your AI applications** against prompt injections, jailbreaks, system prompt extraction, context manipulation, and adversarial exploits.

### Built for AI Applications, Not Just Raw Foundation Models

Most security testing tools focus purely on testing raw foundation LLM APIs (like standard OpenAI or Anthropic completion endpoints). But in the real world:
- Vulnerabilities emerge in **your application layer** — inside your custom system prompts, RAG retrieval pipelines, agentic tools, customer support bots, and middleware business logic.
- Testing a raw model in isolation doesn't reflect how *your* application behaves when an attacker tries to jailbreak your assistant or exfiltrate private context.

**PIT puts your custom AI application front and center.** You simply provide your application's REST / HTTP endpoint, configure your JSON payload and authentication headers, specify which response field contains the output, and PIT will fire a comprehensive, automated suite of adversarial attacks against your live system.

> 💡 **Direct model providers are optional presets:** If you *do* want to benchmark a raw LLM gateway directly (such as OpenAI, Anthropic, Ollama, Bedrock, Azure, or Gemini), PIT includes one-click presets that auto-fill the request format for you.

---

## Key Features

- 🎯 **Test Any AI Application Endpoint:** Plugs into any REST/HTTP API — whether it's a FastAPI/Flask/Express backend, an internal corporate copilot, a customer-facing chatbot, or a multi-agent workflow.
- 🔧 **Custom Request & Auth Mapping:** Fully customizable JSON payload template (`{"query": "{{prompt}}"}`), authentication schemes (Bearer Token, API Key Header, or arbitrary custom headers), and HTTP methods (`POST`, `GET`, `PUT`, `PATCH`).
- 🔍 **Flexible Response Extraction:** Dot-notation JSON path parser (e.g. `response`, `data.reply`, `choices.0.message.content`) extracts replies from any nested response structure.
- 🔒 **100% Local Response Evaluation:** Zero cloud telemetry or third-party judging services. Every response is analyzed entirely on your machine using a local neural classifier model ([`protectai/deberta-v3-base-prompt-injection-v2`](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)) combined with deterministic canary checks and refusal pattern matching.
- ⚡ **Curated Multi-Vector Attack Suite:** 50+ adversarial attacks spanning direct instruction overrides, system prompt extraction, jailbreaks, role manipulation, encoding obfuscation, and context leakage.
- 📊 **Interactive Security Dashboard:** Live attack execution, risk scoring (0–100), per-attack signal inspection, response latency metrics, and instant JSON/CSV report export.
- 🎛️ **Optional Provider Presets:** Fast shortcuts to auto-fill configurations for OpenAI, Anthropic, Ollama, vLLM, Azure OpenAI, AWS Bedrock, and Google Gemini.

---

## How It Works

```
┌─────────────────────────────────────────┐
│         Prompt Injection Tester         │
└───────────────────┬─────────────────────┘
                    │ 1. Sends curated attack prompt in your custom payload
                    ▼
┌─────────────────────────────────────────┐
│     YOUR CUSTOM AI APPLICATION API      │
│  (Chatbot, RAG pipeline, Internal Bot)  │
└───────────────────┬─────────────────────┘
                    │ 2. Returns application response
                    ▼
┌─────────────────────────────────────────┐
│     100% LOCAL EVALUATION ENGINE        │
│  • Local DeBERTa-v3 Neural Classifier   │
│  • Deterministic Canary & Token Checks  │
│  • Refusal Keyword & Behavioral Signals │
└───────────────────┬─────────────────────┘
                    │ 3. Assigns verdict & computes score
                    ▼
┌─────────────────────────────────────────┐
│       SECURITY REPORT & DASHBOARD       │
│  SAFE  |  SUSPECTED BYPASS  |  INJECTION│
└─────────────────────────────────────────┘
```

For each attack in the suite, PIT:
1. Formats the attack prompt into your application's custom JSON request template and sends it via HTTP.
2. Extracts the response text using your specified response path.
3. **Locally evaluates** the response on your machine:
   - Evaluates the output using the local DeBERTa-v3 prompt injection classifier (running on CPU or GPU).
   - Runs deterministic rule checks: canary token leakage, forbidden content indicators, and refusal phrase matching.
4. Assigns a definitive verdict: **SAFE**, **SUSPECTED BYPASS**, or **SUCCESSFUL INJECTION**.
5. Computes a 0–100 security score and generates an interactive audit breakdown.

> 🔒 **Privacy Guarantee:** Target application responses are **never** forwarded to an external judge or cloud LLM. Everything stays strictly on your local machine.

---

## Testing Your Custom AI Application

PIT makes it straightforward to hook into any custom AI endpoint. In **Tab 1 (Target & Evaluator)**, configure the following:

### 1. Endpoint URL & HTTP Method
Enter the full URL where your AI application accepts requests:
```text
https://api.your-company.com/v1/assistant
http://localhost:8000/chat
http://127.0.0.1:5000/api/generate
```
Select the appropriate HTTP method (`POST`, `GET`, `PUT`, or `PATCH`).

### 2. Authentication Scheme
Choose how your API expects authentication credentials:
- **Bearer Token:** Sends `Authorization: Bearer <your-api-key>`
- **API Key Header:** Sends `x-api-key: <your-api-key>`
- **Custom Header:** Define any custom header name and template (e.g. `Header: Authorization`, `Template: Token {{api_key}}` or `Header: X-Corp-Auth`)
- Or leave blank for unauthenticated / internal endpoints.

### 3. Request Body Template
Customize the JSON payload sent to your application. Use the `{{prompt}}` placeholder where the attack prompt should be inserted:

#### Example: Simple Chatbot Endpoint
If your backend expects `{"message": "user text"}`:
```json
{
  "message": "{{prompt}}"
}
```

#### Example: RAG / Q&A Service with Metadata
If your API expects context or session parameters:
```json
{
  "query": "{{prompt}}",
  "session_id": "pit-security-audit",
  "filters": {
    "collection": "customer_support_docs"
  }
}
```

#### Example: Multi-turn / OpenAI-Style Custom Backend
If your application uses a messages array:
```json
{
  "messages": [
    {"role": "system", "content": "{{system_prompt}}"},
    {"role": "user", "content": "{{prompt}}"}
  ],
  "temperature": 0.0
}
```

*Supported Placeholders:*
- `{{prompt}}`: The adversarial attack text (automatically escaped for valid JSON).
- `{{system_prompt}}`: The optional system prompt configured in Advanced Parameters.
- `{{model}}`: Optional model identifier if your API expects one.

### 4. Response Path (Dot Notation)
Tell PIT where to find the generated assistant text in your API's JSON response:
- Single-level field: `response`, `reply`, or `answer`
- Nested field: `data.reply` or `result.output.text`
- Array element indexing: `choices.0.message.content` or `candidates.0.content.parts.0.text`
- If left empty, PIT uses the raw response body.

### 5. Custom HTTP Headers & Advanced Settings
Under **Advanced Parameters**, you can specify:
- Custom HTTP headers (e.g. `X-Tenant-ID: staging`, `User-Agent: SecurityScanner/1.0`).
- Custom system prompt hint, request timeout (seconds), temperature, and max tokens.

### 6. Test Connection
Click **⚡ Test Connection** to fire a harmless ping probe and confirm your endpoint and response path are configured properly before running the full test suite.

---

## Optional Provider Presets

If you want to test foundation models directly rather than an application endpoint, click **Show Presets** to automatically configure endpoints, templates, and response paths for:

| Preset | Target Type | Default Endpoint |
|---|---|---|
| **Custom AI Application** | Any custom chatbot, RAG, or internal API | *(User provided)* |
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-turbo | `https://api.openai.com/v1` |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.5 Haiku | `https://api.anthropic.com/v1` |
| **OpenAI-Compatible** | Ollama, vLLM, LM Studio, Groq, OpenRouter | `http://localhost:11434/v1` |
| **Azure OpenAI** | Azure-hosted model deployments | Azure deployment endpoint |
| **AWS Bedrock** | Claude / Titan via Bedrock Runtime | Bedrock InvokeModel endpoint |
| **Google Gemini** | Gemini 1.5 Flash / Pro via REST API | Google Gemini v1beta endpoint |

---

## Installation

Requires **Python 3.12+** and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/tan-thombare/pit.git
cd pit
uv sync
```

---

## Running the App

Launch the application:

```bash
uv run pit
```

### Startup Behavior
- **First run:** A splash screen will display while the bundled local DeBERTa neural classifier is loaded into memory. This takes ~20–60 seconds on the first run.
- **Subsequent runs:** The operating system caches the model in memory; the splash screen completes in a few seconds.

---

## The Interface

The application features three main tabs:

### Tab 1 — 🎯 Target AI Application & Evaluator
- Configure your application's **Endpoint URL**, **Authentication**, **Request Template**, and **Response Path**.
- Quick-toggle between **Bearer Token**, **API Key Header**, or **Custom Auth**.
- Optional collapsible **Provider Presets** to quickly populate fields for direct LLM testing.
- Collapsible **Advanced Parameters** for custom HTTP headers, timeout, temperature, and system prompt.
- Live **Local Evaluator Status** displaying model readiness and hardware device (`cpu` / `cuda`).
- **⚡ Test Connection** button with live feedback.

### Tab 2 — 🎯 Attack Suite
- **Search:** Search across attack names, IDs, descriptions, and prompt text.
- **Category Filter:** Filter attacks by specific vulnerability types:
  - Direct Instruction Overrides
  - System Prompt Extraction & Leaks
  - Jailbreaks (Roleplay, Fictional framing, Hypotheticals)
  - Role Manipulation & Persona Subversion
  - Delimiter & Context Boundary Injections
  - Base64 & Obfuscation Attacks
  - Multi-turn & History Fabrication
  - Indirect Injections & Exfiltration
- **Severity Filter:** Critical, High, Medium, Low.
- **Selection Controls:** Select All / Deselect All, or toggle individual attacks.
- **▶ RUN SECURITY TEST:** Executes the selected attacks asynchronously with a live progress bar, current attack status, and an abort button (**⏹ Stop Test**).

### Tab 3 — 📊 Security Results & Reports
Once a run completes, view a comprehensive security audit:
- **Security Score (0–100):** Aggregate metric reflecting application resilience.
- **Summary Cards:** Total Tests, Safe (Resisted), Suspected Bypass, Successful Injections, and Errors.
- **Interactive Results Table:** Filter and click any test to inspect:
  - Sent attack prompt
  - Raw application response
  - Signal evaluation (Canary leakage, forbidden content, refusal keyword matches, classifier score)
  - Automated reasoning and confidence rating
  - API response latency (ms)
- **Export Reports:**
  - **Export JSON:** Full structured vulnerability report including all payloads and signals.
  - **Export CSV:** Tabular summary suitable for spreadsheets and compliance documentation.

---

## Attack Suite Coverage

The built-in attack suite tests against realistic adversarial techniques:

- **System Prompt Leaking:** Probes designed to extract system instructions, internal guardrails, and hidden configurations.
- **Instruction Overrides:** Attempts to bypass developer constraints via authority impersonation, command resets, and role reassignment.
- **Jailbreak Variants:** Fictional world framing, academic research pretexts, evil twin / DAN personas, and adversarial logic traps.
- **Format & Delimiter Exploits:** Markdown escapes, fake message delimiters (`---`, `###`, `<system>`), and syntax trickery.
- **Obfuscation & Evasion:** Base64-encoded instructions, leetspeak, reversed text, and cipher-based requests.
- **Data Exfiltration:** Attempts to trick the assistant into embedding secret canary tokens or proprietary information in external links or formats.

You can also load a custom attack suite JSON file adhering to the attack schema.

---

## Project Structure

```
src/pit/
├── attacks/            # Attack models, built-in attack suite (attacks.json), loader
├── config/             # Pydantic configuration models, auth presets, persistence (~/.pit_config.json)
├── evaluator/          # 100% local evaluation pipeline
│   ├── bundled_model/  # Bundled DeBERTa-v3 model files and tokenizer
│   ├── classifier.py   # Local Hugging Face neural classifier
│   ├── deterministic.py# Rule checks: canary token leaks, refusal keywords, forbidden words
│   └── scorer.py       # Verdict logic (SAFE, SUSPECT, BROKEN) and risk scoring
├── providers/          # Target adapters
│   ├── generic.py      # Primary Generic HTTP Provider for custom AI application endpoints
│   ├── openai.py       # OpenAI preset adapter
│   ├── anthropic.py    # Anthropic preset adapter
│   └── base.py         # Provider interface and data structures
├── runner/             # Async/threaded test execution engine
├── storage/            # Results data structures, JSON and CSV exporters
└── ui/                 # Tkinter dark-mode desktop GUI
    ├── app.py          # Main application window & tab navigation
    ├── splash.py       # Startup model-loading splash screen
    ├── config_view.py  # Tab 1: Target AI application & evaluator configuration
    ├── test_view.py    # Tab 2: Attack suite selection & test execution
    ├── results_view.py # Tab 3: Security report & vulnerability dashboard
    ├── styles.py       # Design system, colors, fonts, styles
    └── widgets.py      # Reusable UI cards, tables, and buttons
```

---

## Running Automated Tests

Run the test suite using `pytest`:

```bash
uv run pytest
```

---

## License

Apache 2.0 / MIT (or your preferred license).
