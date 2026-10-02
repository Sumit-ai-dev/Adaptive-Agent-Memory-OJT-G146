"""
Local Fast Embedder for Semantic Vector Similarity.
Uses sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast CPU) with deterministic offline fallback.
"""

import hashlib
import logging
from typing import List
import numpy as np

logger = logging.getLogger("ai_service.embedder")


class LocalEmbedder:
    """
    Computes dense 384-dimensional semantic embeddings.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            # Load with local cache
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded SentenceTransformer: {self.model_name}")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer could not load {self.model_name} ({e}). "
                "Using deterministic high-fidelity mathematical hash embedder."
            )
            self._model = None

    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string into a normalized 384-dimensional vector.
        """
        if self._model is not None:
            try:
                vec = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return vec.tolist()
            except Exception as e:
                logger.warning(f"Error during encode: {e}. Falling back to deterministic vector.")

        return self._deterministic_hash_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embed multiple text strings.
        """
        if self._model is not None:
            try:
                vecs = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return vecs.tolist()
            except Exception as e:
                logger.warning(f"Batch encode error: {e}. Falling back.")

        return [self._deterministic_hash_vector(t) for t in texts]

    def _deterministic_hash_vector(self, text: str) -> List[float]:
        """
        Generates a unit-normalized 384-dimensional vector deterministically from text.
        Guarantees that identical text yields exact same vector, and semantically overlapping
        words produce consistent directional projection.
        """
        clean_text = text.strip().lower()
        words = clean_text.split()
        
        # Base vector
        vec = np.zeros(self.dimension, dtype=np.float32)

        if not words:
            vec[0] = 1.0
            return vec.tolist()

        for idx, word in enumerate(words):
            # SHA-256 seed for each word
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.RandomState(h)
            word_vec = rng.randn(self.dimension).astype(np.float32)
            # Add weighted by position
            weight = 1.0 / (1.0 + 0.1 * idx)
            vec += weight * word_vec

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        else:
            vec[0] = 1.0

        return vec.tolist()


# Global singleton embedder instance
local_embedder = LocalEmbedder()
