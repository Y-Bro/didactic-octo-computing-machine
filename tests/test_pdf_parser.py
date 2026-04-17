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
    """Image dicts must have data, mime_type, page, and index keys."""
    import struct, zlib
    # Create a minimal valid PNG (1x1 white pixel)
    def make_png():
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr = b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
        idat_data = zlib.compress(b'\x00\xff\xff\xff')
        idat = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data
        idat += struct.pack('>I', zlib.crc32(b'IDAT' + idat_data) & 0xffffffff)
        iend = b'\x00\x00\x00\x00IEND\xaeB`\x82'
        return sig + ihdr + idat + iend

    png_bytes = make_png()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Some content")
    rect = fitz.Rect(100, 100, 200, 200)
    page.insert_image(rect, stream=png_bytes)
    buf = io.BytesIO()
    doc.save(buf)

    result = parse_pdf(buf.getvalue())
    assert len(result["images"]) >= 1
    img = result["images"][0]
    assert "data" in img
    assert "mime_type" in img
    assert "page" in img
    assert "index" in img


def test_parse_pdf_raises_on_empty_text():
    """Scanned PDFs produce no text — must raise ValueError."""
    doc = fitz.open()
    doc.new_page()  # blank page, no text
    buf = io.BytesIO()
    doc.save(buf)
    with pytest.raises(ValueError, match="PDF appears scanned"):
        parse_pdf(buf.getvalue())
