from pathlib import Path


def load_pdf(path: str) -> str:
    import fitz

    document = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in document)
    finally:
        document.close()


from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def load_docx(path: str) -> str:
    from docx import Document

    document = Document(path)
    parts: list[str] = []
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            text = Paragraph(child, document).text.strip()
            if text:
                parts.append(text)
        elif child.tag == qn("w:tbl"):
            table = Table(child, document)
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
    return "\n".join(parts)


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def load_resume(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        text = load_pdf(path)
    elif suffix == ".docx":
        text = load_docx(path)
    elif suffix == ".txt":
        text = load_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {path}")
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    cleaned = "\n".join(line for line in cleaned.splitlines())
    return cleaned.strip()


def guess_candidate_name(text: str, filename: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if len(candidate) <= 60 and not candidate.endswith(":") and "@" not in candidate:
            return candidate
        break
    return Path(filename).stem.replace("_", " ").replace("-", " ")
