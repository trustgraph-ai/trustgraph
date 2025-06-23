import asyncio
import logging
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger("dispatcher")
logger.setLevel(logging.INFO)

class MessageDispatcher:
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks = set()
        
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
        
        logger.info(f"Processing message {request_id}")
        
        await asyncio.sleep(2.0)
        
        response = {
            'id': request_id,
            'response': 'hello world',
            'status': 'success'
        }
        
        logger.info(f"Completed processing message {request_id}")
        return response
    
    async def shutdown(self):
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete")
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        logger.info("Dispatcher shutdown complete")