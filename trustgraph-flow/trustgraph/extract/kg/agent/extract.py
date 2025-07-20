import re
import json
import urllib.parse

from ....schema import Chunk, Triple, Triples, Metadata, Value
from ....schema import EntityContext, EntityContexts

from ....rdf import TRUSTGRAPH_ENTITIES, RDF_LABEL, SUBJECT_OF, DEFINITION

from ....base import FlowProcessor, ConsumerSpec, ProducerSpec
from ....base import AgentClientSpec

from ....template import PromptManager

default_ident = "kg-extract-agent"
default_concurrency = 1
default_template_id = "agent-kg-extract"
default_config_type = "prompt"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)
        template_id = params.get("template-id", default_template_id)
        config_key = params.get("config-type", default_config_type)

        super().__init__(**params | {
            "id": id,
            "template-id": template_id,
            "config-type": config_key,
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

        print("Loading configuration version", version, flush=True)

        if self.config_key not in config:
            print(f"No key {self.config_key} in config", flush=True)
            return

        config = config[self.config_key]

        try:

            self.manager.load_config(config)

            print("Prompt configuration reloaded.", flush=True)

        except Exception as e:

            print("Exception:", e, flush=True)
            print("Configuration reload failed", flush=True)

    def to_uri(self, text):
        return TRUSTGRAPH_ENTITIES + urllib.parse.quote(text)

    def emit_triples(self, pub, metadata, triples):
        tpls = Triples()
        tpls.metadata = metadata
        tpls.triples = triples
        pub.publish(tpls)

    def emit_entity_contexts(self, pub, metadata, entity_contexts):
        ecs = EntityContexts()
        ecs.metadata = metadata
        ecs.entity_contexts = entity_contexts
        pub.publish(ecs)

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

            print("Got chunk", flush=True)

            prompt = self.manager.render(
                self.template_id,
                {
                    "text": chunk_text
                }
            )

            print("Prompt:", prompt, flush=True)

            async def handle(response):

                print("Response:", response, flush=True)

                print("Done?", response.answer is not None, flush=True)

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

            if agent_response.error:
                raise RuntimeError(f"Agent error: {agent_response.error}")

            print("response:", agent_response, flush=True)
            
            # Parse JSON response
            try:
                extraction_data = self.parse_json(agent_response.answer)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from agent: {e}")
            
            # Process extraction data
            triples, entity_contexts = self.process_extraction_data(
                extraction_data, v.metadata
            )
            
            # Emit outputs
            if triples:
                self.emit_triples(flow("triples"), msg.metadata, triples)
            
            if entity_contexts:
                self.emit_entity_contexts(
                    flow("entity-contexts"), 
                    msg.metadata, 
                    entity_contexts
                )

        except Exception as e:
            print(f"Error processing chunk: {e}", flush=True)
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
                subject=entity_uri,
                predicate=RDF_LABEL,
                object=defn["entity"]
            ))
            
            # Add definition
            triples.append(Triple(
                subject=entity_uri,
                predicate=DEFINITION,
                object=defn["definition"]
            ))
            
            # Add subject-of relationship to document
            if metadata.id:
                triples.append(Triple(
                    subject=entity_uri,
                    predicate=SUBJECT_OF,
                    object=metadata.id
                ))
            
            # Create entity context for embeddings
            entity_contexts.append(EntityContext(
                entity=entity_uri,
                context=defn["context"]
            ))
        
        # Process relationships
        for rel in data.get("relationships", []):
            subject_uri = self.to_uri(rel["subject"])
            predicate_uri = self.to_uri(rel["predicate"])
            
            # Add subject and predicate labels
            triples.append(Triple(
                subject=subject_uri,
                predicate=RDF_LABEL,
                object=rel["subject"]
            ))
            
            triples.append(Triple(
                subject=predicate_uri,
                predicate=RDF_LABEL,
                object=rel["predicate"]
            ))
            
            # Handle object (entity vs literal)
            if rel.get("object-entity", True):
                object_uri = self.to_uri(rel["object"])
                triples.append(Triple(
                    subject=object_uri,
                    predicate=RDF_LABEL,
                    object=rel["object"]
                ))
            else:
                object_uri = rel["object"]  # Keep as literal
            
            # Add the main relationship triple
            triples.append(Triple(
                subject=subject_uri,
                predicate=predicate_uri,
                object=object_uri
            ))
            
            # Add subject-of relationships to document
            if metadata.id:
                triples.append(Triple(
                    subject=subject_uri,
                    predicate=SUBJECT_OF,
                    object=metadata.id
                ))
                
                triples.append(Triple(
                    subject=predicate_uri,
                    predicate=SUBJECT_OF,
                    object=metadata.id
                ))
                
                if rel.get("object-entity", True):
                    triples.append(Triple(
                        subject=object_uri,
                        predicate=SUBJECT_OF,
                        object=metadata.id
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
