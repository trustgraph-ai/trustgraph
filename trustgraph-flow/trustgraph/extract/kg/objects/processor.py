"""
Object extraction service - extracts structured objects from text chunks
based on configured schemas.
"""

import json
import logging
from typing import Dict, List, Any

# Module logger
logger = logging.getLogger(__name__)

from .... schema import Chunk, ExtractedObject, Metadata
from .... schema import PromptRequest, PromptResponse
from .... schema import RowSchema, Field

from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base import PromptClientSpec
from .... messaging.translators import row_schema_translator

default_ident = "kg-extract-objects"


def convert_values_to_strings(obj: Dict[str, Any]) -> Dict[str, str]:
    """Convert all values in a dictionary to strings for Pulsar Map(String()) compatibility"""
    result = {}
    for key, value in obj.items():
        if value is None:
            result[key] = ""
        elif isinstance(value, str):
            result[key] = value
        elif isinstance(value, (int, float, bool)):
            result[key] = str(value)
        elif isinstance(value, (list, dict)):
            # For complex types, serialize as JSON
            result[key] = json.dumps(value)
        else:
            # For any other type, convert to string
            result[key] = str(value)
    return result
default_concurrency = 1

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        # Config key for schemas
        self.config_key = params.get("config_type", "schema")

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config-type": self.config_key,
                "concurrency": concurrency,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Chunk,
                handler = self.on_chunk,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output", 
                schema = ExtractedObject
            )
        )

        # Register config handler for schema updates
        self.register_config_handler(self.on_schema_config)

        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}

    async def on_schema_config(self, config, version):
        """Handle schema configuration updates"""

        logger.info(f"Loading schema configuration version {version}")

        # Clear existing schemas
        self.schemas = {}

        # Check if our config type exists
        if self.config_key not in config:
            logger.warning(f"No '{self.config_key}' type in configuration")
            return

        # Get the schemas dictionary for our type
        schemas_config = config[self.config_key]
        
        # Process each schema in the schemas config
        for schema_name, schema_json in schemas_config.items():
            
            try:
                # Parse the JSON schema definition
                schema_def = json.loads(schema_json)
                
                # Create Field objects
                fields = []
                for field_def in schema_def.get("fields", []):
                    field = Field(
                        name=field_def["name"],
                        type=field_def["type"],
                        size=field_def.get("size", 0),
                        primary=field_def.get("primary_key", False),
                        description=field_def.get("description", ""),
                        required=field_def.get("required", False),
                        enum_values=field_def.get("enum", []),
                        indexed=field_def.get("indexed", False)
                    )
                    fields.append(field)
                
                # Create RowSchema
                row_schema = RowSchema(
                    name=schema_def.get("name", schema_name),
                    description=schema_def.get("description", ""),
                    fields=fields
                )
                
                self.schemas[schema_name] = row_schema
                logger.info(f"Loaded schema: {schema_name} with {len(fields)} fields")
                
            except Exception as e:
                logger.error(f"Failed to parse schema {schema_name}: {e}", exc_info=True)

        logger.info(f"Schema configuration loaded: {len(self.schemas)} schemas")

    async def extract_objects_for_schema(self, text: str, schema_name: str, schema: RowSchema, flow) -> List[Dict[str, Any]]:
        """Extract objects from text for a specific schema"""
        
        try:
            # Convert Pulsar RowSchema to JSON-serializable dict
            schema_dict = row_schema_translator.from_pulsar(schema)
            
            # Use prompt client to extract rows based on schema
            objects = await flow("prompt-request").extract_objects(
                schema=schema_dict,
                text=text
            )
            
            return objects if isinstance(objects, list) else []
            
        except Exception as e:
            logger.error(f"Failed to extract objects for schema {schema_name}: {e}", exc_info=True)
            return []

    async def on_chunk(self, msg, consumer, flow):
        """Process incoming chunk and extract objects"""

        v = msg.value()
        logger.info(f"Extracting objects from chunk {v.metadata.id}...")

        chunk_text = v.chunk.decode("utf-8")

        # If no schemas configured, log warning and return
        if not self.schemas:
            logger.warning("No schemas configured - skipping extraction")
            return

        try:
            # Extract objects for each configured schema
            for schema_name, schema in self.schemas.items():
                
                logger.debug(f"Extracting {schema_name} objects from chunk")
                
                # Extract objects using prompt
                objects = await self.extract_objects_for_schema(
                    chunk_text, 
                    schema_name, 
                    schema,
                    flow
                )
                
                # Emit each extracted object
                for obj in objects:
                    
                    # Calculate confidence (could be enhanced with actual confidence from prompt)
                    confidence = 0.8  # Default confidence
                    
                    # Convert all values to strings for Pulsar compatibility
                    string_values = convert_values_to_strings(obj)
                    
                    # Create ExtractedObject
                    extracted = ExtractedObject(
                        metadata=Metadata(
                            id=f"{v.metadata.id}:{schema_name}:{hash(str(obj))}",
                            metadata=[],
                            user=v.metadata.user,
                            collection=v.metadata.collection,
                        ),
                        schema_name=schema_name,
                        values=string_values,
                        confidence=confidence,
                        source_span=chunk_text[:100]  # First 100 chars as source reference
                    )
                    
                    await flow("output").send(extracted)
                    logger.debug(f"Emitted extracted object for schema {schema_name}")

        except Exception as e:
            logger.error(f"Object extraction exception: {e}", exc_info=True)

        logger.debug("Object extraction complete")

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )

        FlowProcessor.add_args(parser)

def run():
    """Entry point for kg-extract-objects command"""
    Processor.launch(default_ident, __doc__)
