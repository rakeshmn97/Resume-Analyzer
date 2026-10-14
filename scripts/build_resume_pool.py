"""Generate distinct fictional CVs from many fields and index them."""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import ROOT as PROJECT_ROOT
from core.chunker import chunk_text
from core.embedder import get_embedder
from core.vector_store import clear_store, get_collection, list_candidates

POOL_DIR = PROJECT_ROOT / "data" / "uploads" / "cv_pool"
PER_ROLE = 25

FIRST_NAMES = [
    "Aisha", "Arjun", "Meera", "Kabir", "Ananya", "Vikram", "Sara", "Rohan",
    "Leila", "Dev", "Priya", "Omar", "Neha", "Hassan", "Isha", "Nikhil",
    "Fatima", "Aditya", "Maya", "Yusuf", "Diya", "Karthik", "Hana", "Rahul",
    "Zara", "Sanjay", "Amira", "Varun", "Noor", "Amit", "Layla", "Kiran",
    "Elena", "Marcus", "Sofia", "Jonah", "Clara", "Andre", "Nadia", "Luis",
    "Hannah", "Owen", "Grace", "Felix", "Ines", "Theo", "Samuel", "Chloe", "Daniel",
]
LAST_NAMES = [
    "Sharma", "Iyer", "Mehta", "Rahman", "Khan", "Nair", "Patel", "Das",
    "Reddy", "Singh", "Joseph", "Fernandes", "Banerjee", "Chowdhury", "Gupta",
    "Kapoor", "Malhotra", "Qureshi", "Siddiqui", "Almeida", "D'Souza", "Menon",
    "Berg", "Costa", "Novak", "Okeke", "Silva", "Park", "Nguyen", "Rossi",
    "Keller", "Ahmed", "Moreau", "Ibrahim", "Santos", "Okafor", "Petrov",
    "Hughes", "Laurent", "Yamamoto",
]
CITIES = [
    "Bengaluru", "Hyderabad", "Pune", "Chennai", "Mumbai", "Delhi", "Kochi",
    "Jaipur", "Kolkata", "Ahmedabad", "London", "Berlin", "Toronto", "Singapore",
    "Dubai", "Nairobi", "Austin", "Lisbon", "Dublin", "Melbourne",
]

ROLES = [
    ("Nursing", "ICU Nurse", ["patient care", "icu", "medication administration", "ward rounds"], "critical care and medication safety"),
    ("Pharmacy", "Clinical Pharmacist", ["dispensing", "pharmacology", "drug interaction"], "safe dispensing and medication review"),
    ("Teaching", "Secondary School Teacher", ["lesson planning", "classroom management", "curriculum"], "classroom teaching and assessment"),
    ("Accounting", "Accountant", ["bookkeeping", "audit", "taxation", "gst", "reconciliation"], "books, tax filings, and audit support"),
    ("Civil Engineering", "Site Engineer", ["autocad", "site supervision", "structural drawings"], "site execution and drawing control"),
    ("Mechanical Engineering", "Maintenance Engineer", ["hvac", "manufacturing", "quality control"], "plant maintenance and equipment uptime"),
    ("Graphic Design", "Graphic Designer", ["figma", "branding", "typography"], "brand systems and campaign layouts"),
    ("Marketing", "Digital Marketer", ["seo", "social media", "branding"], "search and social campaigns"),
    ("Human Resources", "HR Generalist", ["recruitment", "payroll", "onboarding", "employee relations"], "hiring, payroll, and employee relations"),
    ("Hospitality", "Front Office Manager", ["guest relations", "front office", "housekeeping"], "guest arrival and hotel operations"),
    ("Culinary", "Chef", ["food safety", "menu planning"], "kitchen production and menu development"),
    ("Law", "Associate Lawyer", ["legal research", "litigation", "contract drafting"], "research, hearings, and contracts"),
    ("Journalism", "Reporter", ["news reporting", "interviewing"], "daily reporting and source interviews"),
    ("Agriculture", "Farm Supervisor", ["crop planning", "irrigation", "soil management"], "season planning and field operations"),
    ("Architecture", "Architect", ["revit", "architectural drawings", "site supervision"], "design development and site reviews"),
    ("Electrical Engineering", "Electrical Engineer", ["wiring", "plc", "quality control"], "panels, wiring, and controls"),
    ("Sales", "Account Executive", ["negotiation", "crm"], "pipeline management and deal negotiation"),
    ("Customer Support", "Support Lead", ["ticketing", "crm"], "queue management and response quality"),
    ("Logistics", "Warehouse Supervisor", ["warehouse", "dispatch"], "inbound goods and dispatch planning"),
    ("Finance", "Financial Analyst", ["forecasting", "budgeting", "financial modeling", "excel"], "budgets and management forecasts"),
    ("Software", "Backend Engineer", ["python", "django", "postgresql", "docker", "rest"], "APIs and relational data"),
    ("Software", "Frontend Engineer", ["javascript", "typescript", "react", "html", "css"], "web interfaces"),
    ("Data Science", "Machine Learning Engineer", ["python", "machine learning", "pytorch", "pandas", "aws"], "models and evaluation"),
    ("Laboratory", "Lab Technologist", ["sample processing", "pathology", "quality control"], "specimen handling and result quality"),
]


def unique_names(count: int) -> list[str]:
    names: list[str] = []
    for last in LAST_NAMES:
        for first in dict.fromkeys(FIRST_NAMES):
            names.append(f"{first} {last}")
            if len(names) == count:
                return names
    raise RuntimeError("Not enough unique names")


def chosen_skills(skills: list[str], index: int) -> list[str]:
    drop_at = index % (len(skills) + 1)
    kept = [skill for position, skill in enumerate(skills) if position != drop_at]
    return kept or skills[:1]


def build_resume(index: int, name: str, role: tuple) -> str:
    field, title, skills, focus = role
    kept = chosen_skills(skills, index)
    years = 2 + (index % 12)
    start_year = 2024 - years
    city = CITIES[index % len(CITIES)]
    email = name.lower().replace(" ", ".").replace("'", "") + f".{index + 1}@example.com"
    skill_line = ", ".join(kept)
    return f"""{name}
{title}
Field: {field}
{email} | {city}

Summary:
{title} in {field.lower()} with {years} years focused on {focus}. Based in {city}. Candidate reference {index + 1}.

Skills:
{skill_line}

Experience:
{field} practice — {title}, {start_year} to present
Handled {focus} for a team in {city}. The work depended on {kept[0]} and {kept[min(1, len(kept) - 1)]}. Improved a core operating result by {8 + (index % 20)} percent.

Earlier role — Assistant {title}, {start_year - 2} to {start_year}
Supported day-to-day {field.lower()} work and documented procedures for the next shift.

Education:
Bachelor's degree related to {field}, State University, {start_year - 6}

Projects:
A {field.lower()} improvement project covering {", ".join(kept)}. Wrote the handover notes for the incoming team.
"""


def main() -> None:
    assignments = [(role, offset) for role in ROLES for offset in range(PER_ROLE)]
    names = unique_names(len(assignments))
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    for old in POOL_DIR.glob("*.txt"):
        old.unlink()

    uploaded = datetime.now(timezone.utc).isoformat(timespec="seconds")
    chunks = []
    for index, ((role, _offset), name) in enumerate(zip(assignments, names)):
        field, title, _, _ = role
        filename = f"{index + 1:03d}_{name.lower().replace(' ', '_').replace(chr(39), '')}.txt"
        text = build_resume(index, name, role)
        (POOL_DIR / filename).write_text(text, encoding="utf-8")
        for chunk in chunk_text(text, filename=filename, candidate_name=name, upload_date=uploaded):
            chunk["metadata"]["field"] = field
            chunk["metadata"]["title"] = title
            chunks.append(chunk)

    clear_store()
    embedder = get_embedder()
    collection = get_collection(embedder)
    batch_size = 128
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.add(
            documents=[item["text"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
            embeddings=embedder.embed_documents([item["text"] for item in batch]),
            ids=[f'{item["metadata"]["filename"]}::{item["metadata"]["chunk_index"]}' for item in batch],
        )
        print(f"indexed chunks {start + len(batch)}/{len(chunks)}", flush=True)

    people = list_candidates()
    fields = sorted({person.get("field", "") for person in people})
    print(f"candidates {len(people)} chunks {collection.count()} fields {len(fields)}", flush=True)


if __name__ == "__main__":
    main()
