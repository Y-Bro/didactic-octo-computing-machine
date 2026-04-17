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
