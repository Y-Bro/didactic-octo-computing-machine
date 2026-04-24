# SoW Project Planner Agent

A Python CLI that reads a Statement of Work (PDF or DOCX) and produces a structured project plan in a new Google Sheet. An agentic tool-use loop (Gemini 2.0 Flash by default, Claude Sonnet 4.6 optional) extracts deliverables, estimates timelines for a single senior developer (3 YoE), and flags anything it cannot trace back to the SoW.

## Features

- **PDF and DOCX input** via `pymupdf` and `python-docx`.
- **Architecture-diagram analysis** via a vision tool call that extracts components, integrations, and system boundaries.
- **Grounding enforcement** — every deliverable must carry a verbatim `source_quote` from the SoW; ambiguous items go into a separate "Gaps" tab instead of being hallucinated.
- **Provider toggle** — `--llm gemini` (default) or `--llm claude`; both implement a common `LLMProvider` interface.
- **Template-driven output** — the columns of your CSV template determine the columns of the output Google Sheet.

## Requirements

- Python 3.11+
- A Google Cloud project with the Google Sheets API and Google Drive API enabled
- An OAuth 2.0 client secret (Desktop app type) from Google Cloud Console
- A Gemini API key (default) and/or an Anthropic API key

## Setup

1. Clone the repo and `cd` into it.
2. Create and activate a virtualenv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in credentials:
   ```bash
   cp .env.example .env
   # edit .env
   ```
   Required variables:
   - `GEMINI_API_KEY` — only if using `--llm gemini`
   - `ANTHROPIC_API_KEY` — only if using `--llm claude`
   - `GOOGLE_APPLICATION_CREDENTIALS` — path to your OAuth client secret JSON (default: `credentials.json` in the project root)
   - `GEMINI_MODEL` / `ANTHROPIC_MODEL` — optional model overrides (e.g. `gemini-2.0-pro`); the `--model` CLI flag takes precedence over these env vars, and both fall back to each provider's built-in default if unset.
5. Set up Google OAuth credentials:
   1. Go to [Google Cloud Console](https://console.cloud.google.com) and create or select a project.
   2. Enable the **Google Sheets API** and **Google Drive API**.
   3. Configure the OAuth consent screen: External → add your email as a test user.
   4. Go to **Credentials → Create Credentials → OAuth client ID**, set Application type to **Desktop app**, download the JSON, and save it as `credentials.json` at the project root.
   5. Run normally — the first run opens a browser to approve access; the token is cached in `.oauth_token.json` for subsequent runs.

## Usage

```bash
python main.py \
  --sow path/to/statement-of-work.pdf \
  --template path/to/template.csv \
  --llm gemini \
  --credentials credentials.json \
  --title "My Project Plan"
```

### CLI flags

| Flag | Required | Default | Description |
|---|---|---|---|
| `--sow` | yes | — | Path to SoW file (`.pdf` or `.docx`) |
| `--template` | yes | — | Path to CSV template defining output columns |
| `--llm` | no | `gemini` | LLM provider (`gemini` or `claude`) |
| `--model` | no | provider default | Override model name. Also reads $GEMINI_MODEL / $ANTHROPIC_MODEL. |
| `--credentials` | no | `$GOOGLE_APPLICATION_CREDENTIALS` if set, else `credentials.json` | Path to OAuth client secret JSON |
| `--token-cache` | no | `.oauth_token.json` | Path where OAuth token is cached between runs |
| `--title` | no | `Project Plan` | Title of the output Google Sheet |
| `--verbose` | no | (off) | Enable DEBUG-level logging on the agent loop |

### Template CSV format

The first row is the header — its columns become the columns of the output sheet. Any subsequent rows are treated as examples shown to the agent. A minimal template:

```csv
Phase,Milestone,Deliverable,Start Date,End Date,Estimated Days,Notes
Build,API,REST API,2026-05-01,2026-05-10,7,Example row
```

### Output

On success the CLI prints a structured **Run Summary**:

```
==================================================
Run Summary
==================================================
Model:      gemini
Iterations: 3
Rows:       7
Gaps:       1
Elapsed:    12.4s
Sheet:      https://docs.google.com/spreadsheets/d/...
```

The created Google Sheet contains:
- a **Project Plan** tab — one row per deliverable, columns matching the template
- a **Gaps** tab (only if gaps were flagged) — reason + location per ambiguous item

## Tests

```bash
pytest tests/
```

## Project layout

```
agent/
  providers/      LLM provider base + Gemini + Claude implementations
  prompt.py       System prompt builder
  tools.py        Tool schemas and ToolExecutor
  loop.py         Agentic reasoning loop (provider-agnostic)
parsers/          PDF + DOCX parsers
sheets/writer.py  Google Sheets output
template/reader.py Template CSV reader
main.py           CLI entrypoint
tests/            Unit tests (mocked SDKs)
docs/superpowers/ Design spec and implementation plan
```
