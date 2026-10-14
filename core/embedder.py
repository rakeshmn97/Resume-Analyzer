import hashlib
import math
import re

from app.config import EMBEDDING_BACKEND, EMBEDDING_MODEL

TOKEN = re.compile(r"[a-z0-9+#.]{2,}")


class Embedder:
    name: str
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashEmbedder(Embedder):
    """Deterministic bag-of-words vectors. Used for tests and offline fallback."""

    def __init__(self, dimension: int = 384):
        self.name = "hash"
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embed(text, self.dimension) for text in texts]


class MiniLMEmbedder(Embedder):
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self.name = EMBEDDING_MODEL
        self.dimension = int(self._model.get_embedding_dimension())

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is not None:
        return _embedder
    if EMBEDDING_BACKEND == "hash":
        _embedder = HashEmbedder()
        return _embedder
    try:
        _embedder = MiniLMEmbedder()
    except Exception:
        _embedder = HashEmbedder()
    return _embedder


def reset_embedder() -> None:
    global _embedder
    _embedder = None


def _hash_embed(text: str, dimension: int) -> list[float]:
    vector = [0.0] * dimension
    tokens = TOKEN.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
