import re

from app.config import CHUNK_OVERLAP, CHUNK_SIZE

SECTION_PATTERN = re.compile(
    r"(?im)^(summary|profile|skills|technical skills|experience|work experience|"
    r"education|projects|certifications|achievements)\s*:?\s*$"
)


def _detect_section(text: str, current: str) -> str:
    match = SECTION_PATTERN.search(text[:80])
    if match:
        return match.group(1).strip().lower()
    return current


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    separators = ["\n\n", "\n", ". ", " "]
    pieces = [text.strip()]
    for separator in separators:
        next_pieces = []
        for piece in pieces:
            if len(piece) <= size:
                next_pieces.append(piece)
                continue
            parts = piece.split(separator)
            buffer = ""
            for part in parts:
                unit = part if not buffer else buffer + separator + part
                if len(unit) <= size:
                    buffer = unit
                else:
                    if buffer:
                        next_pieces.append(buffer)
                    buffer = part
            if buffer:
                next_pieces.append(buffer)
        pieces = [p.strip() for p in next_pieces if p.strip()]

    chunks: list[str] = []
    for piece in pieces:
        if len(piece) <= size:
            chunks.append(piece)
            continue
        start = 0
        while start < len(piece):
            end = min(start + size, len(piece))
            chunks.append(piece[start:end].strip())
            if end == len(piece):
                break
            start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def chunk_text(
    text: str,
    filename: str,
    candidate_name: str,
    upload_date: str = "",
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    blocks = re.split(r"\n(?=(?:[A-Z][A-Za-z ]{2,40}:\s*$))", text)
    if len(blocks) == 1:
        blocks = text.split("\n\n")

    section = "general"
    raw_chunks: list[tuple[str, str]] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        section = _detect_section(block, section)
        for piece in _split_long(block, chunk_size, chunk_overlap):
            raw_chunks.append((piece, section))

    if not raw_chunks and text.strip():
        raw_chunks.append((text.strip(), "general"))

    return [
        {
            "text": chunk,
            "metadata": {
                "filename": filename,
                "candidate": candidate_name,
                "chunk_index": index,
                "section": section_name,
                "upload_date": upload_date,
            },
        }
        for index, (chunk, section_name) in enumerate(raw_chunks)
    ]
