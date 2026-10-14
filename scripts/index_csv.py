"""Index AI_Resume_Screening.csv into the RAG store."""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import CSV_PATH
from core.embedder import get_embedder
from core.vector_store import clear_store, get_collection, list_candidates


def row_to_text(row: dict) -> str:
    name = row["Name"].strip()
    role = row["Job Role"].strip()
    skills = row["Skills"].strip()
    return f"""{name}
{role}
Field: {role}

Summary:
{role} with {row['Experience (Years)']} years of experience. Education: {row['Education']}. Certifications: {row['Certifications']}.

Skills:
{skills}

Experience:
{row['Experience (Years)']} years in {role}. Completed {row['Projects Count']} projects.

Education:
{row['Education']}

Certifications:
{row['Certifications']}

Screening notes:
Recruiter decision {row['Recruiter Decision']}. Dataset AI score {row['AI Score (0-100)']}. Salary expectation {row['Salary Expectation ($)']}.
"""


def row_metadata(row: dict, filename: str) -> dict:
    name = row["Name"].strip()
    role = row["Job Role"].strip()
    resume_id = str(row["Resume_ID"]).strip()
    return {
        "filename": filename,
        "candidate": f"{name} #{resume_id}",
        "chunk_index": 0,
        "section": "profile",
        "field": role,
        "title": role,
        "education": str(row["Education"]).strip(),
        "certifications": str(row["Certifications"]).strip(),
        "years": str(row["Experience (Years)"]).strip(),
        "salary": str(row["Salary Expectation ($)"]).strip(),
        "decision": str(row["Recruiter Decision"]).strip(),
        "ai_score": str(row["AI Score (0-100)"]).strip(),
        "projects": str(row["Projects Count"]).strip(),
        "skills_line": str(row["Skills"]).strip(),
        "resume_id": resume_id,
        "upload_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)
    rows = load_rows(CSV_PATH)
    documents = []
    metadatas = []
    ids = []
    for row in rows:
        resume_id = str(row["Resume_ID"]).strip()
        filename = f"csv_{resume_id}.txt"
        documents.append(row_to_text(row))
        metadatas.append(row_metadata(row, filename))
        ids.append(f"{filename}::0")

    clear_store()
    embedder = get_embedder()
    collection = get_collection(embedder)
    batch_size = 64
    for start in range(0, len(documents), batch_size):
        batch_docs = documents[start : start + batch_size]
        batch_meta = metadatas[start : start + batch_size]
        batch_ids = ids[start : start + batch_size]
        collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            embeddings=embedder.embed_documents(batch_docs),
            ids=batch_ids,
        )
        print(f"indexed {start + len(batch_docs)}/{len(documents)}", flush=True)
    people = list_candidates()
    fields = sorted({person.get("field", "") for person in people})
    print(f"candidates {len(people)} fields {fields}", flush=True)


if __name__ == "__main__":
    main()
