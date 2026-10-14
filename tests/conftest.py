import os
import tempfile

os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["GOOGLE_API_KEY"] = ""
os.environ["CHROMA_PATH"] = tempfile.mkdtemp(prefix="resume-rag-")
