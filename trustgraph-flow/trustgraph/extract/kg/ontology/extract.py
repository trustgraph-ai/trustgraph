"""
OntoRAG: Ontology-based knowledge extraction service.
Extracts ontology-conformant triples from text chunks.
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

from .... schema import Chunk, Triple, Triples, Metadata, Value
from .... schema import PromptRequest, PromptResponse
from .... rdf import TRUSTGRAPH_ENTITIES, RDF_TYPE, RDF_LABEL
from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base import PromptClientSpec, EmbeddingsClientSpec

from .ontology_loader import OntologyLoader
from .ontology_embedder import OntologyEmbedder
from .vector_store import InMemoryVectorStore
from .text_processor import TextProcessor
from .ontology_selector import OntologySelector, OntologySubset

logger = logging.getLogger(__name__)

default_ident = "kg-extract-ontology"
default_concurrency = 1


class Processor(FlowProcessor):
    """Main OntoRAG extraction processor."""

    def __init__(self, **params):
        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
            }
        )

        # Register specifications
        self.register_specification(
            ConsumerSpec(
                name="input",
                schema=Chunk,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

        self.register_specification(
            EmbeddingsClientSpec(
                request_name="embeddings-request",
                response_name="embeddings-response"
            )
        )

        self.register_specification(
            ProducerSpec(
                name="triples",
                schema=Triples
            )
        )

        # Register config handler for ontology updates
        self.register_config_handler(self.on_ontology_config)

        # Shared components (not flow-specific)
        self.ontology_loader = OntologyLoader()
        self.text_processor = TextProcessor()

        # Per-flow components (each flow gets its own embedder/vector store/selector)
        self.flow_components = {}  # flow_id -> {embedder, vector_store, selector}

        # Configuration
        self.top_k = params.get("top_k", 10)
        self.similarity_threshold = params.get("similarity_threshold", 0.3)

        # Track loaded ontology version
        self.current_ontology_version = None
        self.loaded_ontology_ids = set()

    async def initialize_flow_components(self, flow):
        """Initialize per-flow OntoRAG components.

        Each flow gets its own vector store and embedder to support
        different embedding models across flows. The vector store dimension
        is auto-detected from the embeddings service.

        Args:
            flow: Flow object for this processing context

        Returns:
            flow_id: Identifier for this flow's components
        """
        # Use flow object as identifier
        flow_id = id(flow)

        if flow_id in self.flow_components:
            return flow_id  # Already initialized for this flow

        try:
            logger.info(f"Initializing components for flow {flow_id}")

            # Use embeddings client directly (no wrapper needed)
            embeddings_client = flow("embeddings-request")

            # Detect embedding dimension by embedding a test string
            logger.info("Detecting embedding dimension from embeddings service...")
            test_embedding_response = await embeddings_client.embed("test")
            test_embedding = test_embedding_response[0]  # Extract from [[vector]]
            dimension = len(test_embedding)
            logger.info(f"Detected embedding dimension: {dimension}")

            # Initialize vector store with detected dimension
            vector_store = InMemoryVectorStore(
                dimension=dimension,
                index_type='flat'
            )

            ontology_embedder = OntologyEmbedder(
                embedding_service=embeddings_client,
                vector_store=vector_store
            )

            # Embed all loaded ontologies for this flow
            if self.ontology_loader.get_all_ontologies():
                logger.info(f"Embedding ontologies for flow {flow_id}")
                for ont_id, ontology in self.ontology_loader.get_all_ontologies().items():
                    await ontology_embedder.embed_ontology(ontology)
                logger.info(f"Embedded {ontology_embedder.get_embedded_count()} ontology elements for flow {flow_id}")

            # Initialize ontology selector
            ontology_selector = OntologySelector(
                ontology_embedder=ontology_embedder,
                ontology_loader=self.ontology_loader,
                top_k=self.top_k,
                similarity_threshold=self.similarity_threshold
            )

            # Store flow-specific components
            self.flow_components[flow_id] = {
                'embedder': ontology_embedder,
                'vector_store': vector_store,
                'selector': ontology_selector,
                'dimension': dimension
            }

            logger.info(f"Flow {flow_id} components initialized successfully (dimension={dimension})")
            return flow_id

        except Exception as e:
            logger.error(f"Failed to initialize flow {flow_id} components: {e}", exc_info=True)
            raise

    async def on_ontology_config(self, config, version):
        """
        Handle ontology configuration updates from ConfigPush queue.

        Parses and stores ontologies. Embedding happens per-flow on first message.

        Called automatically when:
        - Processor starts (gets full config history via start_of_messages=True)
        - Config service pushes updates (immediate event-driven notification)

        Args:
            config: Full configuration map - config[type][key] = value
            version: Config version number (monotonically increasing)
        """
        try:
            logger.info(f"Received ontology config update, version={version}")

            # Skip if we've already processed this version
            if version == self.current_ontology_version:
                logger.debug(f"Already at version {version}, skipping")
                return

            # Extract ontology configurations
            if "ontology" not in config:
                logger.warning("No 'ontology' section in config")
                return

            ontology_configs = config["ontology"]

            # Parse ontology definitions
            ontologies = {}
            for ont_id, ont_json in ontology_configs.items():
                try:
                    ontologies[ont_id] = json.loads(ont_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse ontology '{ont_id}': {e}")
                    continue

            logger.info(f"Loaded {len(ontologies)} ontology definitions")

            # Determine what changed (for incremental updates)
            new_ids = set(ontologies.keys())
            added_ids = new_ids - self.loaded_ontology_ids
            removed_ids = self.loaded_ontology_ids - new_ids
            updated_ids = new_ids & self.loaded_ontology_ids  # May have changed content

            if added_ids:
                logger.info(f"New ontologies: {added_ids}")
            if removed_ids:
                logger.info(f"Removed ontologies: {removed_ids}")
            if updated_ids:
                logger.info(f"Updated ontologies: {updated_ids}")

            # Update ontology loader's internal state
            self.ontology_loader.update_ontologies(ontologies)

            # Clear all flow components to force re-embedding with new ontologies
            if added_ids or removed_ids or updated_ids:
                logger.info("Clearing flow components to trigger re-embedding")
                self.flow_components.clear()

            # Update tracking
            self.current_ontology_version = version
            self.loaded_ontology_ids = new_ids

            logger.info(f"Ontology config update complete, version={version}")

        except Exception as e:
            logger.error(f"Failed to process ontology config: {e}", exc_info=True)

    async def on_message(self, msg, consumer, flow):
        """Process incoming chunk message."""
        v = msg.value()
        logger.info(f"Extracting ontology-based triples from {v.metadata.id}...")

        # Initialize flow-specific components if needed
        flow_id = await self.initialize_flow_components(flow)
        components = self.flow_components[flow_id]

        chunk = v.chunk.decode("utf-8")
        logger.debug(f"Processing chunk: {chunk[:200]}...")

        try:
            # Process text into segments
            segments = self.text_processor.process_chunk(chunk, extract_phrases=True)
            logger.debug(f"Split chunk into {len(segments)} segments")

            # Select relevant ontology subset (using flow-specific selector)
            ontology_subsets = await components['selector'].select_ontology_subset(segments)

            if not ontology_subsets:
                logger.warning("No relevant ontology elements found for chunk")
                # Emit empty triples
                await self.emit_triples(
                    flow("triples"),
                    v.metadata,
                    []
                )
                return

            # Merge subsets if multiple ontologies matched
            if len(ontology_subsets) > 1:
                ontology_subset = components['selector'].merge_subsets(ontology_subsets)
            else:
                ontology_subset = ontology_subsets[0]

            logger.debug(f"Selected ontology subset with {len(ontology_subset.classes)} classes, "
                        f"{len(ontology_subset.object_properties)} object properties, "
                        f"{len(ontology_subset.datatype_properties)} datatype properties")

            # Build extraction prompt variables
            prompt_variables = self.build_extraction_variables(chunk, ontology_subset)

            # Call prompt service for extraction
            try:
                # Use prompt() method with extract-with-ontologies prompt ID
                triples_response = await flow("prompt-request").prompt(
                    id="extract-with-ontologies",
                    variables=prompt_variables
                )
                logger.debug(f"Extraction response: {triples_response}")

                if not isinstance(triples_response, list):
                    logger.error("Expected list of triples from prompt service")
                    triples_response = []

            except Exception as e:
                logger.error(f"Prompt service error: {e}", exc_info=True)
                triples_response = []

            # Parse and validate triples
            triples = self.parse_and_validate_triples(triples_response, ontology_subset)

            # Add metadata triples
            for t in v.metadata.metadata:
                triples.append(t)

            # Emit triples
            await self.emit_triples(
                flow("triples"),
                v.metadata,
                triples
            )

            logger.info(f"Extracted {len(triples)} ontology-conformant triples")

        except Exception as e:
            logger.error(f"OntoRAG extraction exception: {e}", exc_info=True)
            # Emit empty triples on error
            await self.emit_triples(
                flow("triples"),
                v.metadata,
                []
            )

    def build_extraction_prompt(self, chunk: str, ontology_subset: OntologySubset) -> str:
        """Build prompt for ontology-based extraction."""
        # Format classes
        classes_str = self.format_classes(ontology_subset.classes)

        # Format properties
        obj_props_str = self.format_properties(
            ontology_subset.object_properties,
            "object"
        )
        dt_props_str = self.format_properties(
            ontology_subset.datatype_properties,
            "datatype"
        )

        prompt = f"""Extract knowledge triples from the following text using ONLY the provided ontology elements.

ONTOLOGY CLASSES:
{classes_str}

OBJECT PROPERTIES (connect entities):
{obj_props_str}

DATATYPE PROPERTIES (entity attributes):
{dt_props_str}

RULES:
1. Only use classes defined above for entity types
2. Only use properties defined above for relationships and attributes
3. Respect domain and range constraints
4. Output format: JSON array of {{"subject": "", "predicate": "", "object": ""}}
5. For class instances, use rdf:type as predicate
6. Include rdfs:label for new entities

TEXT:
{chunk}

TRIPLES (JSON array):"""

        return prompt

    def format_classes(self, classes: Dict[str, Any]) -> str:
        """Format classes for prompt."""
        if not classes:
            return "None"

        lines = []
        for class_id, definition in classes.items():
            comment = definition.get('comment', '')
            parent = definition.get('subclass_of', 'Thing')
            lines.append(f"- {class_id} (subclass of {parent}): {comment}")

        return '\n'.join(lines)

    def format_properties(self, properties: Dict[str, Any], prop_type: str) -> str:
        """Format properties for prompt."""
        if not properties:
            return "None"

        lines = []
        for prop_id, definition in properties.items():
            comment = definition.get('comment', '')
            domain = definition.get('domain', 'Any')
            range_val = definition.get('range', 'Any')
            lines.append(f"- {prop_id} ({domain} -> {range_val}): {comment}")

        return '\n'.join(lines)

    def parse_and_validate_triples(self, triples_response: List[Any],
                                  ontology_subset: OntologySubset) -> List[Triple]:
        """Parse and validate extracted triples against ontology."""
        validated_triples = []

        for triple_data in triples_response:
            try:
                if isinstance(triple_data, dict):
                    subject = triple_data.get('subject', '')
                    predicate = triple_data.get('predicate', '')
                    object_val = triple_data.get('object', '')

                    if not subject or not predicate or not object_val:
                        continue

                    # Validate against ontology
                    if self.is_valid_triple(subject, predicate, object_val, ontology_subset):
                        # Create Triple object
                        s_value = Value(value=subject, is_uri=self.is_uri(subject))
                        p_value = Value(value=predicate, is_uri=True)
                        o_value = Value(value=object_val, is_uri=self.is_uri(object_val))

                        validated_triples.append(Triple(
                            s=s_value,
                            p=p_value,
                            o=o_value
                        ))
                    else:
                        logger.debug(f"Invalid triple: ({subject}, {predicate}, {object_val})")

            except Exception as e:
                logger.error(f"Error parsing triple: {e}")

        return validated_triples

    def is_valid_triple(self, subject: str, predicate: str, object_val: str,
                       ontology_subset: OntologySubset) -> bool:
        """Validate triple against ontology constraints."""
        # Special case for rdf:type
        if predicate == "rdf:type" or predicate == str(RDF_TYPE):
            # Check if object is a valid class
            return object_val in ontology_subset.classes

        # Special case for rdfs:label
        if predicate == "rdfs:label" or predicate == str(RDF_LABEL):
            return True  # Labels are always valid

        # Check if predicate is a valid property
        is_obj_prop = predicate in ontology_subset.object_properties
        is_dt_prop = predicate in ontology_subset.datatype_properties

        if not is_obj_prop and not is_dt_prop:
            return False  # Unknown property

        # TODO: Add more sophisticated validation (domain/range checking)
        return True

    def is_uri(self, value: str) -> bool:
        """Check if value is a URI."""
        return value.startswith("http://") or value.startswith("https://") or \
               value.startswith(str(TRUSTGRAPH_ENTITIES)) or \
               value in ["rdf:type", "rdfs:label"]

    async def emit_triples(self, pub, metadata: Metadata, triples: List[Triple]):
        """Emit triples to output."""
        t = Triples(
            metadata=Metadata(
                id=metadata.id,
                metadata=[],
                user=metadata.user,
                collection=metadata.collection,
            ),
            triples=triples,
        )
        await pub.send(t)

    @staticmethod
    def add_args(parser):
        """Add command-line arguments."""
        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )
        parser.add_argument(
            '--top-k',
            type=int,
            default=10,
            help='Number of top ontology elements to retrieve (default: 10)'
        )
        parser.add_argument(
            '--similarity-threshold',
            type=float,
            default=0.3,
            help='Similarity threshold for ontology matching (default: 0.3, range: 0.0-1.0)'
        )
        FlowProcessor.add_args(parser)


def run():
    """Launch the OntoRAG extraction service."""
    Processor.launch(default_ident, __doc__)