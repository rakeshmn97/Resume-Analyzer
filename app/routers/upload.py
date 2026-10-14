from datetime import datetime, timezone
from pathlib import Path

from app.config import UPLOAD_DIR
from core.chunker import chunk_text
from core.classifier import profile_from_text
from core.loader import guess_candidate_name, load_resume
from core.vector_store import add_chunks, delete_by_candidate, delete_by_filename, find_existing
from models.resume import Resume


def ingest_path(path: str, candidate_name: str | None = None, update_existing: bool = True) -> Resume:
    source = Path(path)
    text = load_resume(str(source))
    if not text:
        raise ValueError(f"No text extracted from {source.name}")
    name = (candidate_name or "").strip() or guess_candidate_name(text, source.name)
    uploaded = datetime.now(timezone.utc).isoformat(timespec="seconds")
    profile = profile_from_text(text, source.name, name)
    chunks = chunk_text(text, filename=source.name, candidate_name=name, upload_date=uploaded)
    extra = {
        "field": profile["field"],
        "all_fields": profile.get("all_fields", profile["field"]),
        "title": profile["title"],
        "education": profile["education"],
        "certifications": profile["certifications"],
        "years": profile["years"],
        "level": profile.get("level") or "",
        "salary": profile["salary"],
        "decision": profile["decision"],
        "ai_score": profile["ai_score"],
        "projects": profile["projects"],
        "skills_line": profile["skills_line"],
    }
    for chunk in chunks:
        chunk["metadata"].update(extra)
    if update_existing:
        delete_by_candidate(name)
    stored = add_chunks(chunks)
    return Resume(
        id=source.stem,
        name=name,
        filename=source.name,
        chunk_count=stored,
        skills=[part for part in profile["skills_line"].split(", ") if part] if profile["skills_line"] else [],
        field=profile["field"],
        title=profile["title"],
        salary=profile.get("salary") or "",
        ai_score=profile.get("ai_score") or "",
    )


def save_upload(filename: str, data: bytes) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    destination = UPLOAD_DIR / safe_name
    destination.write_bytes(data)
    return destination
