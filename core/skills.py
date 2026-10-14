import re

SKILL_LEXICON = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql", "nosql",
    "react", "next.js", "node", "angular", "vue", "html", "css",
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git",
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "pandas", "numpy", "scikit-learn", "spark", "hadoop",
    "postgresql", "mysql", "mongodb", "redis",
    "fastapi", "django", "flask", "streamlit", "langchain",
    "excel", "tableau", "power bi", "powerbi",
    "rest", "graphql", "microservices", "ci/cd",
    "communication", "leadership", "teamwork", "problem solving",
    "xgboost", "opencv",
    "ethical hacking", "cybersecurity", "networking",
    "patient care", "medication administration", "icu", "ward rounds",
    "dispensing", "pharmacology", "drug interaction",
    "lesson planning", "classroom management", "curriculum",
    "bookkeeping", "audit", "taxation", "gst", "reconciliation",
    "autocad", "site supervision", "structural drawings",
    "hvac", "manufacturing", "figma", "branding", "typography",
    "seo", "social media", "recruitment", "payroll", "onboarding",
    "employee relations", "guest relations", "front office", "housekeeping",
    "food safety", "menu planning", "legal research", "litigation", "contract drafting",
    "news reporting", "interviewing", "crop planning", "irrigation", "soil management",
    "revit", "architectural drawings", "wiring", "plc", "negotiation", "crm",
    "ticketing", "warehouse", "dispatch", "forecasting", "budgeting", "financial modeling",
    "sample processing", "pathology", "quality control",
]

SOFT_SKILLS = {"communication", "leadership", "teamwork", "problem solving"}

# Job-title words mapped to the words that appear in a matching field or title.
ROLE_TERMS = {
    "secondary school teacher": ("teacher", "teaching"),
    "school teacher": ("teacher", "teaching"),
    "teacher": ("teacher", "teaching"),
    "teachers": ("teacher", "teaching"),
    "teaching": ("teacher", "teaching"),
    "tutor": ("teacher", "teaching"),
    "icu nurse": ("nurse", "nursing"),
    "nurse": ("nurse", "nursing"),
    "nurses": ("nurse", "nursing"),
    "nursing": ("nurse", "nursing"),
    "pharmacist": ("pharmacist", "pharmacy"),
    "pharmacy": ("pharmacist", "pharmacy"),
    "accountant": ("accountant", "accounting"),
    "accounting": ("accountant", "accounting"),
    "lawyer": ("lawyer", "law"),
    "attorney": ("lawyer", "law"),
    "chef": ("chef", "culinary"),
    "cook": ("chef", "culinary"),
    "journalist": ("reporter", "journalism"),
    "reporter": ("reporter", "journalism"),
    "architect": ("architect", "architecture"),
    "recruiter": ("hr", "human resources"),
    "human resources": ("hr", "human resources"),
    "graphic designer": ("designer", "graphic design"),
    "designer": ("designer", "graphic design"),
    "frontend": ("frontend",),
    "front end": ("frontend",),
    "front-end": ("frontend",),
    "backend": ("backend",),
    "back end": ("backend",),
    "back-end": ("backend",),
    "ai researcher": ("ai researcher",),
    "researcher": ("researcher",),
    "data scientist": ("data scientist", "data science"),
    "data science": ("data scientist", "data science"),
    "cybersecurity analyst": ("cybersecurity analyst", "cybersecurity"),
    "security analyst": ("cybersecurity analyst", "cybersecurity"),
    "cybersecurity": ("cybersecurity",),
    "ethical hacking": ("ethical hacking", "cybersecurity"),
    "software engineer": ("software engineer", "software"),
    "software developer": ("software engineer", "software"),
    "developer": ("software engineer", "software"),
    "software": ("software engineer", "software"),
    "data analyst": ("data scientist", "data analyst", "analytics"),
    "ai/ml engineer": ("data scientist", "machine learning"),
    "ml engineer": ("data scientist", "machine learning"),
    "machine learning engineer": ("data scientist", "machine learning"),
    "civil engineer": ("civil",),
    "civil": ("civil",),
    "mechanical": ("mechanical",),
    "electrical": ("electrical",),
    "marketer": ("marketer", "marketing"),
    "marketing": ("marketer", "marketing"),
    "hospitality": ("hospitality", "front office"),
    "hotel": ("hospitality", "front office"),
    "warehouse": ("warehouse", "logistics"),
    "logistics": ("warehouse", "logistics"),
    "sales": ("sales", "account executive"),
    "customer support": ("support",),
    "support lead": ("support",),
    "finance": ("finance", "financial"),
    "financial analyst": ("finance", "financial"),
    "lab technologist": ("lab", "laboratory"),
    "laboratory": ("lab", "laboratory"),
    "pathologist": ("pathology", "laboratory"),
    "farmer": ("farm", "agriculture"),
    "agriculture": ("farm", "agriculture"),
}

_ROLE_PHRASES = sorted(ROLE_TERMS, key=len, reverse=True)

_SORTED = sorted(SKILL_LEXICON, key=len, reverse=True)


def _has_term(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for skill in _SORTED:
        if _has_term(lowered, skill) and skill not in found:
            found.append(skill)
    return found


def role_match(job_description: str, field: str, title: str) -> tuple[int | None, list[str], list[str]]:
    """Return how well a job title request fits this candidate.

    The score is None when the text does not name a role.
    """
    jd = job_description.lower()
    hay = f"{field} {title}".lower()
    asked = [phrase for phrase in _ROLE_PHRASES if _has_term(jd, phrase)]
    if not asked:
        return None, [], []
    # Prefer the longest phrase so "icu nurse" does not also count as "nurse".
    kept: list[str] = []
    for phrase in asked:
        if any(_has_term(phrase, earlier) or _has_term(earlier, phrase) for earlier in kept):
            continue
        kept.append(phrase)
    matched = [phrase for phrase in kept if any(_has_term(hay, target) for target in ROLE_TERMS[phrase])]
    missing = [phrase for phrase in kept if phrase not in matched]
    score = round(100 * len(matched) / len(kept))
    return score, matched, missing


def skill_overlap(left: list[str], right: list[str]) -> tuple[list[str], list[str], int]:
    right_set = set(right)
    matched = [skill for skill in left if skill in right_set]
    missing = [skill for skill in left if skill not in right_set]
    if not left:
        return matched, missing, 0
    total = 0
    earned = 0
    for skill in left:
        weight = 1 if skill in SOFT_SKILLS else 3
        total += weight
        if skill in right_set:
            earned += weight
    return matched, missing, round(100 * earned / total)
