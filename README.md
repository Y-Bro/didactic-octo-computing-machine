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
- A Google Cloud service account with the Google Sheets API enabled
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
   - `GOOGLE_APPLICATION_CREDENTIALS` — path to your Google service-account JSON (default: `credentials.json` in the project root)
5. Place your Google service-account key file at the path pointed to by `GOOGLE_APPLICATION_CREDENTIALS`. Share the target Sheet's parent folder with the service-account email if you want the sheet to land somewhere specific.

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
| `--credentials` | no | `$GOOGLE_APPLICATION_CREDENTIALS` if set, else `credentials.json` | Path to Google service account key |
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
