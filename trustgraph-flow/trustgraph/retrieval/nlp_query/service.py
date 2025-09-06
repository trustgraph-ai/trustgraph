"""
NLP to Structured Query Service - converts natural language questions to GraphQL queries.
Two-phase approach: 1) Select relevant schemas, 2) Generate GraphQL query.
"""

import json
import logging
from typing import Dict, Any, Optional, List

from ...schema import QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse
from ...schema import PromptRequest
from ...schema import Error, RowSchema, Field as SchemaField

from ...base import FlowProcessor, ConsumerSpec, ProducerSpec, PromptClientSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "nlp-query"
default_schema_selection_template = "schema-selection"
default_graphql_generation_template = "graphql-generation"

class Processor(FlowProcessor):
    
    def __init__(self, **params):
        
        id = params.get("id", default_ident)
        
        # Config key for schemas
        self.config_key = params.get("config_type", "schema")
        
        # Configurable prompt template names
        self.schema_selection_template = params.get("schema_selection_template", default_schema_selection_template)
        self.graphql_generation_template = params.get("graphql_generation_template", default_graphql_generation_template)
        
        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config_type": self.config_key,
            }
        )
        
        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = QuestionToStructuredQueryRequest,
                handler = self.on_message
            )
        )
        
        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = QuestionToStructuredQueryResponse,
            )
        )
        
        # Client spec for calling prompt service
        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
            )
        )
        
        # Register config handler for schema updates
        self.register_config_handler(self.on_schema_config)
        
        # Schema storage: name -> RowSchema
        self.schemas: Dict[str, RowSchema] = {}
        
        logger.info("NLP Query service initialized")

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
                    field = SchemaField(
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

    async def phase1_select_schemas(self, question: str, flow) -> List[str]:
        """Phase 1: Use prompt service to select relevant schemas for the question"""
        logger.info("Starting Phase 1: Schema selection")
        
        # Prepare schema information for the prompt
        schema_info = []
        for name, schema in self.schemas.items():
            schema_desc = {
                "name": name,
                "description": schema.description,
                "fields": [{"name": f.name, "type": f.type, "description": f.description} 
                          for f in schema.fields]
            }
            schema_info.append(schema_desc)
        
        # Create prompt variables
        variables = {
            "question": question,
            "schemas": schema_info  # Pass structured data directly
        }
        
        # Call prompt service for schema selection
        # Convert variables to JSON-encoded terms
        terms = {k: json.dumps(v) for k, v in variables.items()}
        prompt_request = PromptRequest(
            id=self.schema_selection_template,
            terms=terms
        )
        
        try:
            response = await flow("prompt-request").request(prompt_request)
            
            if response.error is not None:
                raise Exception(f"Prompt service error: {response.error}")
            
            # Parse the response to get selected schema names
            # Response could be in either text or object field
            response_data = response.text if response.text else response.object
            if response_data is None:
                raise Exception("Prompt service returned empty response")
            
            # Parse JSON array of schema names
            selected_schemas = json.loads(response_data)
            
            logger.info(f"Phase 1 selected schemas: {selected_schemas}")
            return selected_schemas
            
        except Exception as e:
            logger.error(f"Phase 1 schema selection failed: {e}")
            raise

    async def phase2_generate_graphql(self, question: str, selected_schemas: List[str], flow) -> Dict[str, Any]:
        """Phase 2: Generate GraphQL query using selected schemas"""
        logger.info(f"Starting Phase 2: GraphQL generation for schemas: {selected_schemas}")
        
        # Get detailed schema information for selected schemas only
        selected_schema_info = []
        for schema_name in selected_schemas:
            if schema_name in self.schemas:
                schema = self.schemas[schema_name]
                schema_desc = {
                    "name": schema_name,
                    "description": schema.description,
                    "fields": [
                        {
                            "name": f.name, 
                            "type": f.type, 
                            "description": f.description,
                            "required": f.required,
                            "primary_key": f.primary,
                            "indexed": f.indexed,
                            "enum_values": f.enum_values if f.enum_values else []
                        } 
                        for f in schema.fields
                    ]
                }
                selected_schema_info.append(schema_desc)
        
        # Create prompt variables for GraphQL generation
        variables = {
            "question": question,
            "schemas": selected_schema_info  # Pass structured data directly
        }
        
        # Call prompt service for GraphQL generation
        # Convert variables to JSON-encoded terms
        terms = {k: json.dumps(v) for k, v in variables.items()}
        prompt_request = PromptRequest(
            id=self.graphql_generation_template,
            terms=terms
        )
        
        try:
            response = await flow("prompt-request").request(prompt_request)
            
            if response.error is not None:
                raise Exception(f"Prompt service error: {response.error}")
            
            # Parse the response to get GraphQL query and variables
            # Response could be in either text or object field
            response_data = response.text if response.text else response.object
            if response_data is None:
                raise Exception("Prompt service returned empty response")
            
            # Parse JSON with "query" and "variables" fields
            result = json.loads(response_data)
            
            logger.info(f"Phase 2 generated GraphQL: {result.get('query', '')[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"Phase 2 GraphQL generation failed: {e}")
            raise

    async def on_message(self, msg, consumer, flow):
        """Handle incoming question to structured query request"""
        
        try:
            request = msg.value()
            
            # Sender-produced ID
            id = msg.properties()["id"]
            
            logger.info(f"Handling NLP query request {id}: {request.question[:100]}...")
            
            # Phase 1: Select relevant schemas
            selected_schemas = await self.phase1_select_schemas(request.question, flow)
            
            # Phase 2: Generate GraphQL query
            graphql_result = await self.phase2_generate_graphql(request.question, selected_schemas, flow)
            
            # Create response
            response = QuestionToStructuredQueryResponse(
                error=None,
                graphql_query=graphql_result.get("query", ""),
                variables=graphql_result.get("variables", {}),
                detected_schemas=selected_schemas,
                confidence=graphql_result.get("confidence", 0.8)  # Default confidence
            )
            
            logger.info("Sending NLP query response...")
            await flow("response").send(response, properties={"id": id})
            
            logger.info("NLP query request completed")
            
        except Exception as e:
            
            logger.error(f"Exception in NLP query service: {e}", exc_info=True)
            
            logger.info("Sending error response...")
            
            response = QuestionToStructuredQueryResponse(
                error = Error(
                    type = "nlp-query-error",
                    message = str(e),
                ),
                graphql_query = "",
                variables = {},
                detected_schemas = [],
                confidence = 0.0
            )
            
            await flow("response").send(response, properties={"id": id})

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""
        
        FlowProcessor.add_args(parser)
        
        parser.add_argument(
            '--config-type',
            default='schema',
            help='Configuration type prefix for schemas (default: schema)'
        )
        
        parser.add_argument(
            '--schema-selection-template',
            default=default_schema_selection_template,
            help=f'Prompt template name for schema selection (default: {default_schema_selection_template})'
        )
        
        parser.add_argument(
            '--graphql-generation-template', 
            default=default_graphql_generation_template,
            help=f'Prompt template name for GraphQL generation (default: {default_graphql_generation_template})'
        )

def run():
    """Entry point for nlp-query command"""
    Processor.launch(default_ident, __doc__)