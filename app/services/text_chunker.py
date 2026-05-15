CHUNK_SIZE = 1500  # target characters per chunk
CHUNK_OVERLAP = 100  # overlap to avoid cutting sentences mid-thought


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split cleaned text into overlapping chunks.

    Args:
        text: Cleaned text string.
        chunk_size: Max characters per chunk.
        overlap: Overlap characters between chunks.

    Returns:
        List of text chunks.
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a paragraph or sentence boundary near the end
        if end < len(text):
            # Look backwards for a paragraph break
            last_para = chunk.rfind("\n\n")
            if last_para > chunk_size // 2:
                end = start + last_para
                chunk = text[start:end]
            else:
                # Look backwards for a sentence end
                last_sentence = max(
                    chunk.rfind(". "),
                    chunk.rfind("?\n"),
                    chunk.rfind("!\n"),
                )
                if last_sentence > chunk_size // 2:
                    end = start + last_sentence + 1
                    chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - overlap if end < len(text) else len(text)

    return chunks
