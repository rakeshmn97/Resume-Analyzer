import re
from pathlib import Path

from core.skills import extract_skills

SCREENING_FIELDS = [
    "AI Researcher",
    "Data Scientist",
    "Cybersecurity Analyst",
    "Software Engineer",
]

FIELD_SIGNALS = {
    "Data Scientist": {
        "titles": [
            "data scientist",
            "data analyst",
            "business analyst",
            "ml engineer",
            "ai/ml engineer",
            "aiml engineer",
            "machine learning engineer",
            "business analytics",
            "analytics intern",
        ],
        "skills": [
            "machine learning",
            "deep learning",
            "pandas",
            "numpy",
            "scikit-learn",
            "sql",
            "python",
            "tableau",
            "power bi",
            "xgboost",
            "statistics",
        ],
    },
    "AI Researcher": {
        "titles": [
            "ai researcher",
            "research scientist",
            "nlp engineer",
            "computer vision",
            "research intern",
        ],
        "skills": [
            "pytorch",
            "tensorflow",
            "nlp",
            "deep learning",
            "langchain",
            "transformer",
            "llm",
            "opencv",
        ],
    },
    "Software Engineer": {
        "titles": [
            "software engineer",
            "software developer",
            "full stack",
            "full-stack",
            "backend engineer",
            "frontend engineer",
            "web developer",
        ],
        "skills": [
            "django",
            "fastapi",
            "flask",
            "react",
            "javascript",
            "java",
            "c++",
            "rest",
            "html",
            "css",
            "node",
        ],
    },
    "Cybersecurity Analyst": {
        "titles": [
            "cybersecurity",
            "security analyst",
            "ethical hacker",
            "soc analyst",
            "information security",
        ],
        "skills": [
            "cybersecurity",
            "ethical hacking",
            "linux",
            "networking",
            "penetration",
            "siem",
        ],
    },
}

_OCR_FIXES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bbengalure\b", re.I), "Bengaluru"),
    (re.compile(r"\bbengalore\b", re.I), "Bengaluru"),
    (re.compile(r"\bbanglaore\b", re.I), "Bangalore"),
]


def _normalize_text(text: str) -> str:
    """Fix common OCR mis-reads before any extraction."""
    for pattern, replacement in _OCR_FIXES:
        text = pattern.sub(replacement, text)
    return text


_DEGREE = re.compile(
    r"\b(?:M\.?Sc|MBA|M\.?Tech|B\.?Tech|B\.?Sc|Ph\.?D|Bachelor(?:'s)?(?:\s+degree)?|Master(?:'s)?(?:\s+degree)?)\b[^\n|]{0,90}",
    re.I,
)
_YEARS = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs)\b", re.I)
_EDU_KEEP = re.compile(
    r"university|college|school|institute|msc|mba|m\.tech|b\.tech|bsc|ph\.d|bachelor|master|dublin|electronics|analytics",
    re.I,
)


def _has(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


def classify_field(text: str) -> tuple[str, str, int]:
    lowered = text.lower()
    head = lowered[:900]
    scores: dict[str, int] = {field: 0 for field in SCREENING_FIELDS}
    for field, signals in FIELD_SIGNALS.items():
        for title in signals["titles"]:
            if _has(head, title):
                scores[field] += 8
            elif _has(lowered, title):
                scores[field] += 4
        for skill in signals["skills"]:
            if _has(lowered, skill):
                scores[field] += 2
    field, score = max(scores.items(), key=lambda item: item[1])
    if score < 4:
        return "Unspecified", "Candidate", score
    title = _guess_title(head, field)
    return field, title, score


def classify_all_fields(text: str) -> list[str]:
    """Return every field whose score meets the threshold (multi-field support)."""
    lowered = text.lower()
    head = lowered[:900]
    scores: dict[str, int] = {field: 0 for field in SCREENING_FIELDS}
    for field, signals in FIELD_SIGNALS.items():
        for title in signals["titles"]:
            if _has(head, title):
                scores[field] += 8
            elif _has(lowered, title):
                scores[field] += 4
        for skill in signals["skills"]:
            if _has(lowered, skill):
                scores[field] += 2
    qualified = [f for f, s in scores.items() if s >= 4]
    if not qualified:
        return ["Unspecified"]
    # Sort: highest score first
    return sorted(qualified, key=lambda f: -scores[f])


def _guess_title(head: str, field: str) -> str:
    preferred = FIELD_SIGNALS[field]["titles"]
    for title in preferred:
        if _has(head, title):
            return title.title().replace("Ai/Ml", "AI/ML").replace("Aiml", "AI/ML")
    return field


def experience_level(years: str | int | float | None) -> str:
    try:
        value = float(str(years).strip())
    except (TypeError, ValueError):
        value = 0
    if value <= 3:
        return "Fresher"
    if value <= 6:
        return "Mid-level"
    return "Senior"


def extract_education(text: str) -> str:
    section_lines: list[str] = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip(" •-\t")
        if re.match(r"(?i)^education\b", stripped):
            capture = True
            rest = re.sub(r"(?i)^education\b[:\s|]*", "", stripped).strip()
            if rest and _EDU_KEEP.search(rest):
                section_lines.append(rest)
            continue
        if capture and re.match(
            r"(?i)^(certifications|projects|skills|experience|work experience|professional summary|screening)\b",
            stripped,
        ):
            break
        if capture and stripped and _EDU_KEEP.search(stripped):
            section_lines.append(stripped)
    if section_lines:
        unique: list[str] = []
        for item in section_lines:
            if item.lower() not in {existing.lower() for existing in unique}:
                unique.append(item)
        return "; ".join(unique[:4])

    found = [match.group(0).strip(" |,.") for match in _DEGREE.finditer(text)]
    unique = []
    for item in found:
        if "bengaluru" in item.lower() or "bangalore" in item.lower():
            continue
        if item.lower() not in {existing.lower() for existing in unique}:
            unique.append(item)
    return "; ".join(unique[:3])


def extract_years(text: str) -> str:
    matches = [int(match.group(1)) for match in _YEARS.finditer(text)]
    if matches:
        return str(max(matches))
    if re.search(r"intern", text, re.I):
        return "1"
    return "0"


def extract_certifications(text: str) -> str:
    lines = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^certifications?\b", stripped):
            capture = True
            continue
        if capture and re.match(r"(?i)^(education|projects|skills|experience|work)\b", stripped):
            break
        if capture and stripped:
            lines.append(stripped)
    if lines:
        return "; ".join(lines[:4])
    if re.search(r"udemy|coursera|aws certified|google ml", text, re.I):
        hits = re.findall(r"(Udemy|Coursera|AWS Certified|Google ML)[^\n]{0,60}", text, re.I)
        return "; ".join(hits[:3])
    return "None"


def extract_projects_count(text: str) -> str:
    capture = False
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^projects?\b", stripped):
            capture = True
            continue
        if capture and re.match(r"(?i)^(education|certifications|skills|experience)\b", stripped):
            break
        if capture and stripped and (stripped.startswith(("•", "-", "*")) or len(stripped) > 40):
            count += 1
    return str(count)


def extract_salary(text: str) -> str:
    match = re.search(
        r"(?:current\s+salary|salary|ctc|compensation)[^\d]{0,24}(?:rs\.?|inr|usd|\$)?\s*(\d[\d,]{2,})",
        text,
        re.I,
    )
    if match:
        return match.group(1).replace(",", "")
    match = re.search(r"\$\s*(\d[\d,]{3,})", text)
    if match:
        return match.group(1).replace(",", "")
    return ""


def compute_ai_score(profile: dict, text: str = "") -> int:
    score = 15
    field = profile.get("field") or "Unspecified"
    if field != "Unspecified":
        score += 20
    skills = [part for part in (profile.get("skills_line") or "").split(",") if part.strip()]
    score += min(25, len(skills) * 3)
    try:
        years = float(profile.get("years") or 0)
    except ValueError:
        years = 0
    score += min(15, int(years) * 2)
    try:
        projects = int(float(profile.get("projects") or 0))
    except ValueError:
        projects = 0
    score += min(15, projects * 3)
    education = (profile.get("education") or "").lower()
    if re.search(r"m\.?sc|m\.?tech|mba|ph\.?d|master", education):
        score += 10
    elif re.search(r"b\.?tech|b\.?sc|bachelor", education):
        score += 6
    certs = (profile.get("certifications") or "").strip()
    if certs and certs.lower() not in {"none", ""}:
        score += 5
    if re.search(r"python|sql|machine learning|tensorflow|pytorch", text.lower()):
        score += 5
    return max(0, min(100, score))


def requested_field(query: str) -> str | None:
    lowered = query.lower()
    names = sorted(SCREENING_FIELDS, key=len, reverse=True)
    for field in names:
        if field.lower() in lowered:
            return field
    aliases = {
        "ai researcher": "AI Researcher",
        "data scientist": "Data Scientist",
        "data analyst": "Data Scientist",
        "cybersecurity": "Cybersecurity Analyst",
        "software engineer": "Software Engineer",
        "software developer": "Software Engineer",
    }
    for phrase, field in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", lowered):
            return field
    return None


def parse_year_bounds(query: str) -> tuple[float | None, float | None]:
    lowered = query.lower()
    ranged = re.search(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:years?|yrs)?", lowered)
    if ranged and re.search(r"year|exp|fresher|experience", lowered):
        return float(ranged.group(1)), float(ranged.group(2))
    plus = re.search(r"(\d+)\s*\+\s*(?:years?|yrs)", lowered)
    if plus:
        return float(plus.group(1)), None
    over = re.search(r"(?:more than|above|over|greater than)\s*(\d+)\s*(?:years?|yrs)", lowered)
    if over:
        return float(over.group(1)) + 0.01, None
    if re.search(r"\bfresher\b|\bjunior\b|\bentry[- ]level\b", lowered):
        return 0.0, 3.0
    if re.search(r"\bmid[- ]level\b|\bmidlevel\b", lowered):
        return 4.0, 6.0
    if re.search(r"\bsenior\b", lowered) and re.search(r"year|exp|experience|level", lowered):
        return 7.0, None
    return None, None


def years_in_range(years: str | int | float | None, low: float | None, high: float | None) -> bool:
    try:
        value = float(str(years).strip())
    except (TypeError, ValueError):
        value = 0.0
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def profile_from_text(text: str, filename: str, candidate_name: str) -> dict:
    text = _normalize_text(text)
    field, title, _score = classify_field(text)
    skills = extract_skills(text)
    years = extract_years(text)
    all_fields = classify_all_fields(text)
    profile = {
        "candidate": candidate_name,
        "filename": Path(filename).name,
        "field": field,
        "all_fields": "|".join(all_fields),   # pipe-separated for metadata storage
        "title": title,
        "education": extract_education(text),
        "certifications": extract_certifications(text),
        "years": years,
        "level": experience_level(years),
        "salary": extract_salary(text),
        "decision": "",
        "projects": extract_projects_count(text),
        "skills_line": ", ".join(skill.title() if skill not in {"sql", "nlp"} else skill.upper() for skill in skills),
    }
    profile["ai_score"] = str(compute_ai_score(profile, text))
    return profile
