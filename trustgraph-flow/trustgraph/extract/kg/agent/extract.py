import json
import urllib.parse

from .... schema import Chunk, Triple, Triples, Metadata, Value
from .... schema import AgentRequest, AgentResponse, EntityContext, EntityContexts
from .... schema import ConfigRequest, ConfigResponse

from .... rdf import TRUSTGRAPH_ENTITIES, RDF_LABEL, SUBJECT_OF, DEFINITION

from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base import AgentClientSpec, ConfigClientSpec

default_ident = "kg-extract-relationships"
default_concurrency = 1
default_template_id = "agent-kg-extract"
default_config_key = "prompt"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)
        template_id = params.get("template-id", default_template_id)
        config_key = params.get("config-key", default_config_key)

        super().__init__(**params | {
            "id": id,
            "template-id": template_id,
            "config-key": config_key,
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
            ConfigClientSpec(
                request_name="config-request",
                response_name="config-response",
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

    async def on_prompt_config(self, config, version):

        print("Got config version", version)

        if self.config_key not in config:
            print(f"No key {self.config_key} in config", flush=True)
            return

        config = config[self.config_key]

        try:

            tmpl = json.loads(config[self.template_id])

            self.c

            self.prompt = data.get("prompt")
            self.rtype = data.get("response-type", "text")
            schema = data.get("schema", None)

            if schema:
                self.schema = json.loads(schema)
            else:
                self.schema = {}

            print("Prompt template reloaded.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")
            
            self.prompt = ""
            self.rtype = "text"
            self.schema = {}

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

    async def on_message(self, msg, consumer, flow):

        try:

            # Get template from config
            template_key = f"template.{self.template_id}"
            config_response = await flow("config-request").get(
                keys=[template_key]
            )
            
            if template_key not in config_response.values:
                raise ValueError(f"Template '{self.template_id}' not found in config")
            
            template = config_response.values[template_key]
            
            # Extract chunk text
            chunk_text = msg.chunk.decode('utf-8')
            
            # Render template with chunk content
            rendered_prompt = template.prompt.replace("{{text}}", chunk_text)
            
            # Send to agent API
            agent_response = await flow("agent-request").request(
                question=rendered_prompt
            )
            
            if agent_response.error:
                raise Exception(f"Agent error: {agent_response.error}")
            
            # Parse JSON response
            try:
                extraction_data = json.loads(agent_response.answer)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response from agent: {e}")
            
            # Process extraction data
            triples, entity_contexts = self.process_extraction_data(
                extraction_data, msg.metadata
            )
            
            # Emit outputs
            if triples:
                self.emit_triples(flow.producer("triples"), msg.metadata, triples)
            
            if entity_contexts:
                self.emit_entity_contexts(
                    flow.producer("entity-contexts"), 
                    msg.metadata, 
                    entity_contexts
                )

        except Exception as e:
            print(f"Error processing chunk: {e}")
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
            "--template-id",
            type=str,
            default="agent-kg-extract",
            help="Template ID to use for agent extraction"
        )

    @staticmethod
    def run():
        import argparse
        from .... base import run_processor
        
        parser = argparse.ArgumentParser(
            description="Agent-based knowledge extractor"
        )
        Processor.add_args(parser)
        args = parser.parse_args()
        
        processor = Processor(
            template_id=args.template_id
        )
        
        run_processor(processor)
