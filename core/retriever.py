from core.vector_store import list_candidates, search


def retrieve(query: str, n_results: int = 5, candidate: str | None = None) -> list[dict]:
    where = {"candidate": candidate} if candidate else None
    return search(query, n_results=n_results, where=where)


def retrieve_for_candidate(candidate: str, query: str, n_results: int = 8) -> list[dict]:
    return retrieve(query, n_results=n_results, candidate=candidate)


def all_candidate_names() -> list[str]:
    return [item["candidate"] for item in list_candidates()]
