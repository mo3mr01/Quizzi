import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    """Extract all text from a PDF file.

    Args:
        file_bytes: Raw bytes of the uploaded PDF.

    Returns:
        A tuple of (full_text, page_count).
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text_parts.append(page.get_text())
    page_count = len(doc)
    doc.close()

    full_text = "\n".join(text_parts).strip()
    return full_text, page_count
