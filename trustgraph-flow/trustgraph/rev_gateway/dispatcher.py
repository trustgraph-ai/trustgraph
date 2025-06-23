import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from trustgraph.messaging import TranslatorRegistry

logger = logging.getLogger("dispatcher")
logger.setLevel(logging.INFO)

class MessageDispatcher:
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks = set()
        
        # Service name mapping from websocket protocol to translator registry
        self.service_mapping = {
            "text-completion": "text-completion",
            "graph-rag": "graph-rag", 
            "agent": "agent",
            "embeddings": "embeddings",
            "graph-embeddings": "graph-embeddings-query",
            "triples": "triples-query",
            "document-load": "document",
            "text-load": "text-document", 
            "flow": "flow",
            "knowledge": "knowledge",
            "config": "config",
            "librarian": "librarian",
            "document-rag": "document-rag"
        }
        
    async def handle_message(self, message: Dict[Any, Any]) -> Optional[Dict[Any, Any]]:
        async with self.semaphore:
            task = asyncio.create_task(self._process_message(message))
            self.active_tasks.add(task)
            
            try:
                result = await task
                return result
            finally:
                self.active_tasks.discard(task)
    
    async def _process_message(self, message: Dict[Any, Any]) -> Dict[Any, Any]:
        request_id = message.get('id', str(uuid.uuid4()))
        service = message.get('service')
        request_data = message.get('request', {})
        
        logger.info(f"Processing message {request_id} for service {service}")
        
        try:
            # Map websocket service name to translator service name
            translator_service = self.service_mapping.get(service, service)
            
            # Get the request translator 
            if TranslatorRegistry.has_service(translator_service):
                request_translator = TranslatorRegistry.get_request_translator(translator_service)
                response_translator = TranslatorRegistry.get_response_translator(translator_service)
                
                # Convert websocket request to Pulsar message
                pulsar_request = request_translator.to_pulsar(request_data)
                logger.info(f"Converted to Pulsar request: {type(pulsar_request)}")
                
                # Send to fixme function (placeholder for actual processing)
                pulsar_response = await self.fixme(pulsar_request)
                
                # Convert Pulsar response back to websocket format
                response_data = response_translator.from_pulsar(pulsar_response)
                
                response = {
                    'id': request_id,
                    'response': response_data
                }
            else:
                logger.warning(f"No translator found for service: {service}")
                response = {
                    'id': request_id,
                    'response': {'error': f'Unsupported service: {service}'}
                }
                
        except Exception as e:
            logger.error(f"Error processing message {request_id}: {e}")
            response = {
                'id': request_id,
                'response': {'error': str(e)}
            }
        
        logger.info(f"Completed processing message {request_id}")
        return response
        
    async def fixme(self, pulsar_request) -> Any:
        """Placeholder function for actual message processing"""
        logger.info(f"FIXME: Processing Pulsar request of type {type(pulsar_request)}")
        
        # Wait 2 seconds as before
        await asyncio.sleep(2.0)
        
        # For now, create a mock response based on request type
        # This will be replaced with actual processing logic later
        request_type = type(pulsar_request).__name__
        
        # Import appropriate response schema - this is a temporary mock
        if "TextCompletion" in request_type:
            from trustgraph.schema import TextCompletionResponse
            return TextCompletionResponse(response="hello world")
        elif "Agent" in request_type:
            from trustgraph.schema import AgentResponse  
            return AgentResponse(answer="hello world")
        elif "Embeddings" in request_type:
            from trustgraph.schema import EmbeddingsResponse
            return EmbeddingsResponse(vectors=[[0.1, 0.2, 0.3]])
        else:
            # Generic response for unknown types
            logger.warning(f"Unknown request type: {request_type}")
            # Return a simple dict that can be handled
            return {"response": "hello world"}
    
    async def shutdown(self):
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        logger.info("Dispatcher shutdown complete")