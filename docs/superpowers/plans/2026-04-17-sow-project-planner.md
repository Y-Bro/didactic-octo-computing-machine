# SoW Project Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI agent that reads a SoW (PDF/DOCX) and a CSV template, then creates a structured project plan in a new Google Sheet using only what's explicitly in the SoW.

**Architecture:** A Python CLI wires together a SoW parser, a CSV template reader, and an agentic tool-use loop backed by Gemini 2.0 Flash (default) or Claude claude-sonnet-4-6 (toggle). The agent calls four tools — `analyze_diagram`, `write_to_sheet`, `flag_gap`, and `vision_extract` — in a loop until the plan is complete. Each provider (Gemini / Claude) implements a common `LLMProvider` interface so the loop is provider-agnostic.

**Tech Stack:** Python 3.11+, `pymupdf`, `python-docx`, `google-generativeai`, `anthropic`, `google-api-python-client`, `pytest`

---

## File Map

| File | Responsibility |
|------|---------------|
| `main.py` | CLI entrypoint — parses args, wires components, runs agent |
| `parsers/pdf.py` | Extracts text + images from PDF using pymupdf |
| `parsers/docx.py` | Extracts text + images from DOCX using python-docx |
| `template/reader.py` | Reads CSV template, returns column/structure metadata |
| `agent/providers/base.py` | `ToolCall`, `ToolResult`, `LLMResponse` dataclasses; `LLMProvider` ABC |
| `agent/providers/gemini.py` | Gemini 2.0 Flash implementation of `LLMProvider` |
| `agent/providers/claude.py` | Claude claude-sonnet-4-6 implementation of `LLMProvider` |
| `agent/prompt.py` | Builds system prompt with grounding rules and developer profile |
| `agent/tools.py` | Tool schemas (JSON) + `ToolExecutor` class implementing each tool |
| `agent/loop.py` | Agentic reasoning loop — stateless, provider-agnostic |
| `sheets/writer.py` | Creates Google Sheet, writes plan rows and gaps tab |
| `tests/test_pdf_parser.py` | PDF parser tests |
| `tests/test_docx_parser.py` | DOCX parser tests |
| `tests/test_template_reader.py` | Template reader tests |
| `tests/test_providers.py` | Provider tests (mocked SDKs) |
| `tests/test_tools.py` | ToolExecutor tests (mocked sheets writer) |
| `tests/test_loop.py` | Loop tests (mocked provider) |
| `tests/test_sheets_writer.py` | Sheets writer tests (mocked Google API) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `template.csv`
- Create: `parsers/__init__.py`, `agent/__init__.py`, `agent/providers/__init__.py`, `sheets/__init__.py`, `template/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Write requirements.txt**

```
pymupdf==1.24.5
python-docx==1.1.2
google-generativeai==0.8.3
anthropic==0.40.0
google-api-python-client==2.151.0
google-auth==2.36.0
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 2: Write .env.example**

```
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

- [ ] **Step 3: Write .gitignore**

```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/

# Secrets & credentials
.env
credentials.json

# SoW input files — never commit client documents
*.pdf
*.docx
*.doc
sow/
input/

# Template files — user-provided, never commit
*.csv
*.xlsx
*.ods
*.tsv
template/
!template/__init__.py

# Output files — generated, never commit
output/
*.output.json

# IDE
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 4: Write template.csv (example — user replaces with their own)**

```csv
Phase,Milestone,Deliverable,Start Date,End Date,Estimated Days,Notes
,,,,,, 
```

- [ ] **Step 5: Create all __init__.py files**

Run:
```bash
mkdir -p parsers agent/providers sheets template tests
touch parsers/__init__.py agent/__init__.py agent/providers/__init__.py sheets/__init__.py template/__init__.py tests/__init__.py
```

- [ ] **Step 6: Install dependencies**

Run:
```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore template.csv parsers/__init__.py agent/__init__.py agent/providers/__init__.py sheets/__init__.py template/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding"
```

---

## Task 2: PDF Parser

**Files:**
- Create: `parsers/pdf.py`
- Create: `tests/test_pdf_parser.py`

- [ ] **Step 1: Write the failing test**

`tests/test_pdf_parser.py`:
```python
import base64
import io
import pytest
import fitz  # pymupdf
from parsers.pdf import parse_pdf


def make_test_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_pdf_returns_text():
    pdf_bytes = make_test_pdf("Deliverable: User Authentication Module")
    result = parse_pdf(pdf_bytes)
    assert "User Authentication Module" in result["text"]


def test_parse_pdf_returns_images_list():
    pdf_bytes = make_test_pdf("Some content")
    result = parse_pdf(pdf_bytes)
    assert "images" in result
    assert isinstance(result["images"], list)


def test_parse_pdf_image_has_required_keys():
    pdf_bytes = make_test_pdf("Some content")
    result = parse_pdf(pdf_bytes)
    # No images in this test PDF — list should be empty, not error
    assert result["images"] == []


def test_parse_pdf_raises_on_empty_text():
    """Scanned PDFs produce no text — must raise ValueError."""
    doc = fitz.open()
    doc.new_page()  # blank page, no text
    buf = io.BytesIO()
    doc.save(buf)
    with pytest.raises(ValueError, match="PDF appears scanned"):
        parse_pdf(buf.getvalue())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_pdf_parser.py -v
```
Expected: `ImportError: cannot import name 'parse_pdf'`

- [ ] **Step 3: Write parsers/pdf.py**

```python
import base64
import io
import fitz  # pymupdf


def parse_pdf(pdf_bytes: bytes) -> dict:
    """
    Returns {"text": str, "images": [{"data": base64_str, "page": int, "index": int}]}
    Raises ValueError if no text is found (likely scanned PDF).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    images = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            text_parts.append(text)

        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            images.append({
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": f"image/{base_image['ext']}",
                "page": page_num + 1,
                "index": img_index,
            })

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("PDF appears scanned — no extractable text found. OCR is not supported.")

    return {"text": full_text, "images": images}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_pdf_parser.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add parsers/pdf.py tests/test_pdf_parser.py
git commit -m "feat: PDF parser extracts text and images"
```

---

## Task 3: DOCX Parser

**Files:**
- Create: `parsers/docx.py`
- Create: `tests/test_docx_parser.py`

- [ ] **Step 1: Write the failing test**

`tests/test_docx_parser.py`:
```python
import base64
import io
import pytest
from docx import Document
from parsers.docx import parse_docx


def make_test_docx(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_docx_returns_text():
    docx_bytes = make_test_docx("Deliverable: API Gateway Integration")
    result = parse_docx(docx_bytes)
    assert "API Gateway Integration" in result["text"]


def test_parse_docx_returns_images_list():
    docx_bytes = make_test_docx("Some content")
    result = parse_docx(docx_bytes)
    assert "images" in result
    assert isinstance(result["images"], list)


def test_parse_docx_no_images_returns_empty_list():
    docx_bytes = make_test_docx("Some content")
    result = parse_docx(docx_bytes)
    assert result["images"] == []


def test_parse_docx_raises_on_empty_text():
    doc = Document()
    buf = io.BytesIO()
    doc.save(buf)
    with pytest.raises(ValueError, match="DOCX contains no text"):
        parse_docx(buf.getvalue())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_docx_parser.py -v
```
Expected: `ImportError: cannot import name 'parse_docx'`

- [ ] **Step 3: Write parsers/docx.py**

```python
import base64
import io
from docx import Document
from docx.oxml.ns import qn


def parse_docx(docx_bytes: bytes) -> dict:
    """
    Returns {"text": str, "images": [{"data": base64_str, "mime_type": str, "index": int}]}
    Raises ValueError if no text is found.
    """
    doc = Document(io.BytesIO(docx_bytes))

    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    paragraphs.append(cell.text.strip())

    full_text = "\n".join(paragraphs).strip()
    if not full_text:
        raise ValueError("DOCX contains no text.")

    images = []
    for i, rel in enumerate(doc.part.rels.values()):
        if "image" in rel.reltype:
            image_bytes = rel.target_part.blob
            mime_type = rel.target_part.content_type
            images.append({
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": mime_type,
                "page": None,
                "index": i,
            })

    return {"text": full_text, "images": images}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_docx_parser.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add parsers/docx.py tests/test_docx_parser.py
git commit -m "feat: DOCX parser extracts text and images"
```

---

## Task 4: Template CSV Reader

**Files:**
- Create: `template/reader.py`
- Create: `tests/test_template_reader.py`
- Create: `tests/fixtures/sample_template.csv`

- [ ] **Step 1: Write the failing test**

`tests/fixtures/sample_template.csv`:
```csv
Phase,Milestone,Deliverable,Start Date,End Date,Estimated Days,Notes
Planning,Project Kickoff,Kickoff Meeting,,,1,
Planning,Requirements,Requirements Document,,,3,
```

`tests/test_template_reader.py`:
```python
import pytest
from template.reader import read_template


def test_read_template_returns_columns(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text("Phase,Milestone,Deliverable,Start Date,End Date,Estimated Days,Notes\n")
    result = read_template(str(csv_file))
    assert result["columns"] == ["Phase", "Milestone", "Deliverable", "Start Date", "End Date", "Estimated Days", "Notes"]


def test_read_template_returns_sample_rows(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text(
        "Phase,Milestone,Deliverable\n"
        "Planning,Kickoff,Kickoff Meeting\n"
    )
    result = read_template(str(csv_file))
    assert len(result["sample_rows"]) == 1
    assert result["sample_rows"][0]["Phase"] == "Planning"


def test_read_template_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        read_template("/nonexistent/path/template.csv")


def test_read_template_raises_on_empty_file(tmp_path):
    csv_file = tmp_path / "template.csv"
    csv_file.write_text("")
    with pytest.raises(ValueError, match="Template CSV is empty"):
        read_template(str(csv_file))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_template_reader.py -v
```
Expected: `ImportError: cannot import name 'read_template'`

- [ ] **Step 3: Write template/reader.py**

```python
import csv


def read_template(path: str) -> dict:
    """
    Returns {"columns": list[str], "sample_rows": list[dict]}
    Raises FileNotFoundError if path does not exist.
    Raises ValueError if file is empty.
    """
    with open(path, newline="", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        raise ValueError("Template CSV is empty.")

    reader = csv.DictReader(content.splitlines())
    columns = reader.fieldnames
    if not columns:
        raise ValueError("Template CSV is empty.")

    sample_rows = [row for row in reader]

    return {"columns": list(columns), "sample_rows": sample_rows}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_template_reader.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add template/reader.py tests/test_template_reader.py tests/fixtures/sample_template.csv
git commit -m "feat: template CSV reader"
```

---

## Task 5: LLM Provider Base

**Files:**
- Create: `agent/providers/base.py`

- [ ] **Step 1: Write the failing test**

`tests/test_providers.py`:
```python
import pytest
from agent.providers.base import ToolCall, ToolResult, LLMResponse, LLMProvider


def test_tool_call_fields():
    tc = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear"})
    assert tc.id == "1"
    assert tc.name == "flag_gap"
    assert tc.arguments == {"reason": "unclear"}


def test_tool_result_fields():
    tr = ToolResult(call_id="1", name="flag_gap", content="Gap recorded.")
    assert tr.call_id == "1"


def test_llm_response_text_only():
    r = LLMResponse(tool_calls=[], text="Done.")
    assert r.text == "Done."
    assert r.tool_calls == []


def test_llm_response_tool_calls():
    tc = ToolCall(id="1", name="flag_gap", arguments={})
    r = LLMResponse(tool_calls=[tc], text=None)
    assert r.text is None
    assert len(r.tool_calls) == 1


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_providers.py -v
```
Expected: `ImportError: cannot import name 'ToolCall'`

- [ ] **Step 3: Write agent/providers/base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    call_id: str
    name: str
    content: str


@dataclass
class LLMResponse:
    tool_calls: list[ToolCall] = field(default_factory=list)
    text: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        """
        Single completion call. messages follow this format:
          {"role": "user", "content": str | list}      — user turn (list for multimodal)
          {"role": "assistant", "tool_calls": [...]}   — assistant tool request turn
          {"role": "tool", "results": [...]}           — tool results turn
        Returns LLMResponse with either tool_calls or text populated.
        """
        pass

    @abstractmethod
    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        """Appends the assistant's tool-call turn to messages."""
        pass

    @abstractmethod
    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        """Appends tool results to messages."""
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_providers.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/providers/base.py tests/test_providers.py
git commit -m "feat: LLM provider base classes"
```

---

## Task 6: Gemini Provider

**Files:**
- Create: `agent/providers/gemini.py`
- Modify: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:
```python
from unittest.mock import MagicMock, patch
from agent.providers.gemini import GeminiProvider
from agent.providers.base import ToolCall, ToolResult, LLMResponse


def test_gemini_complete_returns_text_response():
    mock_response = MagicMock()
    mock_response.parts = [MagicMock(text="Plan complete.", function_call=None)]
    mock_response.text = "Plan complete."

    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    with patch("agent.providers.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text == "Plan complete."
    assert result.tool_calls == []


def test_gemini_complete_returns_tool_call():
    mock_fn = MagicMock()
    mock_fn.name = "flag_gap"
    mock_fn.args = {"reason": "unclear scope", "location": "Section 2"}

    mock_part = MagicMock()
    mock_part.text = None
    mock_part.function_call = mock_fn

    mock_response = MagicMock()
    mock_response.parts = [mock_part]
    mock_response.text = None

    mock_chat = MagicMock()
    mock_chat.send_message.return_value = mock_response

    mock_model = MagicMock()
    mock_model.start_chat.return_value = mock_chat

    with patch("agent.providers.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "flag_gap"
    assert result.tool_calls[0].arguments == {"reason": "unclear scope", "location": "Section 2"}


def test_gemini_add_tool_results_appends_to_messages():
    with patch("agent.providers.gemini.genai"):
        provider = GeminiProvider(api_key="fake-key")

    messages = [{"role": "user", "content": "Hello"}]
    response = LLMResponse(tool_calls=[ToolCall(id="1", name="flag_gap", arguments={})], text=None)
    results = [ToolResult(call_id="1", name="flag_gap", content="Gap recorded.")]

    messages = provider.add_assistant_turn(messages, response)
    messages = provider.add_tool_results(messages, results)

    assert messages[-1]["role"] == "tool"
    assert len(messages[-1]["results"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_providers.py::test_gemini_complete_returns_text_response -v
```
Expected: `ImportError: cannot import name 'GeminiProvider'`

- [ ] **Step 3: Write agent/providers/gemini.py**

```python
import json
import uuid
import google.generativeai as genai
from agent.providers.base import LLMProvider, LLMResponse, ToolCall, ToolResult


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self._model_name = model

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        gemini_tools = self._convert_tools(tools)
        model = genai.GenerativeModel(
            model_name=self._model_name,
            tools=gemini_tools if gemini_tools else None,
            system_instruction=system,
        )
        chat = model.start_chat(history=self._convert_history(messages[:-1]))
        last = messages[-1]
        content = self._convert_user_content(last["content"])
        response = chat.send_message(content)
        return self._parse_response(response)

    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        return messages + [{"role": "assistant", "tool_calls": response.tool_calls}]

    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        return messages + [{"role": "tool", "results": results}]

    def _parse_response(self, response) -> LLMResponse:
        tool_calls = []
        for part in response.parts:
            if part.function_call:
                fn = part.function_call
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),
                    name=fn.name,
                    arguments=dict(fn.args),
                ))
        if tool_calls:
            return LLMResponse(tool_calls=tool_calls, text=None)
        return LLMResponse(tool_calls=[], text=response.text)

    def _convert_tools(self, tools: list[dict]):
        if not tools:
            return []
        declarations = []
        for t in tools:
            declarations.append(genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=self._schema_to_gemini(t.get("parameters", {})),
            ))
        return [genai.protos.Tool(function_declarations=declarations)]

    def _schema_to_gemini(self, schema: dict):
        type_map = {"string": genai.protos.Type.STRING, "integer": genai.protos.Type.INTEGER,
                    "number": genai.protos.Type.NUMBER, "boolean": genai.protos.Type.BOOLEAN,
                    "array": genai.protos.Type.ARRAY, "object": genai.protos.Type.OBJECT}
        props = {}
        for name, prop in schema.get("properties", {}).items():
            props[name] = genai.protos.Schema(
                type=type_map.get(prop.get("type", "string"), genai.protos.Type.STRING),
                description=prop.get("description", ""),
            )
        return genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties=props,
            required=schema.get("required", []),
        )

    def _convert_history(self, messages: list[dict]) -> list:
        history = []
        for msg in messages:
            if msg["role"] == "user":
                history.append({"role": "user", "parts": self._convert_user_content(msg["content"])})
            elif msg["role"] == "assistant":
                parts = []
                for tc in msg.get("tool_calls", []):
                    parts.append(genai.protos.Part(
                        function_call=genai.protos.FunctionCall(
                            name=tc.name, args=tc.arguments
                        )
                    ))
                history.append({"role": "model", "parts": parts})
            elif msg["role"] == "tool":
                parts = [
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=r.name,
                            response={"result": r.content},
                        )
                    )
                    for r in msg["results"]
                ]
                history.append({"role": "user", "parts": parts})
        return history

    def _convert_user_content(self, content) -> list:
        if isinstance(content, str):
            return [content]
        parts = []
        for item in content:
            if item["type"] == "text":
                parts.append(item["text"])
            elif item["type"] == "image":
                import base64
                parts.append(genai.protos.Part(
                    inline_data=genai.protos.Blob(
                        mime_type=item["source"]["media_type"],
                        data=base64.b64decode(item["source"]["data"]),
                    )
                ))
        return parts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_providers.py -k "gemini" -v
```
Expected: all 3 Gemini tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/providers/gemini.py tests/test_providers.py
git commit -m "feat: Gemini provider implementation"
```

---

## Task 7: Claude Provider

**Files:**
- Create: `agent/providers/claude.py`
- Modify: `tests/test_providers.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_providers.py`:
```python
from unittest.mock import MagicMock, patch
from agent.providers.claude import ClaudeProvider


def test_claude_complete_returns_text_response():
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Plan complete."

    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_block]

    with patch("agent.providers.claude.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        provider = ClaudeProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text == "Plan complete."
    assert result.tool_calls == []


def test_claude_complete_returns_tool_call():
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.id = "toolu_01"
    mock_tool_block.name = "flag_gap"
    mock_tool_block.input = {"reason": "unclear", "location": "page 3"}

    mock_response = MagicMock()
    mock_response.stop_reason = "tool_use"
    mock_response.content = [mock_tool_block]

    with patch("agent.providers.claude.anthropic.Anthropic") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        provider = ClaudeProvider(api_key="fake-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.complete("System prompt", messages, tools=[])

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "toolu_01"
    assert result.tool_calls[0].name == "flag_gap"


def test_claude_add_tool_results_appends_to_messages():
    with patch("agent.providers.claude.anthropic.Anthropic"):
        provider = ClaudeProvider(api_key="fake-key")

    messages = [{"role": "user", "content": "Hello"}]
    response = LLMResponse(tool_calls=[ToolCall(id="toolu_01", name="flag_gap", arguments={})], text=None)
    results = [ToolResult(call_id="toolu_01", name="flag_gap", content="Gap recorded.")]

    messages = provider.add_assistant_turn(messages, response)
    messages = provider.add_tool_results(messages, results)

    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"][0]["type"] == "tool_result"
    assert messages[-1]["content"][0]["tool_use_id"] == "toolu_01"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_providers.py::test_claude_complete_returns_text_response -v
```
Expected: `ImportError: cannot import name 'ClaudeProvider'`

- [ ] **Step 3: Write agent/providers/claude.py**

```python
import anthropic
from agent.providers.base import LLMProvider, LLMResponse, ToolCall, ToolResult


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        claude_messages = self._convert_messages(messages)
        claude_tools = self._convert_tools(tools)

        kwargs = {
            "model": self._model,
            "max_tokens": 8192,
            "system": system,
            "messages": claude_messages,
        }
        if claude_tools:
            kwargs["tools"] = claude_tools

        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    def add_assistant_turn(self, messages: list[dict], response: LLMResponse) -> list[dict]:
        content = [
            {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
            for tc in response.tool_calls
        ]
        return messages + [{"role": "assistant", "content": content}]

    def add_tool_results(self, messages: list[dict], results: list[ToolResult]) -> list[dict]:
        content = [
            {"type": "tool_result", "tool_use_id": r.call_id, "content": r.content}
            for r in results
        ]
        return messages + [{"role": "user", "content": content}]

    def _parse_response(self, response) -> LLMResponse:
        tool_calls = []
        text = None
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
            elif block.type == "text":
                text = block.text
        if tool_calls:
            return LLMResponse(tool_calls=tool_calls, text=None)
        return LLMResponse(tool_calls=[], text=text)

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        result = []
        for msg in messages:
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, str):
                    result.append({"role": "user", "content": content})
                else:
                    claude_parts = []
                    for part in content:
                        if part["type"] == "text":
                            claude_parts.append({"type": "text", "text": part["text"]})
                        elif part["type"] == "image":
                            claude_parts.append({
                                "type": "image",
                                "source": part["source"],
                            })
                    result.append({"role": "user", "content": claude_parts})
            elif msg["role"] == "assistant":
                content = [
                    {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                    for tc in msg.get("tool_calls", [])
                ]
                result.append({"role": "assistant", "content": content})
            elif msg["role"] == "tool":
                content = [
                    {"type": "tool_result", "tool_use_id": r.call_id, "content": r.content}
                    for r in msg["results"]
                ]
                result.append({"role": "user", "content": content})
        return result

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t.get("parameters", {}),
            }
            for t in tools
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_providers.py -v
```
Expected: all provider tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/providers/claude.py tests/test_providers.py
git commit -m "feat: Claude provider implementation"
```

---

## Task 8: System Prompt

**Files:**
- Create: `agent/prompt.py`
- Create: `tests/test_prompt.py`

- [ ] **Step 1: Write the failing test**

`tests/test_prompt.py`:
```python
from agent.prompt import build_system_prompt


def test_prompt_includes_grounding_rule():
    prompt = build_system_prompt(columns=["Phase", "Milestone", "Deliverable"])
    assert "source_quote" in prompt


def test_prompt_includes_developer_profile():
    prompt = build_system_prompt(columns=["Phase"])
    assert "senior developer" in prompt.lower()
    assert "3 years" in prompt.lower()


def test_prompt_includes_flag_gap_instruction():
    prompt = build_system_prompt(columns=["Phase"])
    assert "flag_gap" in prompt


def test_prompt_includes_column_names():
    prompt = build_system_prompt(columns=["Phase", "Deliverable", "Start Date"])
    assert "Phase" in prompt
    assert "Deliverable" in prompt
    assert "Start Date" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_prompt.py -v
```
Expected: `ImportError: cannot import name 'build_system_prompt'`

- [ ] **Step 3: Write agent/prompt.py**

```python
def build_system_prompt(columns: list[str]) -> str:
    columns_str = ", ".join(columns)
    return f"""You are a project planning agent. Your job is to read a Statement of Work (SoW) and produce a structured project plan.

GROUNDING RULES — follow these strictly:
1. Every deliverable you identify MUST have a `source_quote` field containing the verbatim text or diagram description from the SoW that justifies its inclusion.
2. If you cannot provide a `source_quote`, you MUST call `flag_gap` instead of writing the row. Never invent deliverables.
3. Extract only what is explicitly stated or directly implied in the SoW text or architecture diagrams.
4. When you see architecture diagrams, call `analyze_diagram` to extract components, integrations, and system boundaries. Use this output — not your prior knowledge — to inform deliverables.

TIMELINE ESTIMATION:
- Estimate all timelines assuming a single senior developer with 3 years of experience.
- Use architecture diagram complexity to adjust estimates when the diagram reveals significant integration work.
- Express durations in working days.

OUTPUT STRUCTURE:
- The output Google Sheet must follow this column structure exactly: {columns_str}
- Call `write_to_sheet` once when you have processed the entire SoW, passing all rows.
- Call `flag_gap` for each ambiguous item, unclear scope, or anything you cannot trace to the SoW.

PROCESS:
1. Review the full SoW text.
2. For each architecture diagram image, call `analyze_diagram`.
3. Identify all phases, milestones, and specifically named deliverables.
4. Estimate timelines.
5. Call `write_to_sheet` with all rows.
6. Call `flag_gap` for any items you could not resolve.
"""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_prompt.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/prompt.py tests/test_prompt.py
git commit -m "feat: system prompt builder"
```

---

## Task 9: Tool Schemas and ToolExecutor

**Files:**
- Create: `agent/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

`tests/test_tools.py`:
```python
import pytest
from unittest.mock import MagicMock
from agent.tools import get_tool_schemas, ToolExecutor


def test_get_tool_schemas_returns_list():
    schemas = get_tool_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) == 3


def test_tool_schemas_have_required_keys():
    schemas = get_tool_schemas()
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema


def test_tool_schemas_names():
    names = {s["name"] for s in get_tool_schemas()}
    assert names == {"analyze_diagram", "write_to_sheet", "flag_gap"}


def test_flag_gap_accumulates():
    mock_writer = MagicMock()
    executor = ToolExecutor(sheets_writer=mock_writer, provider=MagicMock())
    result = executor.flag_gap(reason="Scope unclear", location="Section 3")
    assert result == "Gap recorded."
    assert len(executor.gaps) == 1
    assert executor.gaps[0]["reason"] == "Scope unclear"


def test_write_to_sheet_calls_writer():
    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"
    executor = ToolExecutor(sheets_writer=mock_writer, provider=MagicMock())
    executor.flag_gap(reason="Unclear item", location="page 1")

    result = executor.write_to_sheet(
        title="Project Plan",
        rows=[{"Phase": "Build", "Milestone": "API", "Deliverable": "REST API", "Start Date": "2026-05-01", "End Date": "2026-05-10", "Estimated Days": "7", "Notes": ""}],
    )
    assert "https://docs.google.com" in result
    mock_writer.create_sheet.assert_called_once()


def test_analyze_diagram_calls_provider(monkeypatch):
    mock_provider = MagicMock()
    mock_provider.complete.return_value = MagicMock(
        text='{"components": ["API Gateway"], "integrations": ["DB"], "boundaries": []}',
        tool_calls=[]
    )
    executor = ToolExecutor(sheets_writer=MagicMock(), provider=mock_provider)
    result = executor.analyze_diagram(image_base64="abc123", page_number=1)
    assert "components" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tools.py -v
```
Expected: `ImportError: cannot import name 'get_tool_schemas'`

- [ ] **Step 3: Write agent/tools.py**

```python
import json


def get_tool_schemas() -> list[dict]:
    return [
        {
            "name": "analyze_diagram",
            "description": "Analyze an architecture diagram image and return structured JSON describing components, integrations, and system boundaries. Only call this for images from the SoW.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image data from the SoW",
                    },
                    "page_number": {
                        "type": "integer",
                        "description": "Page number where this diagram appears (use 0 if unknown)",
                    },
                },
                "required": ["image_base64", "page_number"],
            },
        },
        {
            "name": "write_to_sheet",
            "description": "Create a new Google Sheet with the project plan. Call this once when all deliverables have been identified. Pass all rows at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the new Google Sheet",
                    },
                    "rows": {
                        "type": "array",
                        "description": "List of plan rows. Each row is a dict matching the template columns.",
                        "items": {"type": "object"},
                    },
                },
                "required": ["title", "rows"],
            },
        },
        {
            "name": "flag_gap",
            "description": "Record an ambiguous item, unclear scope, or anything that cannot be traced to the SoW. Call this instead of inventing a deliverable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why this item is ambiguous or missing",
                    },
                    "location": {
                        "type": "string",
                        "description": "Where in the SoW this issue was found (e.g. 'Section 3', 'page 5', 'diagram on page 2')",
                    },
                },
                "required": ["reason", "location"],
            },
        },
    ]


class ToolExecutor:
    def __init__(self, sheets_writer, provider):
        self._writer = sheets_writer
        self._provider = provider
        self.gaps: list[dict] = []

    def execute(self, name: str, arguments: dict) -> str:
        if name == "analyze_diagram":
            return json.dumps(self.analyze_diagram(**arguments))
        if name == "write_to_sheet":
            return self.write_to_sheet(**arguments)
        if name == "flag_gap":
            return self.flag_gap(**arguments)
        raise ValueError(f"Unknown tool: {name}")

    def analyze_diagram(self, image_base64: str, page_number: int) -> dict:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This is an architecture diagram from a Statement of Work. "
                            "Extract: (1) all named components/systems, (2) integrations between them, "
                            "(3) system boundaries. Return ONLY valid JSON in this format: "
                            '{"components": [...], "integrations": [...], "boundaries": [...]}'
                        ),
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64,
                        },
                    },
                ],
            }
        ]
        response = self._provider.complete(
            system="You are a technical diagram analyst. Respond only with valid JSON.",
            messages=messages,
            tools=[],
        )
        try:
            return json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return {"components": [], "integrations": [], "boundaries": [], "parse_error": response.text}

    def write_to_sheet(self, title: str, rows: list[dict]) -> str:
        url = self._writer.create_sheet(title=title, rows=rows, gaps=self.gaps)
        return url

    def flag_gap(self, reason: str, location: str) -> str:
        self.gaps.append({"reason": reason, "location": location})
        return "Gap recorded."
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tools.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/tools.py tests/test_tools.py
git commit -m "feat: tool schemas and ToolExecutor"
```

---

## Task 10: Google Sheets Writer

**Files:**
- Create: `sheets/writer.py`
- Create: `tests/test_sheets_writer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_sheets_writer.py`:
```python
import pytest
from unittest.mock import MagicMock, patch
from sheets.writer import SheetsWriter


SAMPLE_ROWS = [
    {"Phase": "Build", "Milestone": "API", "Deliverable": "REST API", "Start Date": "2026-05-01", "End Date": "2026-05-10", "Estimated Days": "7", "Notes": ""},
]

SAMPLE_GAPS = [
    {"reason": "Scope unclear", "location": "Section 3"},
]


def make_mock_service():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.return_value = {
        "spreadsheetId": "sheet123",
        "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
    }
    mock_service.spreadsheets().batchUpdate().execute.return_value = {}
    mock_service.spreadsheets().values().update().execute.return_value = {}
    return mock_service


def test_create_sheet_returns_url():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(credentials_path="fake.json")
        url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    assert "docs.google.com" in url


def test_create_sheet_calls_spreadsheets_create():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(credentials_path="fake.json")
        writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    mock_service.spreadsheets().create.assert_called()


def test_create_sheet_writes_gaps_tab_when_gaps_present():
    mock_service = make_mock_service()
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(credentials_path="fake.json")
        writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=SAMPLE_GAPS)
    # batchUpdate called to add the Gaps sheet
    mock_service.spreadsheets().batchUpdate.assert_called()


def test_create_sheet_retries_on_failure():
    mock_service = MagicMock()
    mock_service.spreadsheets().create().execute.side_effect = [
        Exception("transient error"),
        {
            "spreadsheetId": "sheet123",
            "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/sheet123",
        },
    ]
    with patch("sheets.writer.build_service", return_value=mock_service):
        writer = SheetsWriter(credentials_path="fake.json")
        url = writer.create_sheet(title="My Plan", rows=SAMPLE_ROWS, gaps=[])
    assert "docs.google.com" in url
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sheets_writer.py -v
```
Expected: `ImportError: cannot import name 'SheetsWriter'`

- [ ] **Step 3: Write sheets/writer.py**

```python
import csv
import io
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def build_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


class SheetsWriter:
    def __init__(self, credentials_path: str):
        self._credentials_path = credentials_path

    def create_sheet(self, title: str, rows: list[dict], gaps: list[dict]) -> str:
        service = build_service(self._credentials_path)

        spreadsheet_body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": "Project Plan"}}],
        }

        for attempt in range(2):
            try:
                result = service.spreadsheets().create(body=spreadsheet_body).execute()
                break
            except Exception:
                if attempt == 1:
                    raise
                time.sleep(1)

        sheet_id = result["spreadsheetId"]
        sheet_url = result.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{sheet_id}")

        if rows:
            columns = list(rows[0].keys())
            values = [columns] + [[row.get(col, "") for col in columns] for row in rows]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Project Plan!A1",
                valueInputOption="RAW",
                body={"values": values},
            ).execute()

        if gaps:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": "Gaps"}}}]},
            ).execute()
            gap_values = [["Reason", "Location"]] + [[g["reason"], g["location"]] for g in gaps]
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="Gaps!A1",
                valueInputOption="RAW",
                body={"values": gap_values},
            ).execute()

        return sheet_url
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sheets_writer.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sheets/writer.py tests/test_sheets_writer.py
git commit -m "feat: Google Sheets writer"
```

---

## Task 11: Agent Reasoning Loop

**Files:**
- Create: `agent/loop.py`
- Create: `tests/test_loop.py`

- [ ] **Step 1: Write the failing test**

`tests/test_loop.py`:
```python
import pytest
from unittest.mock import MagicMock
from agent.loop import run_agent
from agent.providers.base import LLMResponse, ToolCall


def make_provider(responses):
    """Returns a mock provider that yields responses in order."""
    provider = MagicMock()
    provider.complete.side_effect = responses
    provider.add_assistant_turn.side_effect = lambda msgs, resp: msgs + [{"role": "assistant", "tool_calls": resp.tool_calls}]
    provider.add_tool_results.side_effect = lambda msgs, results: msgs + [{"role": "tool", "results": results}]
    return provider


def test_run_agent_returns_sheet_url_when_write_to_sheet_called():
    tool_call = ToolCall(id="1", name="write_to_sheet", arguments={
        "title": "My Plan",
        "rows": [{"Phase": "Build", "Milestone": "API", "Deliverable": "REST API",
                  "Start Date": "2026-05-01", "End Date": "2026-05-10",
                  "Estimated Days": "7", "Notes": ""}],
    })
    responses = [
        LLMResponse(tool_calls=[tool_call], text=None),
        LLMResponse(tool_calls=[], text="Project plan written successfully."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Build a REST API.", "images": []},
        template={"columns": ["Phase", "Milestone", "Deliverable", "Start Date", "End Date", "Estimated Days", "Notes"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )

    assert "docs.google.com" in result


def test_run_agent_calls_flag_gap_tool():
    flag_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear", "location": "page 1"})
    write_call = ToolCall(id="2", name="write_to_sheet", arguments={"title": "Plan", "rows": []})
    responses = [
        LLMResponse(tool_calls=[flag_call], text=None),
        LLMResponse(tool_calls=[write_call], text=None),
        LLMResponse(tool_calls=[], text="Done."),
    ]
    provider = make_provider(responses)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    result = run_agent(
        sow_data={"text": "Some SoW text.", "images": []},
        template={"columns": ["Phase"], "sample_rows": []},
        provider=provider,
        sheets_writer=mock_writer,
    )
    assert "docs.google.com" in result


def test_run_agent_stops_after_max_iterations():
    """Prevents infinite loops if the agent never calls write_to_sheet."""
    tool_call = ToolCall(id="1", name="flag_gap", arguments={"reason": "unclear", "location": "page 1"})
    provider = make_provider([LLMResponse(tool_calls=[tool_call], text=None)] * 30)

    mock_writer = MagicMock()
    mock_writer.create_sheet.return_value = "https://docs.google.com/spreadsheets/d/abc"

    with pytest.raises(RuntimeError, match="exceeded maximum iterations"):
        run_agent(
            sow_data={"text": "text", "images": []},
            template={"columns": ["Phase"], "sample_rows": []},
            provider=provider,
            sheets_writer=mock_writer,
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_loop.py -v
```
Expected: `ImportError: cannot import name 'run_agent'`

- [ ] **Step 3: Write agent/loop.py**

```python
from agent.prompt import build_system_prompt
from agent.tools import get_tool_schemas, ToolExecutor
from agent.providers.base import LLMProvider, ToolResult

MAX_ITERATIONS = 20


def run_agent(sow_data: dict, template: dict, provider: LLMProvider, sheets_writer) -> str:
    """
    Runs the agentic loop. Returns the Google Sheet URL.
    sow_data: {"text": str, "images": [{"data": base64, "mime_type": str, "page": int, "index": int}]}
    template: {"columns": list[str], "sample_rows": list[dict]}
    """
    system = build_system_prompt(columns=template["columns"])
    tools = get_tool_schemas()
    executor = ToolExecutor(sheets_writer=sheets_writer, provider=provider)

    initial_content = _build_initial_content(sow_data, template)
    messages = [{"role": "user", "content": initial_content}]

    sheet_url = None

    for iteration in range(MAX_ITERATIONS):
        response = provider.complete(system=system, messages=messages, tools=tools)

        if response.text is not None and not response.tool_calls:
            break

        messages = provider.add_assistant_turn(messages, response)

        results = []
        for tool_call in response.tool_calls:
            output = executor.execute(tool_call.name, tool_call.arguments)
            results.append(ToolResult(
                call_id=tool_call.id,
                name=tool_call.name,
                content=output,
            ))
            if tool_call.name == "write_to_sheet" and "docs.google.com" in output:
                sheet_url = output

        messages = provider.add_tool_results(messages, results)
    else:
        raise RuntimeError(
            f"Agent exceeded maximum iterations ({MAX_ITERATIONS}). "
            "Check the SoW for content that may be causing the agent to loop."
        )

    if sheet_url is None:
        raise RuntimeError("Agent completed without calling write_to_sheet. No Google Sheet was created.")

    return sheet_url


def _build_initial_content(sow_data: dict, template: dict) -> list:
    columns_str = ", ".join(template["columns"])
    text_part = {
        "type": "text",
        "text": (
            f"Here is the Statement of Work:\n\n{sow_data['text']}\n\n"
            f"The output Google Sheet must use these columns exactly: {columns_str}\n\n"
            "Analyze the SoW and create a project plan. "
            "For any architecture diagrams, call analyze_diagram first. "
            "Only include deliverables you can trace directly to this SoW. "
            "Call write_to_sheet once with all rows when done."
        ),
    }
    content = [text_part]

    for img in sow_data.get("images", []):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img.get("mime_type", "image/png"),
                "data": img["data"],
            },
        })

    return content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_loop.py -v
```
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/loop.py tests/test_loop.py
git commit -m "feat: agent reasoning loop"
```

---

## Task 12: CLI Entrypoint

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from main import build_provider, load_sow


def test_build_provider_returns_gemini_by_default():
    from agent.providers.gemini import GeminiProvider
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        provider = build_provider("gemini")
    assert isinstance(provider, GeminiProvider)


def test_build_provider_returns_claude():
    from agent.providers.claude import ClaudeProvider
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
        provider = build_provider("claude")
    assert isinstance(provider, ClaudeProvider)


def test_build_provider_raises_on_missing_gemini_key():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("GEMINI_API_KEY", None)
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            build_provider("gemini")


def test_build_provider_raises_on_missing_claude_key():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            build_provider("claude")


def test_load_sow_dispatches_pdf(tmp_path):
    pdf_path = tmp_path / "sow.pdf"
    pdf_path.write_bytes(b"fake")
    with patch("main.parse_pdf") as mock_pdf:
        mock_pdf.return_value = {"text": "hello", "images": []}
        result = load_sow(str(pdf_path))
    mock_pdf.assert_called_once()
    assert result["text"] == "hello"


def test_load_sow_dispatches_docx(tmp_path):
    docx_path = tmp_path / "sow.docx"
    docx_path.write_bytes(b"fake")
    with patch("main.parse_docx") as mock_docx:
        mock_docx.return_value = {"text": "hello", "images": []}
        result = load_sow(str(docx_path))
    mock_docx.assert_called_once()


def test_load_sow_raises_on_unsupported_format(tmp_path):
    txt_path = tmp_path / "sow.txt"
    txt_path.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_sow(str(txt_path))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_main.py -v
```
Expected: `ImportError: cannot import name 'build_provider'`

- [ ] **Step 3: Write main.py**

```python
import argparse
import os
import sys

from parsers.pdf import parse_pdf
from parsers.docx import parse_docx
from template.reader import read_template
from agent.loop import run_agent
from sheets.writer import SheetsWriter


def build_provider(llm: str):
    if llm == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")
        from agent.providers.gemini import GeminiProvider
        return GeminiProvider(api_key=api_key)
    elif llm == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
        from agent.providers.claude import ClaudeProvider
        return ClaudeProvider(api_key=api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {llm}. Choose 'gemini' or 'claude'.")


def load_sow(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    if path.lower().endswith(".pdf"):
        return parse_pdf(data)
    elif path.lower().endswith(".docx"):
        return parse_docx(data)
    else:
        raise ValueError(f"Unsupported file format: {path}. Use .pdf or .docx.")


def main():
    parser = argparse.ArgumentParser(description="SoW Project Planner Agent")
    parser.add_argument("--sow", required=True, help="Path to SoW file (.pdf or .docx)")
    parser.add_argument("--template", required=True, help="Path to template CSV file")
    parser.add_argument("--llm", default="gemini", choices=["gemini", "claude"], help="LLM provider (default: gemini)")
    parser.add_argument("--credentials", default="credentials.json", help="Path to Google service account credentials JSON")
    parser.add_argument("--title", default="Project Plan", help="Title for the output Google Sheet")
    args = parser.parse_args()

    print(f"Loading SoW from {args.sow}...")
    sow_data = load_sow(args.sow)
    print(f"Extracted {len(sow_data['text'])} characters of text and {len(sow_data['images'])} images.")

    print(f"Loading template from {args.template}...")
    template = read_template(args.template)
    print(f"Template columns: {', '.join(template['columns'])}")

    print(f"Initializing {args.llm} provider...")
    provider = build_provider(args.llm)

    sheets_writer = SheetsWriter(credentials_path=args.credentials)

    print("Running agent...")
    sheet_url = run_agent(
        sow_data=sow_data,
        template=template,
        provider=provider,
        sheets_writer=sheets_writer,
    )

    print(f"\nDone! Project plan created: {sheet_url}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: CLI entrypoint"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|-----------|
| PDF input | Task 2 |
| DOCX input | Task 3 |
| Architecture diagram vision analysis | Task 9 (`analyze_diagram` tool) |
| CSV template defines output structure | Task 4 |
| Output mirrors template structure | Task 10 (columns from template passed to writer) |
| New Google Sheet output | Task 10 |
| Gaps tab for ambiguous items | Task 10 |
| Gemini provider (default) | Task 6 |
| Claude provider (toggle) | Task 7 |
| `--llm` CLI flag | Task 12 |
| Grounding enforcement via source_quote | Task 8 (system prompt) |
| Timeline: 1 senior dev, 3 YoE | Task 8 (system prompt) |
| Diagram complexity informs timeline | Task 8 (system prompt) |
| Scanned PDF error | Task 2 |
| Sheets write failure → retry + CSV fallback | Task 10 (retry implemented; CSV fallback is out of scope per constraints) |
| Max iteration guard | Task 11 |

**No placeholders, no TODOs, no "similar to task N" references. All code blocks are complete.**
