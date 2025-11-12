"""
Ontology embedder component for OntoRAG system.
Generates and stores embeddings for ontology elements.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .ontology_loader import Ontology, OntologyClass, OntologyProperty
from .vector_store import InMemoryVectorStore

logger = logging.getLogger(__name__)


@dataclass
class OntologyElementMetadata:
    """Metadata for an embedded ontology element."""
    type: str  # 'class', 'objectProperty', 'datatypeProperty'
    ontology: str  # Ontology ID
    element: str  # Element ID
    definition: Dict[str, Any]  # Full element definition
    text: str  # Text used for embedding


class OntologyEmbedder:
    """Generates embeddings for ontology elements and stores them in vector store."""

    def __init__(self, embedding_service=None, vector_store: Optional[InMemoryVectorStore] = None):
        """Initialize the ontology embedder.

        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector store instance (InMemoryVectorStore)
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store or InMemoryVectorStore()
        self.embedded_ontologies = set()

    def _create_text_representation(self, element_id: str, element: Any,
                                   element_type: str) -> str:
        """Create text representation of an ontology element for embedding.

        Args:
            element_id: ID of the element
            element: The element object (OntologyClass or OntologyProperty)
            element_type: Type of element

        Returns:
            Text representation for embedding
        """
        parts = []

        # Add the element ID (often meaningful)
        parts.append(element_id.replace('-', ' ').replace('_', ' '))

        # Add labels
        if hasattr(element, 'labels') and element.labels:
            for label in element.labels:
                if isinstance(label, dict):
                    parts.append(label.get('value', ''))
                else:
                    parts.append(str(label))

        # Add comment/description
        if hasattr(element, 'comment') and element.comment:
            parts.append(element.comment)

        # Add type-specific information
        if element_type == 'class':
            if hasattr(element, 'subclass_of') and element.subclass_of:
                parts.append(f"subclass of {element.subclass_of}")
        elif element_type in ['objectProperty', 'datatypeProperty']:
            if hasattr(element, 'domain') and element.domain:
                parts.append(f"domain: {element.domain}")
            if hasattr(element, 'range') and element.range:
                parts.append(f"range: {element.range}")

        # Join all parts with spaces
        text = ' '.join(filter(None, parts))
        return text

    async def embed_ontology(self, ontology: Ontology) -> int:
        """Generate and store embeddings for all elements in an ontology.

        Args:
            ontology: The ontology to embed

        Returns:
            Number of elements embedded
        """
        if not self.embedding_service:
            logger.warning("No embedding service available, skipping embedding")
            return 0

        embedded_count = 0
        batch_size = 50  # Process embeddings in batches

        # Collect all elements to embed
        elements_to_embed = []

        # Process classes
        for class_id, class_def in ontology.classes.items():
            text = self._create_text_representation(class_id, class_def, 'class')
            elements_to_embed.append({
                'id': f"{ontology.id}:class:{class_id}",
                'text': text,
                'metadata': OntologyElementMetadata(
                    type='class',
                    ontology=ontology.id,
                    element=class_id,
                    definition=class_def.__dict__,
                    text=text
                ).__dict__
            })

        # Process object properties
        for prop_id, prop_def in ontology.object_properties.items():
            text = self._create_text_representation(prop_id, prop_def, 'objectProperty')
            elements_to_embed.append({
                'id': f"{ontology.id}:objectProperty:{prop_id}",
                'text': text,
                'metadata': OntologyElementMetadata(
                    type='objectProperty',
                    ontology=ontology.id,
                    element=prop_id,
                    definition=prop_def.__dict__,
                    text=text
                ).__dict__
            })

        # Process datatype properties
        for prop_id, prop_def in ontology.datatype_properties.items():
            text = self._create_text_representation(prop_id, prop_def, 'datatypeProperty')
            elements_to_embed.append({
                'id': f"{ontology.id}:datatypeProperty:{prop_id}",
                'text': text,
                'metadata': OntologyElementMetadata(
                    type='datatypeProperty',
                    ontology=ontology.id,
                    element=prop_id,
                    definition=prop_def.__dict__,
                    text=text
                ).__dict__
            })

        # Process in batches
        for i in range(0, len(elements_to_embed), batch_size):
            batch = elements_to_embed[i:i + batch_size]

            # Get embeddings for batch
            texts = [elem['text'] for elem in batch]
            try:
                # Call embedding service for each text (EmbeddingsClient.embed() is single-text)
                embedding_tasks = [self.embedding_service.embed(text) for text in texts]
                embeddings_list = await asyncio.gather(*embedding_tasks)

                # Convert to numpy array
                embeddings = np.array(embeddings_list)

                # Store in vector store
                ids = [elem['id'] for elem in batch]
                metadata_list = [elem['metadata'] for elem in batch]

                self.vector_store.add_batch(ids, embeddings, metadata_list)
                embedded_count += len(batch)

                logger.debug(f"Embedded batch of {len(batch)} elements from ontology {ontology.id}")

            except Exception as e:
                logger.error(f"Failed to embed batch for ontology {ontology.id}: {e}")

        self.embedded_ontologies.add(ontology.id)
        logger.info(f"Embedded {embedded_count} elements from ontology {ontology.id}")
        return embedded_count

    async def embed_ontologies(self, ontologies: Dict[str, Ontology]) -> int:
        """Generate and store embeddings for multiple ontologies.

        Args:
            ontologies: Dictionary of ontology ID to Ontology objects

        Returns:
            Total number of elements embedded
        """
        total_embedded = 0

        for ont_id, ontology in ontologies.items():
            if ont_id not in self.embedded_ontologies:
                count = await self.embed_ontology(ontology)
                total_embedded += count
            else:
                logger.debug(f"Ontology {ont_id} already embedded, skipping")

        logger.info(f"Total embedded elements: {total_embedded} from {len(ontologies)} ontologies")
        return total_embedded

    async def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if failed
        """
        if not self.embedding_service:
            logger.warning("No embedding service available")
            return None

        try:
            embedding = await self.embedding_service.embed(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            return None

    async def embed_texts(self, texts: List[str]) -> Optional[np.ndarray]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            Array of embeddings or None if failed
        """
        if not self.embedding_service:
            logger.warning("No embedding service available")
            return None

        try:
            # EmbeddingsClient.embed() is single-text, so call in parallel
            embedding_tasks = [self.embedding_service.embed(text) for text in texts]
            embeddings_list = await asyncio.gather(*embedding_tasks)
            return np.array(embeddings_list)
        except Exception as e:
            logger.error(f"Failed to embed texts: {e}")
            return None

    def remove_ontology(self, ontology_id: str):
        """Remove all embeddings for a specific ontology.

        Note: FAISS doesn't support efficient deletion, so this currently
        requires rebuilding the entire index without the removed ontology.

        Args:
            ontology_id: ID of ontology to remove
        """
        if ontology_id not in self.embedded_ontologies:
            logger.debug(f"Ontology '{ontology_id}' not embedded, nothing to remove")
            return

        # FAISS doesn't support selective deletion, so we'd need to rebuild the index
        # For now, just remove from tracking set
        # TODO: Implement index rebuilding if selective removal is needed
        self.embedded_ontologies.discard(ontology_id)
        logger.info(f"Removed ontology '{ontology_id}' from embedded set (note: vectors still in store)")

    def clear_embeddings(self, ontology_id: Optional[str] = None):
        """Clear embeddings from vector store.

        Args:
            ontology_id: If provided, only clear embeddings for this ontology
                        Otherwise, clear all embeddings
        """
        if ontology_id:
            self.remove_ontology(ontology_id)
        else:
            self.vector_store.clear()
            self.embedded_ontologies.clear()
            logger.info("Cleared all embeddings from vector store")

    def get_vector_store(self) -> InMemoryVectorStore:
        """Get the vector store instance.

        Returns:
            The vector store being used
        """
        return self.vector_store

    def get_embedded_count(self) -> int:
        """Get the number of embedded elements.

        Returns:
            Number of elements in the vector store
        """
        return self.vector_store.size()

    def is_ontology_embedded(self, ontology_id: str) -> bool:
        """Check if an ontology has been embedded.

        Args:
            ontology_id: ID of the ontology

        Returns:
            True if the ontology has been embedded
        """
        return ontology_id in self.embedded_ontologies