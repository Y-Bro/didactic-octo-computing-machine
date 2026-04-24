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
- The gcloud CLI for Application Default Credentials
- A Gemini API key (default) and/or an Anthropic API key

## Setup

1. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install (on macOS: `brew install --cask google-cloud-sdk`).
2. In Google Cloud Console (https://console.cloud.google.com), create or select a project and enable the **Google Sheets API** and **Google Drive API**.
3. Authenticate locally with the Sheets + Drive scopes:
   ```bash
   gcloud auth application-default login --scopes='https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file,openid'
   gcloud config set project YOUR_PROJECT_ID
   ```
   A browser opens for consent; credentials are stored at `~/.config/gcloud/application_default_credentials.json`.
4. Copy `.env.example` to `.env` and set your `GEMINI_API_KEY` (and/or `ANTHROPIC_API_KEY`). Optional: set `GEMINI_MODEL` / `ANTHROPIC_MODEL` to override the default model.
5. Install Python deps:
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

Sheets created by the CLI will land in your own Drive and appear on drive.google.com.

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
