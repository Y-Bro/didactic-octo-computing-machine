import base64
import fitz  # pymupdf


def parse_pdf(pdf_bytes: bytes) -> dict:
    """
    Returns {"text": str, "images": [{"data": base64_str, "mime_type": str, "page": int, "index": int}]}
    Raises ValueError if no text is found (likely scanned PDF).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    images = []
    seen_xrefs = set()

    try:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(text)

            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                base_image = doc.extract_image(xref)
                if base_image["width"] < 200 or base_image["height"] < 200:
                    continue
                image_bytes = base_image["image"]
                images.append({
                    "data": base64.b64encode(image_bytes).decode("utf-8"),
                    "mime_type": f"image/{base_image['ext']}",
                    "page": page_num + 1,
                    "index": img_index,
                })
    finally:
        doc.close()

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise ValueError("PDF appears scanned — no extractable text found. OCR is not supported.")

    return {"text": full_text, "images": images}
