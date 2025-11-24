"""
OntoRAG: Ontology-based knowledge extraction service.
Extracts ontology-conformant triples from text chunks.
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

from .... schema import Chunk, Triple, Triples, Metadata, Value
from .... schema import EntityContext, EntityContexts
from .... schema import PromptRequest, PromptResponse
from .... rdf import TRUSTGRAPH_ENTITIES, RDF_TYPE, RDF_LABEL, DEFINITION
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

# URI prefix mappings for common namespaces
URI_PREFIXES = {
    "rdf:": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
    "owl:": "http://www.w3.org/2002/07/owl#",
    "skos:": "http://www.w3.org/2004/02/skos/core#",
    "schema:": "https://schema.org/",
    "xsd:": "http://www.w3.org/2001/XMLSchema#",
}


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

        self.register_specification(
            ProducerSpec(
                name="entity-contexts",
                schema=EntityContexts
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
                # Emit empty outputs
                await self.emit_triples(
                    flow("triples"),
                    v.metadata,
                    []
                )
                await self.emit_entity_contexts(
                    flow("entity-contexts"),
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

            # Generate ontology definition triples
            ontology_triples = self.build_ontology_triples(ontology_subset)

            # Combine extracted triples with ontology triples
            all_triples = triples + ontology_triples

            # Build entity contexts from all triples (including ontology elements)
            entity_contexts = self.build_entity_contexts(all_triples)

            # Emit all triples (extracted + ontology definitions)
            await self.emit_triples(
                flow("triples"),
                v.metadata,
                all_triples
            )

            # Emit entity contexts
            await self.emit_entity_contexts(
                flow("entity-contexts"),
                v.metadata,
                entity_contexts
            )

            logger.info(f"Extracted {len(triples)} content triples + {len(ontology_triples)} ontology triples "
                       f"= {len(all_triples)} total triples and {len(entity_contexts)} entity contexts")

        except Exception as e:
            logger.error(f"OntoRAG extraction exception: {e}", exc_info=True)
            # Emit empty outputs on error
            await self.emit_triples(
                flow("triples"),
                v.metadata,
                []
            )
            await self.emit_entity_contexts(
                flow("entity-contexts"),
                v.metadata,
                []
            )

    def build_extraction_variables(self, chunk: str, ontology_subset: OntologySubset) -> Dict[str, Any]:
        """Build variables for ontology-based extraction prompt template.

        Args:
            chunk: Text chunk to extract from
            ontology_subset: Relevant ontology elements

        Returns:
            Dict with template variables: text, classes, object_properties, datatype_properties
        """
        return {
            "text": chunk,
            "classes": ontology_subset.classes,
            "object_properties": ontology_subset.object_properties,
            "datatype_properties": ontology_subset.datatype_properties
        }

    def parse_and_validate_triples(self, triples_response: List[Any],
                                  ontology_subset: OntologySubset) -> List[Triple]:
        """Parse and validate extracted triples against ontology."""
        validated_triples = []
        ontology_id = ontology_subset.ontology_id

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
                        # Expand URIs before creating Value objects
                        subject_uri = self.expand_uri(subject, ontology_subset, ontology_id)
                        predicate_uri = self.expand_uri(predicate, ontology_subset, ontology_id)

                        # Object might be URI or literal - check before expanding
                        if self.is_uri(object_val) or self.should_expand_as_uri(object_val, ontology_subset):
                            object_uri = self.expand_uri(object_val, ontology_subset, ontology_id)
                            is_object_uri = True
                        else:
                            object_uri = object_val
                            is_object_uri = False

                        # Create Triple object with expanded URIs
                        s_value = Value(value=subject_uri, is_uri=True)
                        p_value = Value(value=predicate_uri, is_uri=True)
                        o_value = Value(value=object_uri, is_uri=is_object_uri)

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

    def should_expand_as_uri(self, value: str, ontology_subset: OntologySubset) -> bool:
        """Check if a value should be treated as URI (not literal).

        Returns True if value is a class name, property name, or entity reference.
        """
        # Check if it's a class or property from ontology
        if value in ontology_subset.classes:
            return True
        if value in ontology_subset.object_properties:
            return True
        if value in ontology_subset.datatype_properties:
            return True
        # Check if it starts with a known prefix
        for prefix in URI_PREFIXES.keys():
            if value.startswith(prefix):
                return True
        # Check if it looks like an entity reference (e.g., "recipe:cornish-pasty")
        if ":" in value and not value.startswith("http"):
            return True
        return False

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

    def expand_uri(self, value: str, ontology_subset: OntologySubset, ontology_id: str = "unknown") -> str:
        """Expand prefix notation or short names to full URIs.

        Args:
            value: Value to expand (e.g., "rdf:type", "Recipe", "has_ingredient")
            ontology_subset: Ontology subset for class/property lookup
            ontology_id: ID of the ontology for constructing instance URIs

        Returns:
            Full URI string
        """
        # Already a full URI
        if value.startswith("http://") or value.startswith("https://"):
            return value

        # Check standard prefixes (rdf:, rdfs:, etc.)
        for prefix, namespace in URI_PREFIXES.items():
            if value.startswith(prefix):
                return namespace + value[len(prefix):]

        # Check if it's an ontology class
        if value in ontology_subset.classes:
            class_def = ontology_subset.classes[value]
            # class_def is a dict (from cls.__dict__ in ontology_selector)
            if isinstance(class_def, dict) and 'uri' in class_def and class_def['uri']:
                return class_def['uri']
            # Fallback: construct URI
            return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"

        # Check if it's an ontology property
        if value in ontology_subset.object_properties:
            prop_def = ontology_subset.object_properties[value]
            # prop_def is a dict (from prop.__dict__ in ontology_selector)
            if isinstance(prop_def, dict) and 'uri' in prop_def and prop_def['uri']:
                return prop_def['uri']
            return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"

        if value in ontology_subset.datatype_properties:
            prop_def = ontology_subset.datatype_properties[value]
            # prop_def is a dict (from prop.__dict__ in ontology_selector)
            if isinstance(prop_def, dict) and 'uri' in prop_def and prop_def['uri']:
                return prop_def['uri']
            return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"

        # Otherwise, treat as entity instance - construct unique URI
        # Normalize the value for URI (lowercase, replace spaces with hyphens)
        normalized = value.replace(" ", "-").lower()
        return f"https://trustgraph.ai/{ontology_id}/{normalized}"

    def is_uri(self, value: str) -> bool:
        """Check if value is already a full URI."""
        return value.startswith("http://") or value.startswith("https://")

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

    async def emit_entity_contexts(self, pub, metadata: Metadata, entities: List[EntityContext]):
        """Emit entity contexts to output."""
        ec = EntityContexts(
            metadata=Metadata(
                id=metadata.id,
                metadata=[],
                user=metadata.user,
                collection=metadata.collection,
            ),
            entities=entities,
        )
        await pub.send(ec)

    def build_ontology_triples(self, ontology_subset: OntologySubset) -> List[Triple]:
        """Build triples describing the ontology elements themselves.

        Generates triples for classes and properties so they exist in the knowledge graph.

        Args:
            ontology_subset: The ontology subset used for extraction

        Returns:
            List of Triple objects describing ontology elements
        """
        ontology_triples = []

        # Generate triples for classes
        for class_id, class_def in ontology_subset.classes.items():
            # Get URI for class
            if isinstance(class_def, dict) and 'uri' in class_def and class_def['uri']:
                class_uri = class_def['uri']
            else:
                # Fallback to constructed URI
                class_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{class_id}"

            # rdf:type owl:Class
            ontology_triples.append(Triple(
                s=Value(value=class_uri, is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://www.w3.org/2002/07/owl#Class", is_uri=True)
            ))

            # rdfs:label (stored as 'labels' in OntologyClass.__dict__)
            if isinstance(class_def, dict) and 'labels' in class_def:
                labels = class_def['labels']
                if isinstance(labels, list) and labels:
                    label_val = labels[0].get('value', class_id) if isinstance(labels[0], dict) else str(labels[0])
                    ontology_triples.append(Triple(
                        s=Value(value=class_uri, is_uri=True),
                        p=Value(value=RDF_LABEL, is_uri=True),
                        o=Value(value=label_val, is_uri=False)
                    ))

            # rdfs:comment (stored as 'comment' in OntologyClass.__dict__)
            if isinstance(class_def, dict) and 'comment' in class_def and class_def['comment']:
                comment = class_def['comment']
                ontology_triples.append(Triple(
                    s=Value(value=class_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#comment", is_uri=True),
                    o=Value(value=comment, is_uri=False)
                ))

            # rdfs:subClassOf (stored as 'subclass_of' in OntologyClass.__dict__)
            if isinstance(class_def, dict) and 'subclass_of' in class_def and class_def['subclass_of']:
                parent = class_def['subclass_of']
                # Get parent URI
                if parent in ontology_subset.classes:
                    parent_class_def = ontology_subset.classes[parent]
                    if isinstance(parent_class_def, dict) and 'uri' in parent_class_def and parent_class_def['uri']:
                        parent_uri = parent_class_def['uri']
                    else:
                        parent_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{parent}"
                else:
                    parent_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{parent}"

                ontology_triples.append(Triple(
                    s=Value(value=class_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#subClassOf", is_uri=True),
                    o=Value(value=parent_uri, is_uri=True)
                ))

        # Generate triples for object properties
        for prop_id, prop_def in ontology_subset.object_properties.items():
            # Get URI for property
            if isinstance(prop_def, dict) and 'uri' in prop_def and prop_def['uri']:
                prop_uri = prop_def['uri']
            else:
                prop_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{prop_id}"

            # rdf:type owl:ObjectProperty
            ontology_triples.append(Triple(
                s=Value(value=prop_uri, is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://www.w3.org/2002/07/owl#ObjectProperty", is_uri=True)
            ))

            # rdfs:label (stored as 'labels' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'labels' in prop_def:
                labels = prop_def['labels']
                if isinstance(labels, list) and labels:
                    label_val = labels[0].get('value', prop_id) if isinstance(labels[0], dict) else str(labels[0])
                    ontology_triples.append(Triple(
                        s=Value(value=prop_uri, is_uri=True),
                        p=Value(value=RDF_LABEL, is_uri=True),
                        o=Value(value=label_val, is_uri=False)
                    ))

            # rdfs:comment (stored as 'comment' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'comment' in prop_def and prop_def['comment']:
                comment = prop_def['comment']
                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#comment", is_uri=True),
                    o=Value(value=comment, is_uri=False)
                ))

            # rdfs:domain (stored as 'domain' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'domain' in prop_def and prop_def['domain']:
                domain = prop_def['domain']
                # Get domain class URI
                if domain in ontology_subset.classes:
                    domain_class_def = ontology_subset.classes[domain]
                    if isinstance(domain_class_def, dict) and 'uri' in domain_class_def and domain_class_def['uri']:
                        domain_uri = domain_class_def['uri']
                    else:
                        domain_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{domain}"
                else:
                    domain_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{domain}"

                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#domain", is_uri=True),
                    o=Value(value=domain_uri, is_uri=True)
                ))

            # rdfs:range (stored as 'range' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'range' in prop_def and prop_def['range']:
                range_val = prop_def['range']
                # Get range class URI
                if range_val in ontology_subset.classes:
                    range_class_def = ontology_subset.classes[range_val]
                    if isinstance(range_class_def, dict) and 'uri' in range_class_def and range_class_def['uri']:
                        range_uri = range_class_def['uri']
                    else:
                        range_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{range_val}"
                else:
                    range_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{range_val}"

                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#range", is_uri=True),
                    o=Value(value=range_uri, is_uri=True)
                ))

        # Generate triples for datatype properties
        for prop_id, prop_def in ontology_subset.datatype_properties.items():
            # Get URI for property
            if isinstance(prop_def, dict) and 'uri' in prop_def and prop_def['uri']:
                prop_uri = prop_def['uri']
            else:
                prop_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{prop_id}"

            # rdf:type owl:DatatypeProperty
            ontology_triples.append(Triple(
                s=Value(value=prop_uri, is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://www.w3.org/2002/07/owl#DatatypeProperty", is_uri=True)
            ))

            # rdfs:label (stored as 'labels' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'labels' in prop_def:
                labels = prop_def['labels']
                if isinstance(labels, list) and labels:
                    label_val = labels[0].get('value', prop_id) if isinstance(labels[0], dict) else str(labels[0])
                    ontology_triples.append(Triple(
                        s=Value(value=prop_uri, is_uri=True),
                        p=Value(value=RDF_LABEL, is_uri=True),
                        o=Value(value=label_val, is_uri=False)
                    ))

            # rdfs:comment (stored as 'comment' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'comment' in prop_def and prop_def['comment']:
                comment = prop_def['comment']
                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#comment", is_uri=True),
                    o=Value(value=comment, is_uri=False)
                ))

            # rdfs:domain (stored as 'domain' in OntologyProperty.__dict__)
            if isinstance(prop_def, dict) and 'domain' in prop_def and prop_def['domain']:
                domain = prop_def['domain']
                # Get domain class URI
                if domain in ontology_subset.classes:
                    domain_class_def = ontology_subset.classes[domain]
                    if isinstance(domain_class_def, dict) and 'uri' in domain_class_def and domain_class_def['uri']:
                        domain_uri = domain_class_def['uri']
                    else:
                        domain_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{domain}"
                else:
                    domain_uri = f"https://trustgraph.ai/ontology/{ontology_subset.ontology_id}#{domain}"

                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#domain", is_uri=True),
                    o=Value(value=domain_uri, is_uri=True)
                ))

            # rdfs:range (datatype)
            if isinstance(prop_def, dict) and 'rdfs:range' in prop_def and prop_def['rdfs:range']:
                range_val = prop_def['rdfs:range']
                # Range for datatype properties is usually xsd:string, xsd:int, etc.
                if range_val.startswith('xsd:'):
                    range_uri = f"http://www.w3.org/2001/XMLSchema#{range_val[4:]}"
                else:
                    range_uri = range_val

                ontology_triples.append(Triple(
                    s=Value(value=prop_uri, is_uri=True),
                    p=Value(value="http://www.w3.org/2000/01/rdf-schema#range", is_uri=True),
                    o=Value(value=range_uri, is_uri=True)
                ))

        logger.info(f"Generated {len(ontology_triples)} triples describing ontology elements")
        return ontology_triples

    def build_entity_contexts(self, triples: List[Triple]) -> List[EntityContext]:
        """Build entity contexts from extracted triples.

        Collects rdfs:label and definition properties for each entity to create
        contextual descriptions for embedding.

        Args:
            triples: List of extracted triples

        Returns:
            List of EntityContext objects
        """
        # Group triples by subject to collect entity information
        entity_data = {}  # subject_uri -> {labels: [], definitions: []}

        for triple in triples:
            subject_uri = triple.s.value
            predicate_uri = triple.p.value
            object_val = triple.o.value

            # Initialize entity data if not exists
            if subject_uri not in entity_data:
                entity_data[subject_uri] = {'labels': [], 'definitions': []}

            # Collect labels (rdfs:label)
            if predicate_uri == RDF_LABEL:
                if not triple.o.is_uri:  # Labels are literals
                    entity_data[subject_uri]['labels'].append(object_val)

            # Collect definitions (skos:definition, schema:description)
            elif predicate_uri == DEFINITION or predicate_uri == "https://schema.org/description":
                if not triple.o.is_uri:
                    entity_data[subject_uri]['definitions'].append(object_val)

        # Build EntityContext objects
        entity_contexts = []
        for subject_uri, data in entity_data.items():
            # Build context text from labels and definitions
            context_parts = []

            if data['labels']:
                context_parts.append(f"Label: {data['labels'][0]}")

            if data['definitions']:
                context_parts.extend(data['definitions'])

            # Only create EntityContext if we have meaningful context
            if context_parts:
                context_text = ". ".join(context_parts)
                entity_contexts.append(EntityContext(
                    entity=Value(value=subject_uri, is_uri=True),
                    context=context_text
                ))

        logger.debug(f"Built {len(entity_contexts)} entity contexts from {len(triples)} triples")
        return entity_contexts

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