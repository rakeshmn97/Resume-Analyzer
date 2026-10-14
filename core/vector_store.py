import threading
from pathlib import Path

from app.config import CHROMA_PATH, COLLECTION_NAME
from core.classifier import experience_level
from core.embedder import Embedder, get_embedder

_client = None
_collection = None
_bound_model = None
_lock = threading.Lock()


def _open_client():
    import chromadb
    from chromadb.api.shared_system_client import SharedSystemClient

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    path = str(CHROMA_PATH.resolve())
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            return chromadb.PersistentClient(path=path)
        except (KeyError, ValueError, AttributeError) as error:
            last_error = error
            SharedSystemClient.clear_system_cache()
    if last_error is not None:
        raise last_error
    raise RuntimeError("Could not open the resume index")


def reset_store() -> None:
    global _client, _collection, _bound_model
    _client = None
    _collection = None
    _bound_model = None


def get_collection(embedder: Embedder | None = None):
    global _client, _collection, _bound_model
    with _lock:
        embedder = embedder or get_embedder()
        if _collection is not None and _bound_model == embedder.name:
            return _collection

        _client = _open_client()
        existing = {item.name for item in _client.list_collections()}
        if COLLECTION_NAME in existing:
            current = _client.get_collection(COLLECTION_NAME)
            stored = (current.metadata or {}).get("embedding_model")
            if stored and stored != embedder.name:
                _client.delete_collection(COLLECTION_NAME)
                existing.remove(COLLECTION_NAME)
        if COLLECTION_NAME not in existing:
            _collection = _client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine", "embedding_model": embedder.name},
            )
        else:
            _collection = _client.get_collection(COLLECTION_NAME)
        _bound_model = embedder.name
        return _collection


def add_chunks(chunks: list[dict], embedder: Embedder | None = None) -> int:
    if not chunks:
        return 0
    embedder = embedder or get_embedder()
    collection = get_collection(embedder)
    filename = chunks[0]["metadata"]["filename"]
    delete_by_filename(filename)
    reset_profile_cache()
    documents = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_documents(documents)
    collection.add(
        documents=documents,
        metadatas=[chunk["metadata"] for chunk in chunks],
        embeddings=embeddings,
        ids=[f'{chunk["metadata"]["filename"]}::{chunk["metadata"]["chunk_index"]}' for chunk in chunks],
    )
    return len(chunks)


def delete_by_filename(filename: str) -> None:
    collection = get_collection()
    existing = collection.get(where={"filename": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        reset_profile_cache()


def delete_by_candidate(name: str) -> None:
    collection = get_collection()
    existing = collection.get(where={"candidate": name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        reset_profile_cache()


def find_existing(name: str, filename: str = "") -> dict | None:
    wanted = " ".join(name.lower().split())
    file_key = Path(filename).name.lower() if filename else ""
    for person in list_candidates():
        have = " ".join(str(person.get("candidate", "")).lower().split())
        if have == wanted:
            return person
        if file_key and str(person.get("filename", "")).lower() == file_key:
            return person
        base = have.split("#")[0].strip()
        if base and base == wanted:
            return person
    return None


def search(query: str, n_results: int = 5, where: dict | None = None, embedder: Embedder | None = None) -> list[dict]:
    embedder = embedder or get_embedder()
    collection = get_collection(embedder)
    count = collection.count()
    if count == 0:
        return []
    query_kwargs = {
        "query_embeddings": [embedder.embed_query(query)],
        "n_results": min(n_results, count),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where
    try:
        result = collection.query(**query_kwargs)
    except Exception:
        return []
    hits = []
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        similarity = max(0.0, 1.0 - float(distance))
        hits.append({"text": text, "metadata": metadata or {}, "score": round(similarity, 4)})
    return hits


def reset_profile_cache() -> None:
    global _profiles, _profile_count
    _profiles = None
    _profile_count = -1


_profiles = None
_profile_count = -1


def all_profiles() -> list[dict]:
    global _profiles, _profile_count
    collection = get_collection()
    count = collection.count()
    if _profiles is not None and _profile_count == count:
        return _profiles
    if count == 0:
        _profiles = []
        _profile_count = 0
        return _profiles
    stored = collection.get(include=["documents", "metadatas"])
    grouped: dict[str, dict] = {}
    for text, metadata in zip(stored["documents"], stored["metadatas"]):
        if not metadata:
            continue
        name = metadata.get("candidate", "Unknown")
        entry = grouped.setdefault(
            name,
            {
                "candidate": name,
                "filename": metadata.get("filename", ""),
                "field": metadata.get("field", ""),
                "all_fields": metadata.get("all_fields", metadata.get("field", "")),
                "title": metadata.get("title", ""),
                "education": metadata.get("education", ""),
                "certifications": metadata.get("certifications", ""),
                "years": metadata.get("years", ""),
                "salary": metadata.get("salary", ""),
                "decision": metadata.get("decision", ""),
                "ai_score": metadata.get("ai_score", ""),
                "projects": metadata.get("projects", ""),
                "skills_line": metadata.get("skills_line", ""),
                "resume_id": metadata.get("resume_id", ""),
                "parts": [],
            },
        )
        if metadata.get("field"):
            entry["field"] = metadata["field"]
        if metadata.get("all_fields"):
            entry["all_fields"] = metadata["all_fields"]
        if metadata.get("title"):
            entry["title"] = metadata["title"]
        for key in (
            "education",
            "certifications",
            "years",
            "salary",
            "decision",
            "ai_score",
            "projects",
            "skills_line",
            "resume_id",
        ):
            if metadata.get(key):
                entry[key] = metadata[key]
        entry["parts"].append((int(metadata.get("chunk_index", 0)), text or ""))
    profiles = []
    for entry in grouped.values():
        ordered = [text for _, text in sorted(entry["parts"])]
        profiles.append(
            {
                "candidate": entry["candidate"],
                "filename": entry["filename"],
                "field": entry["field"],
                "all_fields": entry.get("all_fields", entry["field"]),
                "title": entry["title"],
                "education": entry.get("education", ""),
                "certifications": entry.get("certifications", ""),
                "years": entry.get("years", ""),
                "salary": entry.get("salary", ""),
                "decision": entry.get("decision", ""),
                "ai_score": entry.get("ai_score", ""),
                "projects": entry.get("projects", ""),
                "skills_line": entry.get("skills_line", ""),
                "resume_id": entry.get("resume_id", ""),
                "text": "\n".join(ordered),
                "level": experience_level(entry.get("years", "")),
            }
        )
    _profiles = sorted(profiles, key=lambda item: item["candidate"].lower())
    _profile_count = count
    return _profiles


def profile_for(candidate: str) -> dict | None:
    for profile in all_profiles():
        if profile["candidate"] == candidate:
            return profile
    return None


def list_candidates() -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    stored = collection.get(include=["metadatas"])
    grouped: dict[str, dict] = {}
    for metadata in stored["metadatas"]:
        if not metadata:
            continue
        name = metadata.get("candidate", "Unknown")
        entry = grouped.setdefault(
            name,
            {
                "candidate": name,
                "filename": metadata.get("filename", ""),
                "upload_date": metadata.get("upload_date", ""),
                "field": metadata.get("field", ""),
                "title": metadata.get("title", ""),
                "education": metadata.get("education", ""),
                "certifications": metadata.get("certifications", ""),
                "years": metadata.get("years", ""),
                "salary": metadata.get("salary", ""),
                "decision": metadata.get("decision", ""),
                "ai_score": metadata.get("ai_score", ""),
                "projects": metadata.get("projects", ""),
                "skills_line": metadata.get("skills_line", ""),
                "resume_id": metadata.get("resume_id", ""),
                "chunks": 0,
            },
        )
        entry["chunks"] += 1
        entry["filename"] = metadata.get("filename", entry["filename"])
        if metadata.get("field"):
            entry["field"] = metadata["field"]
        if metadata.get("title"):
            entry["title"] = metadata["title"]
        for key in (
            "education",
            "certifications",
            "years",
            "salary",
            "decision",
            "ai_score",
            "projects",
            "skills_line",
            "resume_id",
        ):
            if metadata.get(key):
                entry[key] = metadata[key]
    people = sorted(grouped.values(), key=lambda item: item["candidate"].lower())
    for person in people:
        person["level"] = experience_level(person.get("years", ""))
    return people


def clear_store() -> None:
    global _client, _collection, _bound_model
    with _lock:
        _clear_store_locked()


def _clear_store_locked() -> None:
    global _client, _collection, _bound_model
    client = _client or _open_client()
    names = [item.name for item in client.list_collections()]
    if COLLECTION_NAME in names:
        client.delete_collection(COLLECTION_NAME)
    _client = client
    _collection = None
    _bound_model = None
    reset_profile_cache()
