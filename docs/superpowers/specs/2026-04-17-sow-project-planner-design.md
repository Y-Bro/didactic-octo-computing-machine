# SoW Project Planner — Design Spec

**Date:** 2026-04-17
**Status:** Approved

---

## Overview

An agentic AI system that takes a Statement of Work (SoW) document as input and produces a structured project plan in a new Google Sheet, following a user-provided template. The agent extracts only what is explicitly present in the SoW — it never infers, invents, or assumes deliverables beyond what the document states or clearly implies.

---

## Inputs

| Input | Format | Description |
|-------|--------|-------------|
| SoW document | PDF or DOCX | May contain text, tables, and architecture diagrams |
| Template | `template.csv` | User-provided CSV whose structure (columns, layout, groupings) the output sheet must exactly follow |
| LLM provider | CLI flag | `gemini` (default) or `claude` |

The agent reads the template CSV to understand the full output structure — columns, row groupings, section headers, and layout. The output Google Sheet must mirror this structure exactly, with SoW-derived content populating the appropriate cells.

---

## Output

A new Google Sheet containing:
- **Plan tab:** One row per deliverable, structured per the template columns
- **Gaps tab:** Items flagged as ambiguous or missing from the SoW — never written to the plan tab

---

## Architecture

### Agent Reasoning Loop

The system uses a tool-use agentic loop. The LLM controls sequencing — it decides which tools to call and when based on intermediate results. The host code only runs the loop; it does not hardcode step order.

```
User runs CLI
    ↓
parse_sow runs (outside loop) → produces { text, images[] }
    ↓
Agent receives: SoW text + raw images + template schema + system prompt
    ↓
[Loop]
  Claude/Gemini reasons over content
      → calls analyze_diagram(image) for each diagram image
      → reasons over text + diagram JSON combined
      → calls write_to_sheet or flag_gap per deliverable
      → continues until all SoW content is handled
[End Loop]
    ↓
Output: populated Google Sheet
```

### Grounding Enforcement

The system prompt instructs the agent:
- Every deliverable must include a `source_quote` — verbatim text or diagram description from the SoW that justifies inclusion
- If a `source_quote` cannot be provided, the agent must call `flag_gap` instead of writing the row
- Timeline estimates are based on a single senior developer with 3 years of experience
- Architecture diagram complexity may influence timeline estimates when relevant

---

## Tools

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `parse_sow` | File path | `{ text: str, images: [base64] }` | Extracts text blocks and embedded images from PDF or DOCX |
| `analyze_diagram` | `base64` image | `{ components: [], integrations: [], boundaries: [] }` | Sends image to LLM vision, returns inferred architecture as structured JSON |
| `write_to_sheet` | Plan rows + parsed template structure | Google Sheet URL | Creates a new Google Sheet that exactly mirrors the template layout, populates rows with SoW-derived content |
| `flag_gap` | Reason string, page/section ref | Appended to Gaps tab | Logs ambiguities — called instead of inventing |

---

## LLM Provider Abstraction

A `LLMProvider` base class with two implementations:

```
LLMProvider (abstract)
├── GeminiProvider   — uses Google Generative AI SDK (default)
└── ClaudeProvider   — uses Anthropic SDK
```

Both implement: `reason(messages: list, tools: list) -> ToolCallOrText`

Switched via CLI: `--llm gemini` or `--llm claude`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| LLM (default) | Gemini 2.0 Flash via `google-generativeai` SDK |
| LLM (toggle) | Claude claude-sonnet-4-6 via `anthropic` SDK |
| PDF parsing | `pymupdf` (fitz) |
| DOCX parsing | `python-docx` |
| Google Sheets | `google-api-python-client` |
| Auth | Google Service Account (credentials JSON file) |
| CLI | `argparse` |

---

## CLI Usage

```bash
# Default (Gemini)
python main.py --sow path/to/sow.pdf --template template.csv

# With Claude
python main.py --sow path/to/sow.pdf --template template.csv --llm claude

# DOCX input
python main.py --sow path/to/sow.docx --template template.csv
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Scanned/image-only PDF | Fail fast: "PDF appears scanned, OCR not supported" |
| Unclear or low-resolution diagram | `flag_gap("Diagram on page X was unclear")` |
| Google Sheets write failure | Retry once, then save output as `output.csv` locally |
| Deliverable not traceable to SoW | `source_quote` missing → `flag_gap` called, row not written |
| Ambiguous scope or deliverable | `flag_gap` with reason — never resolved by invention |

---

## Project Structure

```
agent-projectplanner/
├── main.py                  # CLI entrypoint
├── agent/
│   ├── loop.py              # Agentic reasoning loop
│   ├── tools.py             # Tool definitions and implementations
│   ├── prompt.py            # System prompt
│   └── providers/
│       ├── base.py          # LLMProvider abstract class
│       ├── gemini.py        # GeminiProvider
│       └── claude.py        # ClaudeProvider
├── parsers/
│   ├── pdf.py               # pymupdf-based SoW parser
│   └── docx.py              # python-docx-based SoW parser
├── sheets/
│   └── writer.py            # Google Sheets create + write
├── template.csv            # Example template (user replaces with their own)
└── requirements.txt
```

---

## Constraints & Non-Goals

- **No OCR support** — scanned PDFs are out of scope
- **No multi-SoW batch processing** — one SoW per run
- **No web UI** — CLI only
- **No task-level breakdown** — output is phases, milestones, and named deliverables only (high-level)
- **No owner assignment** — timeline assumes one senior dev; owners left blank
