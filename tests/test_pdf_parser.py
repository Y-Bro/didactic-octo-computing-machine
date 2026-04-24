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
    # Use a 200x200 image so it passes the size filter
    pdf_bytes = make_pdf_with_image(200, 200)
    result = parse_pdf(pdf_bytes)
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


def make_png(w: int, h: int) -> bytes:
    """Create a minimal valid PNG of given dimensions."""
    import struct, zlib
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data
    ihdr += struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    raw = (b'\x00' + b'\xff\xff\xff' * w) * h
    idat_data = zlib.compress(raw)
    idat = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data
    idat += struct.pack('>I', zlib.crc32(b'IDAT' + idat_data) & 0xffffffff)
    iend = b'\x00\x00\x00\x00IEND\xaeB`\x82'
    return sig + ihdr + idat + iend


def make_pdf_with_image(img_w: int, img_h: int) -> bytes:
    """Create a PDF containing one image of the given pixel dimensions."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Content with image")
    rect = fitz.Rect(100, 100, 100 + img_w, 100 + img_h)
    page.insert_image(rect, stream=make_png(img_w, img_h))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_pdf_skips_images_smaller_than_200x200():
    """Images below 200x200 pixels must be filtered from the returned list."""
    pdf_bytes = make_pdf_with_image(10, 10)
    result = parse_pdf(pdf_bytes)
    assert result["images"] == [], "tiny image (10x10) should be filtered out"


def test_parse_pdf_keeps_images_at_least_200x200():
    """Images that meet the 200x200 threshold must be kept."""
    pdf_bytes = make_pdf_with_image(200, 200)
    result = parse_pdf(pdf_bytes)
    assert len(result["images"]) >= 1, "200x200 image should NOT be filtered"


def test_parse_pdf_skips_images_below_threshold_one_dimension():
    """Images where either dimension is below 200 must be filtered."""
    # 300 wide but only 50 tall — should be skipped
    pdf_bytes = make_pdf_with_image(300, 50)
    result = parse_pdf(pdf_bytes)
    assert result["images"] == [], "image with height<200 should be filtered"
