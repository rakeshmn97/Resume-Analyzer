# Resume Analyser

RAG recruitment assistant. Upload resumes, embed them once, and answer recruiter questions from the closest stored passages.

The design follows `Resume_Analyser_Project_Documentation.docx`: load PDF/DOCX, chunk with overlap, embed, store in Chroma, retrieve top matches, then answer from that context only.

## Run

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

Copy `.env.example` to `.env` and set `GOOGLE_API_KEY` if you want Gemini to write the final answer. With no key, the app still retrieves passages and scores job-description overlap locally.

Default embeddings are `all-MiniLM-L6-v2` (downloaded on first index). Set `EMBEDDING_BACKEND=hash` only for tests or a machine with no model download.

## Layout

- `app/main.py` — Streamlit upload, ask, job match, and ranking
- `core/loader.py`, `core/chunker.py`, `core/embedder.py` — ingest
- `core/vector_store.py`, `core/retriever.py` — Chroma search
- `core/llm_chain.py` — prompt plus Gemini, or the local fallback
- `data/samples/` — three resumes you can index from the Upload tab

## Tests

```powershell
pytest
```
