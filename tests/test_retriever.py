from core.chunker import chunk_text
from core.embedder import HashEmbedder
from core.vector_store import add_chunks, clear_store, search


def test_chunks_overlap_and_keep_metadata():
    text = "Skills:\n" + ("Python AWS Docker SQL machine learning. " * 40)
    chunks = chunk_text(text, filename="ada.txt", candidate_name="Ada", upload_date="2026-10-06")
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["candidate"] == "Ada"
    assert chunks[0]["metadata"]["chunk_index"] == 0
    assert chunks[1]["metadata"]["section"] == "skills"


def test_semantic_search_returns_the_matching_resume():
    clear_store()
    embedder = HashEmbedder()
    python_resume = (
        "Priya Sharma\n\nSkills:\nPython, AWS, Docker, machine learning, SQL, PyTorch.\n\n"
        "Experience:\nBuilt ranking models with Python on AWS."
    )
    react_resume = (
        "Arjun Mehta\n\nSkills:\nReact, TypeScript, JavaScript, HTML, CSS.\n\n"
        "Experience:\nLed a frontend rewrite in a startup using React."
    )
    add_chunks(chunk_text(python_resume, "priya.txt", "Priya Sharma"), embedder)
    add_chunks(chunk_text(react_resume, "arjun.txt", "Arjun Mehta"), embedder)
    hits = search("Who knows Python and AWS?", n_results=3, embedder=embedder)
    assert hits
    assert hits[0]["metadata"]["candidate"] == "Priya Sharma"
    filtered = search("React startup", n_results=2, where={"candidate": "Arjun Mehta"}, embedder=embedder)
    assert filtered
    assert all(hit["metadata"]["candidate"] == "Arjun Mehta" for hit in filtered)
