import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from app.config import GEMINI_MODEL, GOOGLE_API_KEY, PROMPT_DIR, llm_enabled
from core.classifier import experience_level, parse_year_bounds, requested_field, years_in_range
from core.retriever import retrieve
from core.skills import extract_skills, role_match, skill_overlap
from core.vector_store import all_profiles, profile_for
from models.query import AnalysisResponse, RankedCandidate, SourceChunk

PROMPT_FILES = {
    "analyse": "analyse_prompt.txt",
    "match": "match_prompt.txt",
    "gap": "gap_prompt.txt",
    "summary": "summary_prompt.txt",
}


def _load_prompt(kind: str) -> str:
    return (PROMPT_DIR / PROMPT_FILES.get(kind, PROMPT_FILES["analyse"])).read_text(encoding="utf-8")


def _sources(hits: list[dict]) -> list[SourceChunk]:
    sources = []
    for hit in hits:
        meta = hit["metadata"]
        sources.append(
            SourceChunk(
                candidate=str(meta.get("candidate", "Unknown")),
                filename=str(meta.get("filename", "")),
                section=str(meta.get("section", "general")),
                chunk_index=int(meta.get("chunk_index", 0)),
                text=hit["text"],
                score=float(hit["score"]),
            )
        )
    return sources


def _context(hits: list[dict]) -> str:
    blocks = []
    for hit in hits:
        meta = hit["metadata"]
        header = f"[{meta.get('candidate', 'Unknown')} | {meta.get('section', 'general')}]"
        blocks.append(f"{header}\n{hit['text']}")
    return "\n\n".join(blocks)


def _call_gemini(prompt: str) -> dict | None:
    if not llm_enabled():
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json(text)
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("LLM response did not contain JSON")
    return json.loads(text[start : end + 1])


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip() for part in parts if len(part.strip()) > 40]


def _local_answer(query: str, hits: list[dict], job_description: str = "") -> dict:
    top = hits[0]
    top_name = top["metadata"].get("candidate", "Unknown")
    top_blob = "\n".join(
        hit["text"] for hit in hits if hit["metadata"].get("candidate", "Unknown") == top_name
    )
    resume_skills = extract_skills(top_blob)
    jd_skills = extract_skills(job_description) if job_description else []
    matched, missing, score = skill_overlap(jd_skills, resume_skills) if jd_skills else ([], [], None)

    candidates = []
    for hit in hits:
        name = hit["metadata"].get("candidate", "Unknown")
        if name not in candidates:
            candidates.append(name)

    snippet = " ".join(top["text"].split())
    if len(snippet) > 420:
        snippet = snippet[:420].rsplit(" ", 1)[0] + "..."
    if len(candidates) > 1:
        answer = f"{top_name} is the closest match. Also retrieved: {', '.join(candidates[1:])}. {snippet}"
    else:
        answer = f"{top_name} is the closest match. {snippet}"

    summary_bits = _sentences(top_blob)[:3]
    summary = " ".join(summary_bits) if summary_bits else snippet
    if matched or missing:
        answer = (
            f"Match score {score}%. Found: {', '.join(matched) or 'none'}. "
            f"Missing: {', '.join(missing) or 'none'}."
        )
    return {
        "answer": answer,
        "skills_found": matched or resume_skills,
        "missing_skills": missing,
        "match_score": score,
        "summary": summary,
    }


def _score_resume(resume_text: str, job_description: str, name: str = "", field: str = "", title: str = "") -> dict:
    skill_matched, skill_missing, skill_score = skill_overlap(
        extract_skills(job_description), extract_skills(resume_text)
    )
    role_score, roles_found, roles_missing = role_match(job_description, field, title)
    if role_score is None:
        score = skill_score
    elif not extract_skills(job_description):
        score = role_score
    elif role_score == 0:
        score = round(skill_score * 0.25)
    else:
        score = round(0.55 * role_score + 0.45 * skill_score)

    matched = roles_found + [skill for skill in skill_matched if skill not in roles_found]
    missing = roles_missing + [skill for skill in skill_missing if skill not in roles_missing]
    who = name or "This candidate"
    role = ", ".join(part for part in (field, title) if part)
    prefix = f"{who} ({role})" if role else who
    if role_score == 0:
        answer = (
            f"{prefix} is not a match for this role. "
            f"Missing: {', '.join(missing) or 'the requested role'}."
        )
    elif score == 0 and role_score is None:
        answer = (
            f"{prefix}: no role or listed skill in that text matched this resume. "
            "Try a role such as data scientist, cybersecurity analyst, or software engineer, "
            "or name the skills you need."
        )
    else:
        answer = (
            f"{prefix} matches {score}%. "
            f"Found: {', '.join(matched) or 'none'}. "
            f"Missing: {', '.join(missing) or 'none'}."
        )
    return {
        "answer": answer,
        "skills_found": matched,
        "missing_skills": missing,
        "match_score": score,
        "summary": answer,
    }


def analyse(
    query: str,
    candidate: str | None = None,
    job_description: str = "",
    kind: str = "analyse",
    n_results: int = 5,
) -> AnalysisResponse:
    profile = profile_for(candidate) if candidate and job_description else None
    if profile:
        hits = [
            {
                "text": profile["text"][:1500],
                "metadata": {
                    "candidate": profile["candidate"],
                    "filename": profile["filename"],
                    "section": profile["field"] or "general",
                    "chunk_index": 0,
                },
                "score": 1.0,
            }
        ]
    else:
        hits = retrieve(query if not job_description else f"{query}\n{job_description}", n_results=n_results, candidate=candidate)
    sources = _sources(hits)
    if not hits:
        return AnalysisResponse(
            answer="Not found in resume. Upload resumes before asking a question.",
            sources=[],
            mode="local",
        )

    prompt = _load_prompt(kind).format(
        context=_context(hits),
        query=query,
        job_description=job_description or "Not provided.",
    )
    local_score = None
    resume_text = profile["text"] if profile else _context(hits)
    if job_description:
        local_score = _score_resume(
            resume_text,
            job_description,
            name=candidate or (hits[0]["metadata"].get("candidate") if hits else ""),
            field=(profile or {}).get("field", ""),
            title=(profile or {}).get("title", ""),
        )

    generated = None if job_description else _call_gemini(prompt)
    mode = "gemini" if generated else "local"
    if local_score:
        generated = local_score
        mode = "local"
    elif not generated:
        generated = _local_answer(query, hits, job_description)

    score = generated.get("match_score")
    if isinstance(score, str) and score.isdigit():
        score = int(score)
    if not isinstance(score, int):
        score = None

    skills = generated.get("skills_found") or []
    if isinstance(skills, str):
        skills = [skills]
    missing = generated.get("missing_skills") or []

    return AnalysisResponse(
        answer=str(generated.get("answer") or "Not found in resume."),
        skills_found=[str(skill) for skill in skills],
        missing_skills=[str(skill) for skill in missing],
        match_score=score,
        summary=str(generated.get("summary") or ""),
        sources=sources,
        mode=mode,
    )


def rank_against_job(job_description: str, limit: int = 20) -> list[RankedCandidate]:
    ranked: list[RankedCandidate] = []
    for profile in all_profiles():
        scored = _score_resume(
            profile["text"],
            job_description,
            name=profile["candidate"],
            field=profile.get("field", ""),
            title=profile.get("title", ""),
        )
        ranked.append(
            RankedCandidate(
                candidate=profile["candidate"],
                filename=profile["filename"],
                field=profile.get("field", ""),
                title=profile.get("title", ""),
                match_score=scored["match_score"],
                skills_found=scored["skills_found"],
                missing_skills=scored["missing_skills"],
                summary=scored["summary"],
            )
        )
    ranked.sort(key=lambda item: (-item.match_score, item.candidate.lower()))
    return ranked[:limit] if limit else ranked


def _ai_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def interpret_candidate(profile: dict, scored: dict) -> str:
    years = profile.get("years") or "unknown"
    level = profile.get("level") or experience_level(years)
    education = profile.get("education") or "not listed"
    certs = profile.get("certifications") or "None"
    projects = profile.get("projects") or "0"
    salary = profile.get("salary") or "not listed"
    skills = profile.get("skills_line") or ", ".join(scored.get("skills_found") or []) or "not listed"
    missing = ", ".join(scored.get("missing_skills") or []) or "none for this query"
    return (
        f"{profile['candidate']} is a {level} {profile.get('title') or profile.get('field') or 'candidate'} "
        f"with {years} years of experience. Education: {education}. "
        f"Certifications: {certs}. Skills: {skills}. Projects: {projects}. "
        f"Current salary: ${salary}. AI score: {profile.get('ai_score') or 'n/a'}. "
        f"Match to this query: {scored.get('match_score', 0)}%. "
        f"Gaps vs the query: {missing}."
    )


def screen_query(query: str, minimum: int = 5) -> dict:
    scored_rows: list[tuple[dict, dict]] = []
    for profile in all_profiles():
        scored = _score_resume(
            profile["text"],
            query,
            name=profile["candidate"],
            field=profile.get("field", ""),
            title=profile.get("title", ""),
        )
        scored_rows.append((profile, scored))
    matches = [(profile, scored) for profile, scored in scored_rows if scored["match_score"] > 0]
    wanted_field = requested_field(query)
    year_low, year_high = parse_year_bounds(query)
    lowered_q = query.lower()

    # Detect experience-level keywords and filter by pre-computed level label
    wanted_level: str | None = None
    if re.search(r"\bfresher\b|\bjunior\b|\bentry[- ]level\b", lowered_q):
        wanted_level = "Fresher"
    elif re.search(r"\bmid[- ]?level\b|\bmidlevel\b", lowered_q):
        wanted_level = "Mid-level"
    elif re.search(r"\bsenior\b", lowered_q):
        wanted_level = "Senior"

    # Filter by field only if the query explicitly names one
    if wanted_field:
        matches = [
            item for item in matches if (item[0].get("field") or "Unspecified") == wanted_field
        ]
    # Filter by level label (most reliable — uses stored computed value)
    if wanted_level:
        matches = [
            item for item in matches
            if (item[0].get("level") or experience_level(item[0].get("years", ""))) == wanted_level
        ]
    elif year_low is not None or year_high is not None:
        # Fall back to year-range only when no level keyword was found
        matches = [
            item
            for item in matches
            if years_in_range(item[0].get("years"), year_low, year_high)
        ]
    matches.sort(key=lambda item: (-item[1]["match_score"], item[0]["candidate"].lower()))
    if not matches:
        hint = ""
        if wanted_field:
            hint += f" in {wanted_field}"
        if wanted_level:
            hint += f" at {wanted_level} level"
        elif year_low is not None or year_high is not None:
            hint += " for that experience range"
        return {"field": wanted_field or "", "group": f"Nobody matched that query{hint}.", "people": []}

    # Build field distribution for the summary line
    field_counts: dict[str, int] = {}
    for profile, _scored in matches:
        field = profile.get("field") or "Unspecified"
        field_counts[field] = field_counts.get(field, 0) + 1

    # When a specific field was requested use that; otherwise show all matches
    if wanted_field:
        section = [(profile, scored) for profile, scored in matches if (profile.get("field") or "Unspecified") == wanted_field]
        display_field = wanted_field
    else:
        section = matches          # show everyone across all fields
        display_field = "All Fields"

    levels: dict[str, int] = {}
    for profile, _ in section:
        level = profile.get("level") or experience_level(profile.get("years", ""))
        levels[level] = levels.get(level, 0) + 1
    skill_hits: dict[str, int] = {}
    for profile, _ in section:
        for skill in (profile.get("skills_line") or "").split(","):
            skill = skill.strip()
            if skill:
                skill_hits[skill] = skill_hits.get(skill, 0) + 1
    common = ", ".join(name for name, _count in sorted(skill_hits.items(), key=lambda item: (-item[1], item[0].lower()))[:6]) or "not listed"
    mix = ", ".join(f"{count} {name}" for name, count in sorted(levels.items()))
    fields_summary = ", ".join(f"{f} ({c})" for f, c in sorted(field_counts.items(), key=lambda x: -x[1]))
    level_tag = f" [{wanted_level}]" if wanted_level else ""
    group = (
        f"{len(section)}{level_tag} candidates matched this query across {len(field_counts)} field(s): {fields_summary}. "
        f"Experience mix: {mix or 'n/a'}. Common skills: {common}."
    )
    people = []
    for profile, scored in section:
        people.append(
            {
                "profile": profile,
                "score": scored["match_score"],
                "found": scored["skills_found"],
                "missing": scored["missing_skills"],
                "interpretation": interpret_candidate(profile, scored),
            }
        )
    return {"field": display_field, "group": group, "people": people}


def interpret_field(field: str) -> dict:
    def _in_field(profile: dict) -> bool:
        all_f = profile.get("all_fields") or profile.get("field") or ""
        return field in [f.strip() for f in all_f.split("|")]

    people = [profile for profile in all_profiles() if _in_field(profile)]
    people.sort(key=lambda item: item["candidate"].lower())
    if not people:
        return {"field": field, "group": "No candidates in this field.", "people": []}
    levels: dict[str, int] = {}
    for profile in people:
        level = profile.get("level") or experience_level(profile.get("years", ""))
        levels[level] = levels.get(level, 0) + 1
    mix = ", ".join(f"{count} {name}" for name, count in sorted(levels.items()))
    group = f"{field} has {len(people)} candidates. Experience mix: {mix}."
    rows = []
    for profile in people:
        scored = {
            "match_score": 0,
            "skills_found": [part.strip() for part in (profile.get("skills_line") or "").split(",") if part.strip()],
            "missing_skills": [],
        }
        rows.append(
            {
                "profile": profile,
                "score": scored["match_score"],
                "found": scored["skills_found"],
                "missing": [],
                "interpretation": interpret_candidate(profile, scored),
            }
        )
    return {"field": field, "group": group, "people": rows}


def answer_question(question: str, candidate: str | None = None, minimum: int = 5) -> list[AnalysisResponse]:
    if candidate:
        return [analyse(question, candidate=candidate, n_results=minimum)]

    picked: list[tuple[dict, dict]] = []
    for profile in all_profiles():
        scored = _score_resume(
            profile["text"],
            question,
            name=profile["candidate"],
            field=profile.get("field", ""),
            title=profile.get("title", ""),
        )
        if scored["match_score"] > 0:
            picked.append((profile, scored))
    picked.sort(key=lambda item: (-item[1]["match_score"], item[0]["candidate"].lower()))
    picked = picked[:minimum]

    seen = {profile["candidate"] for profile, _ in picked}
    if len(picked) < minimum:
        for hit in retrieve(question, n_results=80):
            name = str(hit["metadata"].get("candidate", "Unknown"))
            if name in seen:
                continue
            profile = profile_for(name) or {
                "candidate": name,
                "filename": hit["metadata"].get("filename", ""),
                "field": hit["metadata"].get("field", ""),
                "title": hit["metadata"].get("title", ""),
                "text": hit["text"],
            }
            scored = _score_resume(
                profile["text"],
                question,
                name=name,
                field=profile.get("field", ""),
                title=profile.get("title", ""),
            )
            if scored["match_score"] == 0:
                snippet = " ".join(hit["text"].split())
                scored = {
                    "answer": f"{name} is a related resume. {snippet[:320]}",
                    "skills_found": [],
                    "missing_skills": [],
                    "match_score": max(1, round(float(hit["score"]) * 100)),
                    "summary": snippet[:320],
                }
            picked.append((profile, scored))
            seen.add(name)
            if len(picked) >= minimum:
                break

    results = []
    for profile, scored in picked:
        snippet = " ".join(profile["text"].split())
        if len(snippet) > 360:
            snippet = snippet[:360].rsplit(" ", 1)[0] + "..."
        results.append(
            AnalysisResponse(
                answer=scored["answer"],
                skills_found=scored["skills_found"],
                missing_skills=scored["missing_skills"],
                match_score=scored["match_score"],
                summary=snippet,
                sources=[
                    SourceChunk(
                        candidate=profile["candidate"],
                        filename=profile.get("filename", ""),
                        section=profile.get("field") or "general",
                        chunk_index=0,
                        text=snippet,
                        score=1.0,
                    )
                ],
                mode="local",
            )
        )
    return results


def prompt_path(kind: str) -> Path:
    return PROMPT_DIR / PROMPT_FILES.get(kind, PROMPT_FILES["analyse"])
