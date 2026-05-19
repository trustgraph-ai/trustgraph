import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable
from ..gateway.dispatch.manager import DispatcherManager

logger = logging.getLogger("dispatcher")


class _TokenShim:
    def __init__(self, token):
        self.headers = (
            {"Authorization": f"Bearer {token}"} if token else {}
        )


class MessageDispatcher:

    def __init__(self, max_workers=10, config_receiver=None, backend=None,
                 auth=None, timeout=120):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.active_tasks = set()
        self.backend = backend
        self.auth = auth

        if backend and config_receiver and auth:
            self.dispatcher_manager = DispatcherManager(
                backend, config_receiver,
                auth=auth,
                prefix="rev-gateway",
                timeout=timeout,
            )
        else:
            self.dispatcher_manager = None
            logger.warning(
                "Missing backend, config_receiver, or auth "
                "— using fallback mode"
            )

        self.service_mapping = {
            "text-completion": "text-completion",
            "graph-rag": "graph-rag",
            "agent": "agent",
            "embeddings": "embeddings",
            "graph-embeddings": "graph-embeddings",
            "triples": "triples",
            "document-load": "document",
            "text-load": "text-document",
            "flow": "flow",
            "knowledge": "knowledge",
            "config": "config",
            "librarian": "librarian",
            "document-rag": "document-rag",
        }

    async def handle_message(
        self, message: Dict[Any, Any],
        sender: Callable[[dict], Awaitable[None]],
    ):
        async with self.semaphore:
            task = asyncio.create_task(
                self._process_message(message, sender)
            )
            self.active_tasks.add(task)

            try:
                await task
            finally:
                self.active_tasks.discard(task)

    async def _authenticate(self, token):
        if not self.auth:
            raise RuntimeError("Auth not configured")
        return await self.auth.authenticate(_TokenShim(token))

    async def _process_message(
        self, message: Dict[Any, Any],
        sender: Callable[[dict], Awaitable[None]],
    ):
        request_id = message.get('id', str(uuid.uuid4()))
        service = message.get('service')
        request_data = message.get('request', {})
        token = message.get('token', '')
        flow_id = message.get('flow', 'default')

        logger.info(
            f"Processing message {request_id} for service "
            f"{service} on flow {flow_id}"
        )

        try:
            if not self.dispatcher_manager:
                raise RuntimeError(
                    "DispatcherManager not available"
                )

            identity = await self._authenticate(token)
            workspace = identity.workspace

            async def responder(resp, fin):
                await sender({
                    "id": request_id,
                    "response": resp,
                    "complete": fin,
                })

            dispatcher_service = self.service_mapping.get(service, service)

            from ..gateway.dispatch.manager import global_dispatchers
            if dispatcher_service in global_dispatchers:
                await self.dispatcher_manager.invoke_global_service(
                    request_data, responder, dispatcher_service,
                    workspace=workspace,
                )
            else:
                await self.dispatcher_manager.invoke_flow_service(
                    request_data, responder, workspace, flow_id,
                    dispatcher_service,
                )

        except Exception as e:
            logger.error(f"Error processing message {request_id}: {e}")
            await sender({
                "id": request_id,
                "error": {"message": str(e), "type": "error"},
                "complete": True,
            })

        logger.info(f"Completed processing message {request_id}")

    async def shutdown(self):
        if self.active_tasks:
            logger.info(
                f"Waiting for {len(self.active_tasks)} active "
                f"tasks to complete"
            )
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

        logger.info("Dispatcher shutdown complete")
