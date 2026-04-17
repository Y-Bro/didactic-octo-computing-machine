import base64
import io
from docx import Document
from docx.oxml.ns import qn


def parse_docx(docx_bytes: bytes) -> dict:
    """
    Returns {"text": str, "images": [{"data": base64_str, "mime_type": str, "page": None, "index": int}]}
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
