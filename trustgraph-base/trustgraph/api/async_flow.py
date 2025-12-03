
import aiohttp
import json
from typing import Optional, Dict, Any, List

from . exceptions import ProtocolException, ApplicationException


def check_error(response):
    if "error" in response:
        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(response["error"])

        raise ApplicationException(f"{tp}: {msg}")


class AsyncFlow:
    """Asynchronous REST-based flow interface"""

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = url
        self.timeout: int = timeout
        self.token: Optional[str] = token

    async def request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make async HTTP request to Gateway API"""
        url = f"{self.url}{path}"

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=request_data, headers=headers) as resp:
                if resp.status != 200:
                    raise ProtocolException(f"Status code {resp.status}")

                try:
                    obj = await resp.json()
                except:
                    raise ProtocolException(f"Expected JSON response")

                check_error(obj)
                return obj

    async def list(self) -> List[str]:
        """List all flows"""
        result = await self.request("flow", {"operation": "list-flows"})
        return result.get("flow-ids", [])

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        result = await self.request("flow", {
            "operation": "get-flow",
            "flow-id": id
        })
        return json.loads(result.get("flow", "{}"))

    async def start(self, class_name: str, id: str, description: str, parameters: Optional[Dict] = None):
        """Start a flow"""
        request_data = {
            "operation": "start-flow",
            "flow-id": id,
            "class-name": class_name,
            "description": description
        }
        if parameters:
            request_data["parameters"] = json.dumps(parameters)

        await self.request("flow", request_data)

    async def stop(self, id: str):
        """Stop a flow"""
        await self.request("flow", {
            "operation": "stop-flow",
            "flow-id": id
        })

    async def list_classes(self) -> List[str]:
        """List flow classes"""
        result = await self.request("flow", {"operation": "list-classes"})
        return result.get("class-names", [])

    async def get_class(self, class_name: str) -> Dict[str, Any]:
        """Get flow class definition"""
        result = await self.request("flow", {
            "operation": "get-class",
            "class-name": class_name
        })
        return json.loads(result.get("class-definition", "{}"))

    async def put_class(self, class_name: str, definition: Dict[str, Any]):
        """Create/update flow class"""
        await self.request("flow", {
            "operation": "put-class",
            "class-name": class_name,
            "class-definition": json.dumps(definition)
        })

    async def delete_class(self, class_name: str):
        """Delete flow class"""
        await self.request("flow", {
            "operation": "delete-class",
            "class-name": class_name
        })

    def id(self, flow_id: str):
        """Get async flow instance"""
        return AsyncFlowInstance(self, flow_id)

    async def aclose(self) -> None:
        """Close connection (cleanup handled by aiohttp session)"""
        pass


class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    def __init__(self, flow: AsyncFlow, flow_id: str):
        self.flow = flow
        self.flow_id = flow_id

    async def request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to flow-scoped service"""
        return await self.flow.request(f"flow/{self.flow_id}/service/{service}", request_data)

    async def agent(self, question: str, user: str, state: Optional[Dict] = None,
                    group: Optional[str] = None, history: Optional[List] = None, **kwargs: Any) -> Dict[str, Any]:
        """Execute agent (non-streaming, use async_socket for streaming)"""
        request_data = {
            "question": question,
            "user": user,
            "streaming": False  # REST doesn't support streaming
        }
        if state is not None:
            request_data["state"] = state
        if group is not None:
            request_data["group"] = group
        if history is not None:
            request_data["history"] = history
        request_data.update(kwargs)

        return await self.request("agent", request_data)

    async def text_completion(self, system: str, prompt: str, **kwargs: Any) -> str:
        """Text completion (non-streaming, use async_socket for streaming)"""
        request_data = {
            "system": system,
            "prompt": prompt,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("text-completion", request_data)
        return result.get("response", "")

    async def graph_rag(self, question: str, user: str, collection: str,
                        max_subgraph_size: int = 1000, max_subgraph_count: int = 5,
                        max_entity_distance: int = 3, **kwargs: Any) -> str:
        """Graph RAG (non-streaming, use async_socket for streaming)"""
        request_data = {
            "question": question,
            "user": user,
            "collection": collection,
            "max-subgraph-size": max_subgraph_size,
            "max-subgraph-count": max_subgraph_count,
            "max-entity-distance": max_entity_distance,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("graph-rag", request_data)
        return result.get("response", "")

    async def document_rag(self, question: str, user: str, collection: str,
                           doc_limit: int = 10, **kwargs: Any) -> str:
        """Document RAG (non-streaming, use async_socket for streaming)"""
        request_data = {
            "question": question,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("document-rag", request_data)
        return result.get("response", "")

    async def graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any):
        """Query graph embeddings for semantic search"""
        request_data = {
            "text": text,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request_data.update(kwargs)

        return await self.request("graph-embeddings", request_data)

    async def embeddings(self, text: str, **kwargs: Any):
        """Generate text embeddings"""
        request_data = {"text": text}
        request_data.update(kwargs)

        return await self.request("embeddings", request_data)

    async def triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any):
        """Triple pattern query"""
        request_data = {"limit": limit}
        if s is not None:
            request_data["s"] = str(s)
        if p is not None:
            request_data["p"] = str(p)
        if o is not None:
            request_data["o"] = str(o)
        if user is not None:
            request_data["user"] = user
        if collection is not None:
            request_data["collection"] = collection
        request_data.update(kwargs)

        return await self.request("triples", request_data)

    async def objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict] = None,
                            operation_name: Optional[str] = None, **kwargs: Any):
        """GraphQL query"""
        request_data = {
            "query": query,
            "user": user,
            "collection": collection
        }
        if variables:
            request_data["variables"] = variables
        if operation_name:
            request_data["operationName"] = operation_name
        request_data.update(kwargs)

        return await self.request("objects", request_data)
