"""
TrustGraph Knowledge Graph Core Management

This module provides interfaces for managing knowledge graph cores in TrustGraph.
KG cores are pre-built knowledge graph datasets that can be loaded and unloaded
into flows for use in queries and RAG operations.
"""

import json
import base64

from .. knowledge import hash, Uri, Literal
from .. schema import IRI, LITERAL
from . types import Triple


def to_value(x):
    """Convert wire format to Uri or Literal."""
    if x.get("t") == IRI:
        return Uri(x.get("i", ""))
    elif x.get("t") == LITERAL:
        return Literal(x.get("v", ""))
    # Fallback for any other type
    return Literal(x.get("v", x.get("i", "")))

class Knowledge:
    """
    Knowledge graph core management client.

    Provides methods for managing knowledge graph cores, including listing
    available cores, loading them into flows, and unloading them. KG cores
    are pre-built knowledge graph datasets that enhance RAG capabilities.
    """

    def __init__(self, api):
        """
        Initialize Knowledge client.

        Args:
            api: Parent Api instance for making requests
        """
        self.api = api

    def request(self, request):
        """
        Make a knowledge-scoped API request.

        Args:
            request: Request payload dictionary

        Returns:
            dict: Response object
        """
        return self.api.request(f"knowledge", request)

    def list_kg_cores(self, user="trustgraph"):
        """
        List all available knowledge graph cores.

        Retrieves the IDs of all KG cores available for the specified user.

        Args:
            user: User identifier (default: "trustgraph")

        Returns:
            list[str]: List of KG core identifiers

        Example:
            ```python
            knowledge = api.knowledge()

            # List available KG cores
            cores = knowledge.list_kg_cores(user="trustgraph")
            print(f"Available KG cores: {cores}")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "list-kg-cores",
            "user": user,
        }

        return self.request(request = input)["ids"]

    def delete_kg_core(self, id, user="trustgraph"):
        """
        Delete a knowledge graph core.

        Removes a KG core from storage. This does not affect currently loaded
        cores in flows.

        Args:
            id: KG core identifier to delete
            user: User identifier (default: "trustgraph")

        Example:
            ```python
            knowledge = api.knowledge()

            # Delete a KG core
            knowledge.delete_kg_core(id="medical-kb-v1", user="trustgraph")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "delete-kg-core",
            "user": user,
            "id": id,
        }

        self.request(request = input)

    def load_kg_core(self, id, user="trustgraph", flow="default",
                     collection="default"):
        """
        Load a knowledge graph core into a flow.

        Makes a KG core available for use in queries and RAG operations within
        the specified flow and collection.

        Args:
            id: KG core identifier to load
            user: User identifier (default: "trustgraph")
            flow: Flow instance to load into (default: "default")
            collection: Collection to associate with (default: "default")

        Example:
            ```python
            knowledge = api.knowledge()

            # Load a medical knowledge base into the default flow
            knowledge.load_kg_core(
                id="medical-kb-v1",
                user="trustgraph",
                flow="default",
                collection="medical"
            )

            # Now the flow can use this KG core for RAG queries
            flow = api.flow().id("default")
            response = flow.graph_rag(
                query="What are the symptoms of diabetes?",
                user="trustgraph",
                collection="medical"
            )
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "load-kg-core",
            "user": user,
            "id": id,
            "flow": flow,
            "collection": collection,
        }

        self.request(request = input)

    def unload_kg_core(self, id, user="trustgraph", flow="default"):
        """
        Unload a knowledge graph core from a flow.

        Removes a KG core from active use in the specified flow, freeing
        resources while keeping the core available in storage.

        Args:
            id: KG core identifier to unload
            user: User identifier (default: "trustgraph")
            flow: Flow instance to unload from (default: "default")

        Example:
            ```python
            knowledge = api.knowledge()

            # Unload a KG core when no longer needed
            knowledge.unload_kg_core(
                id="medical-kb-v1",
                user="trustgraph",
                flow="default"
            )
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "unload-kg-core",
            "user": user,
            "id": id,
            "flow": flow,
        }

        self.request(request = input)

