"""
Vector store implementation for OntoRAG system.
Provides FAISS-based vector storage for ontology embeddings.
"""

import logging
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
import faiss

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any]


class InMemoryVectorStore:
    """FAISS-based vector store implementation for ontology embeddings."""

    def __init__(self, dimension: int = 1536, index_type: str = 'flat'):
        """Initialize FAISS vector store.

        Args:
            dimension: Embedding dimension (1536 for text-embedding-3-small)
            index_type: 'flat' for exact search, 'ivf' for larger datasets
        """
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
