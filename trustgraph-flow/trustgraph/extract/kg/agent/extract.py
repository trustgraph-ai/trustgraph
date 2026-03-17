import re
import json
import urllib.parse
import logging

from ....schema import Chunk, Triple, Triples, Metadata, Term, IRI, LITERAL
from ....schema import EntityContext, EntityContexts

from ....rdf import TRUSTGRAPH_ENTITIES, RDF_LABEL, DEFINITION

from ....base import FlowProcessor, ConsumerSpec, ProducerSpec
from ....base import AgentClientSpec

from ....provenance import subgraph_uri, subgraph_provenance_triples, set_graph, GRAPH_SOURCE
from ....flow_version import __version__ as COMPONENT_VERSION
from ....template import PromptManager

# Module logger
logger = logging.getLogger(__name__)

default_ident = "kg-extract-agent"
default_concurrency = 1
default_template_id = "agent-kg-extract"
default_config_type = "prompt"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)
        template_id = params.get("template_id", default_template_id)
        config_key = params.get("config_type", default_config_type)

        super().__init__(**params | {
            "id": id,
            "template_id": template_id,
            "config_type": config_key,
            "concurrency": concurrency,
        })

        self.concurrency = concurrency
        self.template_id = template_id
        self.config_key = config_key

        self.register_config_handler(self.on_prompt_config)

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Chunk,
                handler = self.on_message,
                concurrency = self.concurrency,
            )
        )

        self.register_specification(
            AgentClientSpec(
                request_name = "agent-request",
                response_name = "agent-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name="triples",
                schema=Triples,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="entity-contexts",
                schema=EntityContexts,
            )
        )

        # Null configuration, should reload quickly
        self.manager = PromptManager()

    async def on_prompt_config(self, config, version):

        logger.info(f"Loading configuration version {version}")

        if self.config_key not in config:
            logger.warning(f"No key {self.config_key} in config")
            return

        config = config[self.config_key]

        try:

            self.manager.load_config(config)

            logger.info("Prompt configuration reloaded")

        except Exception as e:

            logger.error(f"Configuration reload exception: {e}", exc_info=True)
            logger.error("Configuration reload failed")

    def to_uri(self, text):
        return TRUSTGRAPH_ENTITIES + urllib.parse.quote(text)

    async def emit_triples(self, pub, metadata, triples):
        tpls = Triples(
            metadata = Metadata(
                id = metadata.id,
                root = metadata.root,
                user = metadata.user,
                collection = metadata.collection,
            ),
            triples = triples,
        )

        await pub.send(tpls)

    async def emit_entity_contexts(self, pub, metadata, entity_contexts):
        ecs = EntityContexts(
            metadata = Metadata(
                id = metadata.id,
                root = metadata.root,
                user = metadata.user,
                collection = metadata.collection,
            ),
            entities = entity_contexts,
        )

        await pub.send(ecs)

    def parse_jsonl(self, text):
        """
        Parse JSONL response, returning list of valid objects.

        Invalid lines (malformed JSON, empty lines) are skipped with warnings.
        This provides truncation resilience - partial output yields partial results.
        """
        results = []

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith('```'):
            # Remove opening fence (possibly with language hint)
            text = re.sub(r'^```(?:json|jsonl)?\s*\n?', '', text)
        if text.endswith('```'):
            text = text[:-3]

        for line_num, line in enumerate(text.strip().split('\n'), 1):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip any remaining fence markers
            if line.startswith('```'):
                continue

            try:
                obj = json.loads(line)
                results.append(obj)
            except json.JSONDecodeError as e:
                # Log warning but continue - this provides truncation resilience
                logger.warning(f"JSONL parse error on line {line_num}: {e}")

        return results

    async def on_message(self, msg, consumer, flow):

        try:

            v = msg.value()

            # Extract chunk text
            chunk_text = v.chunk.decode('utf-8')

            logger.debug("Processing chunk for agent extraction")

            prompt = self.manager.render(
                self.template_id,
                {
                    "text": chunk_text
                }
            )

            logger.debug(f"Agent prompt: {prompt}")

            # Send to agent API
            agent_response = await flow("agent-request").invoke(
                question = prompt
            )
            
            # Parse JSONL response
            extraction_data = self.parse_jsonl(agent_response)

            if not extraction_data:
                logger.warning("JSONL parse returned no valid objects")
                return
            
            # Process extraction data
            triples, entity_contexts, extracted_triples = \
                self.process_extraction_data(extraction_data, v.metadata)

            # Generate subgraph provenance for extracted triples
            if extracted_triples:
                chunk_uri = v.metadata.id
                sg_uri = subgraph_uri()
                prov_triples = subgraph_provenance_triples(
                    subgraph_uri=sg_uri,
                    extracted_triples=extracted_triples,
                    chunk_uri=chunk_uri,
                    component_name=default_ident,
                    component_version=COMPONENT_VERSION,
                )
                triples.extend(set_graph(prov_triples, GRAPH_SOURCE))

            # Emit outputs
            if triples:
                await self.emit_triples(flow("triples"), v.metadata, triples)
            
            if entity_contexts:
                await self.emit_entity_contexts(
                    flow("entity-contexts"), 
                    v.metadata, 
                    entity_contexts
                )

        except Exception as e:
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            raise

    def process_extraction_data(self, data, metadata):
        """Process JSONL extraction data to generate triples and entity contexts.

        Data is a flat list of objects with 'type' discriminator field:
        - {"type": "definition", "entity": "...", "definition": "..."}
        - {"type": "relationship", "subject": "...", "predicate": "...", "object": "...", "object-entity": bool}

        Returns:
            Tuple of (all_triples, entity_contexts, extracted_triples) where
            extracted_triples contains only the core knowledge facts (for provenance).
        """
        triples = []
        extracted_triples = []
        entity_contexts = []

        # Categorize items by type
        definitions = [item for item in data if item.get("type") == "definition"]
        relationships = [item for item in data if item.get("type") == "relationship"]

        # Process definitions
        for defn in definitions:

            entity_uri = self.to_uri(defn["entity"])

            # Add entity label
            triples.append(Triple(
                s = Term(type=IRI, iri=entity_uri),
                p = Term(type=IRI, iri=RDF_LABEL),
                o = Term(type=LITERAL, value=defn["entity"]),
            ))

            # Add definition
            definition_triple = Triple(
                s = Term(type=IRI, iri=entity_uri),
                p = Term(type=IRI, iri=DEFINITION),
                o = Term(type=LITERAL, value=defn["definition"]),
            )
            triples.append(definition_triple)
            extracted_triples.append(definition_triple)

            # Create entity context for embeddings
            entity_contexts.append(EntityContext(
                entity=Term(type=IRI, iri=entity_uri),
                context=defn["definition"]
            ))

        # Process relationships
        for rel in relationships:

            subject_uri = self.to_uri(rel["subject"])
            predicate_uri = self.to_uri(rel["predicate"])

            subject_value = Term(type=IRI, iri=subject_uri)
            predicate_value = Term(type=IRI, iri=predicate_uri)
            if rel.get("object-entity", True):
                object_uri = self.to_uri(rel["object"])
                object_value = Term(type=IRI, iri=object_uri)
            else:
                object_value = Term(type=LITERAL, value=rel["object"])

            # Add subject and predicate labels
            triples.append(Triple(
                s = subject_value,
                p = Term(type=IRI, iri=RDF_LABEL),
                o = Term(type=LITERAL, value=rel["subject"]),
            ))

            triples.append(Triple(
                s = predicate_value,
                p = Term(type=IRI, iri=RDF_LABEL),
                o = Term(type=LITERAL, value=rel["predicate"]),
            ))

            # Handle object (entity vs literal)
            if rel.get("object-entity", True):
                triples.append(Triple(
                    s = object_value,
                    p = Term(type=IRI, iri=RDF_LABEL),
                    o = Term(type=LITERAL, value=rel["object"]),
                ))

            # Add the main relationship triple
            relationship_triple = Triple(
                s = subject_value,
                p = predicate_value,
                o = object_value
            )
            triples.append(relationship_triple)
            extracted_triples.append(relationship_triple)

        return triples, entity_contexts, extracted_triples

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        parser.add_argument(
            "--template-id",
            type=str,
            default=default_template_id,
            help="Template ID to use for agent extraction"
        )

        parser.add_argument(
            '--config-type',
            default="prompt",
            help=f'Configuration key for prompts (default: prompt)',
        )

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
