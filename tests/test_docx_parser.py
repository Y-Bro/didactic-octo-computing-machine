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


def test_parse_docx_extracts_table_cell_text():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Phase"
    table.cell(0, 1).text = "Build"
    buf = io.BytesIO()
    doc.save(buf)
    result = parse_docx(buf.getvalue())
    assert "Phase" in result["text"]
    assert "Build" in result["text"]
