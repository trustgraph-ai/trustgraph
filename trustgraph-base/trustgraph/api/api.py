
import requests
import json
import base64
import time
from typing import Optional

from . library import Library
from . flow import Flow
from . config import Config
from . knowledge import Knowledge
from . collection import Collection
from . exceptions import *
from . types import *

def check_error(response):

    if "error" in response:

        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(response["error"])

        raise ApplicationException(f"{tp}: {msg}")

class Api:

    def __init__(self, url="http://localhost:8088/", timeout=60, token: Optional[str] = None):

        self.url = url

        if not url.endswith("/"):
            self.url += "/"

        self.url += "api/v1/"

        self.timeout = timeout
        self.token = token

        # Lazy initialization for new clients
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None
        self._metrics = None
        self._async_metrics = None

    def flow(self):
        return Flow(api=self)

    def config(self):
        return Config(api=self)

    def knowledge(self):
        return Knowledge(api=self)

    def request(self, path, request):

        url = f"{self.url}{path}"

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=request, timeout=self.timeout, headers=headers)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        check_error(object)

        return object

    def library(self):
        return Library(self)

    def collection(self):
        return Collection(self)

    # New synchronous methods
    def socket(self):
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            from . socket_client import SocketClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._socket_client = SocketClient(base_url, self.timeout, self.token)
        return self._socket_client

    def bulk(self):
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            from . bulk_client import BulkClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._bulk_client = BulkClient(base_url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self):
        """Synchronous metrics interface"""
        if self._metrics is None:
            from . metrics import Metrics
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._metrics = Metrics(base_url, self.timeout, self.token)
        return self._metrics

    # New asynchronous methods
    def async_flow(self):
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            from . async_flow import AsyncFlow
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self):
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            from . async_socket_client import AsyncSocketClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_socket_client = AsyncSocketClient(base_url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self):
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            from . async_bulk_client import AsyncBulkClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_bulk_client = AsyncBulkClient(base_url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self):
        """Asynchronous metrics interface"""
        if self._async_metrics is None:
            from . async_metrics import AsyncMetrics
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_metrics = AsyncMetrics(base_url, self.timeout, self.token)
        return self._async_metrics

    # Resource management
    def close(self):
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self):
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
