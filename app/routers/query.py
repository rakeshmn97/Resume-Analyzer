from core.llm_chain import analyse, answer_question, interpret_field, rank_against_job, screen_query
from models.query import AnalysisResponse, RankedCandidate


def ask(question: str, candidate: str | None = None, top_k: int = 5) -> list[AnalysisResponse]:
    return answer_question(question, candidate=candidate or None, minimum=top_k)


def match_job(job_description: str, candidate: str | None = None) -> AnalysisResponse:
    return analyse(
        "Score this candidate against the job description and explain the fit.",
        candidate=candidate or None,
        job_description=job_description,
        kind="match",
        n_results=8,
    )


def find_gaps(job_description: str, candidate: str) -> AnalysisResponse:
    return analyse(
        "Which required skills are missing from this resume?",
        candidate=candidate,
        job_description=job_description,
        kind="gap",
        n_results=8,
    )


def summarize(candidate: str) -> AnalysisResponse:
    return analyse(
        "Write a short executive summary of this candidate.",
        candidate=candidate,
        kind="summary",
        n_results=8,
    )


def rank(job_description: str) -> list[RankedCandidate]:
    return rank_against_job(job_description)


def screen(query: str, minimum: int = 5) -> dict:
    return screen_query(query, minimum=minimum)


def field_details(field: str) -> dict:
    return interpret_field(field)
