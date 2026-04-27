"""
TrustGraph Knowledge Graph Core Management

This module provides interfaces for managing knowledge graph cores in TrustGraph.
KG cores are pre-built knowledge graph datasets that can be loaded and unloaded
into flows for use in queries and RAG operations.
"""

import json
import base64

from .. knowledge import hash, Uri, Literal, QuotedTriple
from .. schema import IRI, LITERAL, TRIPLE
from . types import Triple


def to_value(x):
    """Convert wire format to Uri, Literal, or QuotedTriple."""
    if x.get("t") == IRI:
        return Uri(x.get("i", ""))
    elif x.get("t") == LITERAL:
        return Literal(x.get("v", ""))
    elif x.get("t") == TRIPLE:
        # Wire format uses "tr" key for nested triple dict
        triple_data = x.get("tr")
        if triple_data:
            return QuotedTriple(
                s=to_value(triple_data.get("s", {})),
                p=to_value(triple_data.get("p", {})),
                o=to_value(triple_data.get("o", {})),
            )
        return Literal("")
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

    def list_kg_cores(self):
        """
        List all available knowledge graph cores in this workspace.

        Returns:
            list[str]: List of KG core identifiers
        """

        input = {
            "operation": "list-kg-cores",
            "workspace": self.api.workspace,
        }

        return self.request(request = input)["ids"]

    def delete_kg_core(self, id):
        """
        Delete a knowledge graph core in this workspace.

        Args:
            id: KG core identifier to delete
        """

        input = {
            "operation": "delete-kg-core",
            "workspace": self.api.workspace,
            "id": id,
        }

        self.request(request = input)

    def load_kg_core(self, id, flow="default", collection="default"):
        """
        Load a knowledge graph core into a flow.

        Args:
            id: KG core identifier to load
            flow: Flow instance to load into (default: "default")
            collection: Collection to associate with (default: "default")
        """

        input = {
            "operation": "load-kg-core",
            "workspace": self.api.workspace,
            "id": id,
            "flow": flow,
            "collection": collection,
        }

        self.request(request = input)

    def unload_kg_core(self, id, flow="default"):
        """
        Unload a knowledge graph core from a flow.

        Args:
            id: KG core identifier to unload
            flow: Flow instance to unload from (default: "default")
        """

        input = {
            "operation": "unload-kg-core",
            "workspace": self.api.workspace,
            "id": id,
            "flow": flow,
        }

        self.request(request = input)

