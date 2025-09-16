"""
Structured Data Diagnosis Service - analyzes structured data and generates descriptors.
Supports three operations: detect-type, generate-descriptor, and diagnose (combined).
"""

import json
import logging
from typing import Dict, Any, Optional

from ...schema import StructuredDataDiagnosisRequest, StructuredDataDiagnosisResponse
from ...schema import PromptRequest, Error, RowSchema, Field as SchemaField

from ...base import FlowProcessor, ConsumerSpec, ProducerSpec, PromptClientSpec

from .type_detector import detect_data_type, detect_csv_options

# Module logger
logger = logging.getLogger(__name__)

default_ident = "structured-diag"
default_csv_prompt = "diagnose-csv"
default_json_prompt = "diagnose-json"
default_xml_prompt = "diagnose-xml"


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        # Config key for schemas
        self.config_key = params.get("config_type", "schema")

        # Configurable prompt template names
        self.csv_prompt = params.get("csv_prompt", default_csv_prompt)
        self.json_prompt = params.get("json_prompt", default_json_prompt)
        self.xml_prompt = params.get("xml_prompt", default_xml_prompt)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "config_type": self.config_key,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = StructuredDataDiagnosisRequest,
                handler = self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = StructuredDataDiagnosisResponse,
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

        logger.info("Structured Data Diagnosis service initialized")

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

    async def on_message(self, msg, consumer, flow):
        """Handle incoming structured data diagnosis request"""

        try:
            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.info(f"Handling structured data diagnosis request {id}: operation={request.operation}")

            if request.operation == "detect-type":
                response = await self.detect_type_operation(request, flow)
            elif request.operation == "generate-descriptor":
                response = await self.generate_descriptor_operation(request, flow)
            elif request.operation == "diagnose":
                response = await self.diagnose_operation(request, flow)
            elif request.operation == "schema-selection":
                response = await self.schema_selection_operation(request, flow)
            else:
                error = Error(
                    type="InvalidOperation",
                    message=f"Unknown operation: {request.operation}. Supported: detect-type, generate-descriptor, diagnose, schema-selection"
                )
                response = StructuredDataDiagnosisResponse(
                    error=error,
                    operation=request.operation
                )

            # Send response
            await flow("response").send(
                response, properties={"id": id}
            )

        except Exception as e:
            logger.error(f"Error processing diagnosis request: {e}", exc_info=True)

            error = Error(
                type="ProcessingError",
                message=f"Failed to process diagnosis request: {str(e)}"
            )

            response = StructuredDataDiagnosisResponse(
                error=error,
                operation=request.operation if request else "unknown"
            )

            await flow("response").send(
                response, properties={"id": id}
            )

    async def detect_type_operation(self, request: StructuredDataDiagnosisRequest, flow) -> StructuredDataDiagnosisResponse:
        """Handle detect-type operation"""
        logger.info("Processing detect-type operation")

        detected_type, confidence = detect_data_type(request.sample)

        metadata = {}
        if detected_type == "csv":
            csv_options = detect_csv_options(request.sample)
            metadata["csv_options"] = json.dumps(csv_options)

        return StructuredDataDiagnosisResponse(
            error=None,
            operation=request.operation,
            detected_type=detected_type or "",
            confidence=confidence,
            metadata=metadata
        )

    async def generate_descriptor_operation(self, request: StructuredDataDiagnosisRequest, flow) -> StructuredDataDiagnosisResponse:
        """Handle generate-descriptor operation"""
        logger.info(f"Processing generate-descriptor operation for type: {request.type}")

        if not request.type:
            error = Error(
                type="MissingParameter",
                message="Type parameter is required for generate-descriptor operation"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        if not request.schema_name:
            error = Error(
                type="MissingParameter",
                message="Schema name parameter is required for generate-descriptor operation"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        # Get target schema
        if request.schema_name not in self.schemas:
            error = Error(
                type="SchemaNotFound",
                message=f"Schema '{request.schema_name}' not found in configuration"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        target_schema = self.schemas[request.schema_name]

        # Generate descriptor using prompt service
        descriptor = await self.generate_descriptor_with_prompt(
            request.sample, request.type, target_schema, request.options, flow
        )

        if descriptor is None:
            error = Error(
                type="DescriptorGenerationFailed",
                message="Failed to generate descriptor using prompt service"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        return StructuredDataDiagnosisResponse(
            error=None,
            operation=request.operation,
            descriptor=json.dumps(descriptor),
            metadata={"schema_name": request.schema_name, "type": request.type}
        )

    async def diagnose_operation(self, request: StructuredDataDiagnosisRequest, flow) -> StructuredDataDiagnosisResponse:
        """Handle combined diagnose operation"""
        logger.info("Processing combined diagnose operation")

        # Step 1: Detect type
        detected_type, confidence = detect_data_type(request.sample)

        if not detected_type:
            error = Error(
                type="TypeDetectionFailed",
                message="Unable to detect data type from sample"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        # Step 2: Use provided schema name or auto-select first available
        schema_name = request.schema_name
        if not schema_name and self.schemas:
            schema_name = list(self.schemas.keys())[0]
            logger.info(f"Auto-selected schema: {schema_name}")

        if not schema_name:
            error = Error(
                type="NoSchemaAvailable",
                message="No schema specified and no schemas available in configuration"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        if schema_name not in self.schemas:
            error = Error(
                type="SchemaNotFound",
                message=f"Schema '{schema_name}' not found in configuration"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        target_schema = self.schemas[schema_name]

        # Step 3: Generate descriptor
        descriptor = await self.generate_descriptor_with_prompt(
            request.sample, detected_type, target_schema, request.options, flow
        )

        if descriptor is None:
            error = Error(
                type="DescriptorGenerationFailed",
                message="Failed to generate descriptor using prompt service"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

        metadata = {
            "schema_name": schema_name,
            "auto_selected_schema": request.schema_name != schema_name
        }

        if detected_type == "csv":
            csv_options = detect_csv_options(request.sample)
            metadata["csv_options"] = json.dumps(csv_options)

        return StructuredDataDiagnosisResponse(
            error=None,
            operation=request.operation,
            detected_type=detected_type,
            confidence=confidence,
            descriptor=json.dumps(descriptor),
            metadata=metadata
        )

    async def schema_selection_operation(self, request: StructuredDataDiagnosisRequest, flow) -> StructuredDataDiagnosisResponse:
        """Handle schema-selection operation"""
        logger.info("Processing schema-selection operation")

        # Prepare all schemas for the prompt
        all_schemas = []
        for schema_name, row_schema in self.schemas.items():
            schema_info = {
                "name": row_schema.name,
                "description": row_schema.description,
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
                    for f in row_schema.fields
                ]
            }
            all_schemas.append(schema_info)

        # Create prompt variables - schemas array contains ALL schemas
        variables = {
            "sample": request.sample,
            "schemas": all_schemas,
            "options": request.options or {}
        }

        # Call prompt service (assuming there's a schema-selection prompt template)
        terms = {k: json.dumps(v) for k, v in variables.items()}
        prompt_request = PromptRequest(
            id="schema-selection",  # This prompt template needs to exist
            terms=terms
        )

        try:
            logger.info("Calling prompt service for schema selection")
            response = await flow("prompt-request").request(prompt_request)

            if response.error:
                logger.error(f"Prompt service error: {response.error.message}")
                error = Error(
                    type="PromptServiceError",
                    message="Failed to select schemas using prompt service"
                )
                return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

            if not response.text or not response.text.strip():
                logger.error("Empty response from prompt service")
                error = Error(
                    type="PromptServiceError",
                    message="Empty response from prompt service"
                )
                return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

            # Parse the response as JSON array of schema IDs
            try:
                schema_matches = json.loads(response.text.strip())
                if not isinstance(schema_matches, list):
                    raise ValueError("Response must be an array")
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse schema matches response: {e}")
                error = Error(
                    type="ParseError",
                    message="Failed to parse schema selection response as JSON array"
                )
                return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

            return StructuredDataDiagnosisResponse(
                error=None,
                operation=request.operation,
                schema_matches=schema_matches
            )

        except Exception as e:
            logger.error(f"Error calling prompt service: {e}", exc_info=True)
            error = Error(
                type="PromptServiceError",
                message="Failed to select schemas using prompt service"
            )
            return StructuredDataDiagnosisResponse(error=error, operation=request.operation)

    async def generate_descriptor_with_prompt(
        self, sample: str, data_type: str, target_schema: RowSchema,
        options: Dict[str, str], flow
    ) -> Optional[Dict[str, Any]]:
        """Generate descriptor using appropriate prompt service"""

        # Select prompt template based on data type
        prompt_templates = {
            "csv": self.csv_prompt,
            "json": self.json_prompt,
            "xml": self.xml_prompt
        }

        prompt_id = prompt_templates.get(data_type)
        if not prompt_id:
            logger.error(f"No prompt template defined for data type: {data_type}")
            return None

        # Prepare schema information for prompt
        schema_info = {
            "name": target_schema.name,
            "description": target_schema.description,
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
                for f in target_schema.fields
            ]
        }

        # Create prompt variables
        variables = {
            "sample": sample,
            "schemas": [schema_info],  # Array with single target schema
            "options": options or {}
        }

        # Call prompt service
        terms = {k: json.dumps(v) for k, v in variables.items()}
        prompt_request = PromptRequest(
            id=prompt_id,
            terms=terms
        )

        try:
            logger.info(f"Calling prompt service with template: {prompt_id}")
            response = await flow("prompt-request").request(prompt_request)

            if response.error:
                logger.error(f"Prompt service error: {response.error.message}")
                return None

            # Parse response
            if response.object:
                try:
                    return json.loads(response.object)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse prompt response as JSON: {e}")
                    logger.debug(f"Response object: {response.object}")
                    return None
            elif response.text:
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse prompt text response as JSON: {e}")
                    logger.debug(f"Response text: {response.text}")
                    return None
            else:
                logger.error("Empty response from prompt service")
                return None

        except Exception as e:
            logger.error(f"Error calling prompt service: {e}", exc_info=True)
            return None


def run():
    """Entry point for structured-diag command"""
    Processor.launch(default_ident, __doc__)