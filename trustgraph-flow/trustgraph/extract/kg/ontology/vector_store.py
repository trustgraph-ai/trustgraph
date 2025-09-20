"""
Vector store implementations for OntoRAG system.
Provides both FAISS and NumPy-based vector storage for ontology embeddings.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import FAISS, fall back to NumPy implementation if not available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available, using NumPy implementation")


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    """Abstract base class for vector stores."""

    def add(self, id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add single embedding with metadata."""
        raise NotImplementedError

    def add_batch(self, ids: List[str], embeddings: np.ndarray,
                  metadata_list: List[Dict[str, Any]]):
        """Batch add for initial ontology loading."""
        raise NotImplementedError

    def search(self, embedding: np.ndarray, top_k: int = 10,
               threshold: float = 0.0) -> List[SearchResult]:
        """Search for similar vectors."""
        raise NotImplementedError

    def clear(self):
        """Reset the store."""
        raise NotImplementedError

    def size(self) -> int:
        """Return number of stored vectors."""
        raise NotImplementedError


class FAISSVectorStore(VectorStore):
    """FAISS-based vector store implementation."""

    def __init__(self, dimension: int = 1536, index_type: str = 'flat'):
        """Initialize FAISS vector store.

        Args:
            dimension: Embedding dimension (1536 for text-embedding-3-small)
            index_type: 'flat' for exact search, 'ivf' for larger datasets
        """
        if not FAISS_AVAILABLE:
            raise RuntimeError("FAISS is not installed")

        self.dimension = dimension
        self.metadata = []
        self.ids = []

        if index_type == 'flat':
            # Exact search - best for ontologies with <10k elements
            self.index = faiss.IndexFlatIP(dimension)
            logger.info(f"Created FAISS flat index with dimension {dimension}")
        else:
            # Approximate search - for larger ontologies
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            # Train with random vectors for initialization
            training_data = np.random.randn(1000, dimension).astype('float32')
            training_data = training_data / np.linalg.norm(
                training_data, axis=1, keepdims=True
            )
            self.index.train(training_data)
            logger.info(f"Created FAISS IVF index with dimension {dimension}")

    def add(self, id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add single embedding with metadata."""
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        self.index.add(np.array([embedding], dtype=np.float32))
        self.metadata.append(metadata)
        self.ids.append(id)

    def add_batch(self, ids: List[str], embeddings: np.ndarray,
                  metadata_list: List[Dict[str, Any]]):
        """Batch add for initial ontology loading."""
        # Normalize all embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        self.index.add(normalized.astype(np.float32))
        self.metadata.extend(metadata_list)
        self.ids.extend(ids)
        logger.debug(f"Added batch of {len(ids)} embeddings to FAISS index")

    def search(self, embedding: np.ndarray, top_k: int = 10,
               threshold: float = 0.0) -> List[SearchResult]:
        """Search for similar vectors."""
        # Normalize query
        embedding = embedding / np.linalg.norm(embedding)

        # Search
        scores, indices = self.index.search(
            np.array([embedding], dtype=np.float32),
            min(top_k, self.index.ntotal)
        )

        # Filter by threshold and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score >= threshold:  # FAISS returns -1 for empty slots
                results.append(SearchResult(
                    id=self.ids[idx],
                    score=float(score),
                    metadata=self.metadata[idx]
                ))

        return results

    def clear(self):
        """Reset the store."""
        self.index.reset()
        self.metadata = []
        self.ids = []
        logger.info("Cleared FAISS vector store")

    def size(self) -> int:
        """Return number of stored vectors."""
        return self.index.ntotal


class SimpleVectorStore(VectorStore):
    """NumPy-based vector store implementation for development/small deployments."""

    def __init__(self):
        """Initialize simple NumPy-based vector store."""
        self.embeddings = []
        self.metadata = []
        self.ids = []
        logger.info("Created SimpleVectorStore (NumPy implementation)")

    def add(self, id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add single embedding with metadata."""
        # Normalize for cosine similarity
        normalized = embedding / np.linalg.norm(embedding)
        self.embeddings.append(normalized)
        self.metadata.append(metadata)
        self.ids.append(id)

    def add_batch(self, ids: List[str], embeddings: np.ndarray,
                  metadata_list: List[Dict[str, Any]]):
        """Batch add for initial ontology loading."""
        # Normalize all embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        normalized = embeddings / norms

        for i in range(len(ids)):
            self.embeddings.append(normalized[i])
            self.metadata.append(metadata_list[i])
            self.ids.append(ids[i])

        logger.debug(f"Added batch of {len(ids)} embeddings to simple store")

    def search(self, embedding: np.ndarray, top_k: int = 10,
               threshold: float = 0.0) -> List[SearchResult]:
        """Search for similar vectors using cosine similarity."""
        if not self.embeddings:
            return []

        # Normalize query embedding
        embedding = embedding / np.linalg.norm(embedding)

        # Compute cosine similarities
        embeddings_array = np.array(self.embeddings)
        similarities = np.dot(embeddings_array, embedding)

        # Get top-k indices
        top_k = min(top_k, len(self.embeddings))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            if similarities[idx] >= threshold:
                results.append(SearchResult(
                    id=self.ids[idx],
                    score=float(similarities[idx]),
                    metadata=self.metadata[idx]
                ))

        return results

    def clear(self):
        """Reset the store."""
        self.embeddings = []
        self.metadata = []
        self.ids = []
        logger.info("Cleared simple vector store")

    def size(self) -> int:
        """Return number of stored vectors."""
        return len(self.embeddings)


class InMemoryVectorStore:
    """Factory class to create appropriate vector store based on availability."""

    @staticmethod
    def create(dimension: int = 1536, prefer_faiss: bool = True,
               index_type: str = 'flat') -> VectorStore:
        """Create a vector store instance.

        Args:
            dimension: Embedding dimension
            prefer_faiss: Whether to prefer FAISS if available
            index_type: Type of FAISS index ('flat' or 'ivf')

        Returns:
            VectorStore instance (FAISS or Simple)
        """
        if prefer_faiss and FAISS_AVAILABLE:
            try:
                return FAISSVectorStore(dimension, index_type)
            except Exception as e:
                logger.warning(f"Failed to create FAISS store: {e}, falling back to NumPy")
                return SimpleVectorStore()
        else:
            return SimpleVectorStore()


# Utility functions for vector operations
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def batch_cosine_similarity(queries: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query vectors and target vectors.

    Args:
        queries: Array of shape (n_queries, dimension)
        targets: Array of shape (n_targets, dimension)

    Returns:
        Array of shape (n_queries, n_targets) with similarity scores
    """
    # Normalize queries and targets
    queries_norm = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    targets_norm = targets / np.linalg.norm(targets, axis=1, keepdims=True)

    # Compute dot product
    similarities = np.dot(queries_norm, targets_norm.T)
    return similarities