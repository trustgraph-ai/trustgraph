import re
import json
import urllib.parse
import logging

from ....schema import Chunk, Triple, Triples, Metadata, Value
from ....schema import EntityContext, EntityContexts

from ....rdf import TRUSTGRAPH_ENTITIES, RDF_LABEL, SUBJECT_OF, DEFINITION

from ....base import FlowProcessor, ConsumerSpec, ProducerSpec
from ....base import AgentClientSpec

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
                metadata = [],
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
                metadata = [],
                user = metadata.user,
                collection = metadata.collection,
            ),
            entities = entity_contexts,
        )

        await pub.send(ecs)

    def parse_json(self, text):
        json_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # If no delimiters, assume the entire output is JSON
            json_str = text.strip()

        return json.loads(json_str)

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

            async def handle(response):

                logger.debug(f"Agent response: {response}")

                if response.error is not None:
                    if response.error.message:
                        raise RuntimeError(str(response.error.message))
                    else:
                        raise RuntimeError(str(response.error))

                if response.answer is not None:
                    return True
                else:
                    return False
            
            # Send to agent API
            agent_response = await flow("agent-request").invoke(
                recipient = handle,
                question = prompt
            )
            
            # Parse JSON response
            try:
                extraction_data = self.parse_json(agent_response)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from agent: {e}")
            
            # Process extraction data
            triples, entity_contexts = self.process_extraction_data(
                extraction_data, v.metadata
            )

            # Put document metadata into triples
            for t in v.metadata.metadata:
                triples.append(t)
        
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
        """Process combined extraction data to generate triples and entity contexts"""
        triples = []
        entity_contexts = []

        # Process definitions
        for defn in data.get("definitions", []):

            entity_uri = self.to_uri(defn["entity"])
            
            # Add entity label
            triples.append(Triple(
                s = Value(value=entity_uri, is_uri=True),
                p = Value(value=RDF_LABEL, is_uri=True),
                o = Value(value=defn["entity"], is_uri=False),
            ))
            
            # Add definition
            triples.append(Triple(
                s = Value(value=entity_uri, is_uri=True),
                p = Value(value=DEFINITION, is_uri=True),
                o = Value(value=defn["definition"], is_uri=False),
            ))
            
            # Add subject-of relationship to document
            if metadata.id:
                triples.append(Triple(
                    s = Value(value=entity_uri, is_uri=True),
                    p = Value(value=SUBJECT_OF, is_uri=True),
                    o = Value(value=metadata.id, is_uri=True),
                ))
            
            # Create entity context for embeddings
            entity_contexts.append(EntityContext(
                entity=Value(value=entity_uri, is_uri=True),
                context=defn["definition"]
            ))
        
        # Process relationships
        for rel in data.get("relationships", []):

            subject_uri = self.to_uri(rel["subject"])
            predicate_uri = self.to_uri(rel["predicate"])

            subject_value = Value(value=subject_uri, is_uri=True)
            predicate_value = Value(value=predicate_uri, is_uri=True)
            if data.get("object-entity", False):
                object_value = Value(value=predicate_uri, is_uri=True)
            else:
                object_value = Value(value=predicate_uri, is_uri=False)
            
            # Add subject and predicate labels
            triples.append(Triple(
                s = subject_value,
                p = Value(value=RDF_LABEL, is_uri=True),
                o = Value(value=rel["subject"], is_uri=False),
            ))
            
            triples.append(Triple(
                s = predicate_value,
                p = Value(value=RDF_LABEL, is_uri=True),
                o = Value(value=rel["predicate"], is_uri=False),
            ))
            
            # Handle object (entity vs literal)
            if rel.get("object-entity", True):
                triples.append(Triple(
                    s = object_value,
                    p = Value(value=RDF_LABEL, is_uri=True),
                    o = Value(value=rel["object"], is_uri=True),
                ))
            
            # Add the main relationship triple
            triples.append(Triple(
                s = subject_value,
                p = predicate_value,
                o = object_value
            ))
            
            # Add subject-of relationships to document
            if metadata.id:
                triples.append(Triple(
                    s = subject_value,
                    p = Value(value=SUBJECT_OF, is_uri=True),
                    o = Value(value=metadata.id, is_uri=True),
                ))
                
                triples.append(Triple(
                    s = predicate_value,
                    p = Value(value=SUBJECT_OF, is_uri=True),
                    o = Value(value=metadata.id, is_uri=True),
                ))
                
                if rel.get("object-entity", True):
                    triples.append(Triple(
                        s = object_value,
                        p = Value(value=SUBJECT_OF, is_uri=True),
                        o = Value(value=metadata.id, is_uri=True),
                    ))
        
        return triples, entity_contexts

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
