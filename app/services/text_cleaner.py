import re


def clean_text(raw_text: str) -> str:
    """Clean extracted PDF text for Gemini processing.

    - Collapses multiple newlines into paragraph breaks
    - Removes excessive whitespace
    - Strips non-printable characters
    """
    # Remove null bytes and other non-printable chars (except newlines)
    text = re.sub(r"[^\x20-\x7E\n]", "", raw_text)

    # Replace 3+ newlines with 2 (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces into one
    text = re.sub(r" {2,}", " ", text)

    # Strip leading/trailing whitespace per line, then whole string
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    return text
