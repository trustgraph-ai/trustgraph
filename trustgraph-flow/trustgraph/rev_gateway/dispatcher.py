import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from trustgraph.messaging import TranslatorRegistry
from ..gateway.dispatch.manager import DispatcherManager

logger = logging.getLogger("dispatcher")
logger.setLevel(logging.INFO)

class WebSocketResponder:
    """Simple responder that captures response for websocket return"""
    def __init__(self):
        self.response = None
        self.completed = False
        
    async def send(self, data):
        """Capture the response data"""
        self.response = data
        self.completed = True
    
    async def __call__(self, data, final=False):
        """Make the responder callable for compatibility with requestor"""
        await self.send(data)
        if final:
            self.completed = True

class MessageDispatcher:
    
    def __init__(self, max_workers: int = 10, config_receiver=None, pulsar_client=None):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks = set()
        self.pulsar_client = pulsar_client
        
        # Use DispatcherManager for flow and service management
        if pulsar_client and config_receiver:
            self.dispatcher_manager = DispatcherManager(pulsar_client, config_receiver, prefix="rev-gateway")
        else:
            self.dispatcher_manager = None
            logger.warning("No pulsar_client or config_receiver provided - using fallback mode")
        
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
        flow_id = message.get('flow', 'default')  # Default flow
        
        logger.info(f"Processing message {request_id} for service {service} on flow {flow_id}")
        
        try:
            if not self.dispatcher_manager:
                raise RuntimeError("DispatcherManager not available - pulsar_client and config_receiver required")
            
            # Use DispatcherManager for flow-based processing
            responder = WebSocketResponder()
            
            # Map websocket service name to dispatcher service name
            dispatcher_service = self.service_mapping.get(service, service)
            
            # Check if this is a global service or flow service
            from ..gateway.dispatch.manager import global_dispatchers
            if dispatcher_service in global_dispatchers:
                # Use global service dispatcher
                await self.dispatcher_manager.invoke_global_service(
                    request_data, responder, dispatcher_service
                )
            else:
                # Use DispatcherManager to process the request through Pulsar queues
                await self.dispatcher_manager.invoke_flow_service(
                    request_data, responder, flow_id, dispatcher_service
                )
            
            # Get the response from the responder
            if responder.completed and responder.response:
                response_data = responder.response
            else:
                response_data = {'error': 'No response received'}
                
            response = {
                'id': request_id,
                'response': response_data
            }
                
        except Exception as e:
            logger.error(f"Error processing message {request_id}: {e}")
            response = {
                'id': request_id,
                'response': {'error': str(e)}
            }
        
        logger.info(f"Completed processing message {request_id}")
        return response
    
    
    async def shutdown(self):
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            
        # DispatcherManager handles its own cleanup
        logger.info("Dispatcher shutdown complete")
