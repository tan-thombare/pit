# Prompt Injection Tester (`pit`)

> Test your AI application for prompt injection vulnerabilities — locally, with no data leaving your machine.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/Package_Manager-uv-blueviolet.svg)](https://github.com/astral-sh/uv)
[![Privacy](https://img.shields.io/badge/Privacy-100%25_Local-brightgreen.svg)](#how-it-works)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is this?

**PIT** is a desktop app that security-tests any AI application by firing prompt injection attacks at its API endpoint and evaluating the responses — entirely on your machine.

If your app exposes an API that accepts user messages and returns AI responses, PIT can test it. It doesn't matter what model or backend powers your app — you just point PIT at your endpoint.

---

## The Core Use Case

You've built an AI application — a chatbot, an assistant, an agent. You want to know: **can an attacker manipulate it?**

PIT sends adversarial prompts to your app's API and checks whether the model followed the injected instruction, leaked the system prompt, or was jailbroken. Everything is evaluated locally using a bundled neural classifier — no cloud judging service involved.

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

```bash
uv run pit
```

A splash screen appears briefly on first launch while the local evaluator model loads. Subsequent starts are fast.

---

## How to Use It

### 1. Configure Your Target API

In the **Target & Evaluator** tab, enter:

- **Endpoint URL** — the API your app exposes (e.g. `https://myapp.com/api/chat`)
- **API Key** — if your endpoint requires authentication
- **Model** — the model identifier your API expects
- **System Prompt** — optional, if you want PIT to send one alongside the attacks

Use **Test Connection** to verify PIT can reach your endpoint before running.

> **Provider presets** (OpenAI, Anthropic, Ollama, etc.) are available as shortcuts if your app is powered by one of those directly. They're optional — if your app has its own API, use Generic HTTP or OpenAI-Compatible mode.

### 2. Select Attacks

In the **Attack Suite** tab, browse and filter the built-in attacks by category and severity. Pick the ones relevant to your app, or just run all of them.

Categories include: instruction override, system prompt extraction, jailbreaks, role manipulation, data exfiltration, encoding obfuscation, and more.

### 3. Run and Review

Click **▶ RUN SECURITY TEST**. PIT sends each attack to your API and evaluates the response. When done, the **Results** tab shows:

- A **Security Score** (0–100) — 100 means your app resisted everything
- Per-attack verdicts: **Safe**, **Suspected Bypass**, or **Successful Injection**
- Full details for each attack: the prompt sent, the response received, evaluation signals, and latency

Export results as **JSON** or **CSV** for reporting.

---

## How Evaluation Works

Every response is evaluated locally using:

- A bundled [`protectai/deberta-v3-base-prompt-injection-v2`](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) neural classifier
- Deterministic checks: canary token leakage, forbidden content, refusal keyword matching

No response data is ever sent to an external service.

---

## Attack Categories

- Direct instruction override
- System prompt extraction
- Jailbreaks (hypothetical, roleplay, fictional framing)
- Role manipulation and persona subversion
- Data exfiltration attempts
- Context boundary and delimiter injection
- Encoding obfuscation (Base64, etc.)
- Authority impersonation
- Multi-turn history fabrication

You can also load a **custom attack suite** from your own JSON file.

---

## Contributing

Contributions are welcome! The two main ways to contribute are:

- **Adding new prompt injection attacks** — expand the built-in library
- **Improving the provider/API layer** — add support for new LLM backends

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidance on both.

---

## License

MIT — see [LICENSE](LICENSE).

