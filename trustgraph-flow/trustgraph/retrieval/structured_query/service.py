"""
Structured Query Service - orchestrates natural language question processing.
Takes a question, converts it to GraphQL via nlp-query, executes via objects-query,
and returns the results.
"""

import json
import logging
from typing import Dict, Any, Optional

from ...schema import StructuredQueryRequest, StructuredQueryResponse
from ...schema import QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse  
from ...schema import ObjectsQueryRequest, ObjectsQueryResponse
from ...schema import Error

from ...base import FlowProcessor, ConsumerSpec, ProducerSpec, RequestResponseSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "structured-query"

class Processor(FlowProcessor):
    
    def __init__(self, **params):
        
        id = params.get("id", default_ident)
        
        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )
        
        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = StructuredQueryRequest,
                handler = self.on_message
            )
        )
        
        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = StructuredQueryResponse,
            )
        )
        
        # Client spec for calling NLP query service
        self.register_specification(
            RequestResponseSpec(
                request_name = "nlp-query-request",
                response_name = "nlp-query-response", 
                request_schema = QuestionToStructuredQueryRequest,
                response_schema = QuestionToStructuredQueryResponse
            )
        )
        
        # Client spec for calling objects query service
        self.register_specification(
            RequestResponseSpec(
                request_name = "objects-query-request",
                response_name = "objects-query-response",
                request_schema = ObjectsQueryRequest, 
                response_schema = ObjectsQueryResponse
            )
        )
        
        logger.info("Structured Query service initialized")

    async def on_message(self, msg, consumer, flow):
        """Handle incoming structured query request"""
        
        try:
            request = msg.value()
            
            # Sender-produced ID
            id = msg.properties()["id"]
            
            logger.info(f"Handling structured query request {id}: {request.question[:100]}...")
            
            # Step 1: Convert question to GraphQL using NLP query service
            logger.info("Step 1: Converting question to GraphQL")
            nlp_request = QuestionToStructuredQueryRequest(
                question=request.question,
                max_results=100  # Default limit
            )
            
            nlp_response = await self.client("nlp-query-request").request(nlp_request)
            
            if nlp_response.error is not None:
                raise Exception(f"NLP query service error: {nlp_response.error.message}")
            
            if not nlp_response.graphql_query:
                raise Exception("NLP query service returned empty GraphQL query")
                
            logger.info(f"Generated GraphQL query: {nlp_response.graphql_query[:200]}...")
            logger.info(f"Detected schemas: {nlp_response.detected_schemas}")
            logger.info(f"Confidence: {nlp_response.confidence}")
            
            # Step 2: Execute GraphQL query using objects query service
            logger.info("Step 2: Executing GraphQL query")
            
            # For now, we'll use default user/collection values
            # In a real implementation, these would come from authentication/context
            objects_request = ObjectsQueryRequest(
                user="default",  # TODO: Get from authentication context
                collection="default",  # TODO: Get from request context
                query=nlp_response.graphql_query,
                variables=nlp_response.variables,
                operation_name=None
            )
            
            objects_response = await self.client("objects-query-request").request(objects_request)
            
            if objects_response.error is not None:
                raise Exception(f"Objects query service error: {objects_response.error.message}")
            
            # Handle GraphQL errors from the objects query service
            graphql_errors = []
            if objects_response.errors:
                for gql_error in objects_response.errors:
                    graphql_errors.append(f"{gql_error.message} (path: {gql_error.path})")
            
            logger.info("Step 3: Returning results")
            
            # Create response
            response = StructuredQueryResponse(
                error=None,
                data=objects_response.data or "null",  # JSON string
                errors=graphql_errors
            )
            
            logger.info("Sending structured query response...")
            await flow("response").send(response, properties={"id": id})
            
            logger.info("Structured query request completed")
            
        except Exception as e:
            
            logger.error(f"Exception in structured query service: {e}", exc_info=True)
            
            logger.info("Sending error response...")
            
            response = StructuredQueryResponse(
                error = Error(
                    type = "structured-query-error",
                    message = str(e),
                ),
                data = "null",
                errors = []
            )
            
            await flow("response").send(response, properties={"id": id})

    @staticmethod
    def add_args(parser):
        """Add command-line arguments"""
        
        FlowProcessor.add_args(parser)
        
        # No additional arguments needed for this orchestrator service

def run():
    """Entry point for structured-query command"""
    Processor.launch(default_ident, __doc__)