"""
TrustGraph Flow Management

This module provides interfaces for managing and executing TrustGraph flows.
Flows are the primary execution units that provide access to various services
including LLM operations, RAG queries, knowledge graph management, and more.
"""

import json
import base64

from .. knowledge import hash, Uri, Literal
from .. schema import IRI, LITERAL
from . types import Triple
from . exceptions import ProtocolException


def to_value(x):
    """Convert wire format to Uri or Literal."""
    if x.get("t") == IRI:
        return Uri(x.get("i", ""))
    elif x.get("t") == LITERAL:
        return Literal(x.get("v", ""))
    # Fallback for any other type
    return Literal(x.get("v", x.get("i", "")))


def from_value(v):
    """Convert Uri or Literal to wire format."""
    if isinstance(v, Uri):
        return {"t": IRI, "i": str(v)}
    else:
        return {"t": LITERAL, "v": str(v)}

class Flow:
    """
    Flow management client for blueprint and flow instance operations.

    This class provides methods for managing flow blueprints (templates) and
    flow instances (running flows). Blueprints define the structure and
    parameters of flows, while instances represent active flows that can
    execute services.
    """

    def __init__(self, api):
        """
        Initialize Flow client.

        Args:
            api: Parent Api instance for making requests
        """
        self.api = api

    def request(self, path=None, request=None):
        """
        Make a flow-scoped API request.

        Args:
            path: Optional path suffix for flow endpoints
            request: Request payload dictionary

        Returns:
            dict: Response object

        Raises:
            RuntimeError: If request parameter is not specified
        """

        if request is None:
            raise RuntimeError("request must be specified")

        if path:
            return self.api.request(f"flow/{path}", request)
        else:
            return self.api.request(f"flow", request)

    def id(self, id="default"):
        """
        Get a FlowInstance for executing operations on a specific flow.

        Args:
            id: Flow identifier (default: "default")

        Returns:
            FlowInstance: Flow instance for service operations

        Example:
            ```python
            flow = api.flow().id("my-flow")
            response = flow.text_completion(
                system="You are helpful",
                prompt="Hello"
            )
            ```
        """
        return FlowInstance(api=self, id=id)

    def list_blueprints(self):
        """
        List all available flow blueprints.

        Returns:
            list[str]: List of blueprint names

        Example:
            ```python
            blueprints = api.flow().list_blueprints()
            print(blueprints)  # ['default', 'custom-flow', ...]
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "list-blueprints",
        }

        return self.request(request = input)["blueprint-names"]

    def get_blueprint(self, blueprint_name):
        """
        Get a flow blueprint definition by name.

        Args:
            blueprint_name: Name of the blueprint to retrieve

        Returns:
            dict: Blueprint definition as a dictionary

        Example:
            ```python
            blueprint = api.flow().get_blueprint("default")
            print(blueprint)  # Blueprint configuration
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "get-blueprint",
            "blueprint-name": blueprint_name,
        }

        return json.loads(self.request(request = input)["blueprint-definition"])

    def put_blueprint(self, blueprint_name, definition):
        """
        Create or update a flow blueprint.

        Args:
            blueprint_name: Name for the blueprint
            definition: Blueprint definition dictionary

        Example:
            ```python
            definition = {
                "services": ["text-completion", "graph-rag"],
                "parameters": {"model": "gpt-4"}
            }
            api.flow().put_blueprint("my-blueprint", definition)
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "put-blueprint",
            "blueprint-name": blueprint_name,
            "blueprint-definition": json.dumps(definition),
        }

        self.request(request = input)

    def delete_blueprint(self, blueprint_name):
        """
        Delete a flow blueprint.

        Args:
            blueprint_name: Name of the blueprint to delete

        Example:
            ```python
            api.flow().delete_blueprint("old-blueprint")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "delete-blueprint",
            "blueprint-name": blueprint_name,
        }

        self.request(request = input)

    def list(self):
        """
        List all active flow instances.

        Returns:
            list[str]: List of flow instance IDs

        Example:
            ```python
            flows = api.flow().list()
            print(flows)  # ['default', 'flow-1', 'flow-2', ...]
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "list-flows",
        }

        return self.request(request = input)["flow-ids"]

    def get(self, id):
        """
        Get the definition of a running flow instance.

        Args:
            id: Flow instance ID

        Returns:
            dict: Flow instance definition

        Example:
            ```python
            flow_def = api.flow().get("default")
            print(flow_def)
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "get-flow",
            "flow-id": id,
        }

        return json.loads(self.request(request = input)["flow"])

    def start(self, blueprint_name, id, description, parameters=None):
        """
        Start a new flow instance from a blueprint.

        Args:
            blueprint_name: Name of the blueprint to instantiate
            id: Unique identifier for the flow instance
            description: Human-readable description
            parameters: Optional parameters dictionary

        Example:
            ```python
            api.flow().start(
                blueprint_name="default",
                id="my-flow",
                description="My custom flow",
                parameters={"model": "gpt-4"}
            )
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "start-flow",
            "flow-id": id,
            "blueprint-name": blueprint_name,
            "description": description,
        }

        if parameters:
            input["parameters"] = parameters

        self.request(request = input)

    def stop(self, id):
        """
        Stop a running flow instance.

        Args:
            id: Flow instance ID to stop

        Example:
            ```python
            api.flow().stop("my-flow")
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "operation": "stop-flow",
            "flow-id": id,
        }

        self.request(request = input)

class FlowInstance:
    """
    Flow instance client for executing services on a specific flow.

    This class provides access to all TrustGraph services including:
    - Text completion and embeddings
    - Agent operations with state management
    - Graph and document RAG queries
    - Knowledge graph operations (triples, objects)
    - Document loading and processing
    - Natural language to GraphQL query conversion
    - Structured data analysis and schema detection
    - MCP tool execution
    - Prompt templating

    Services are accessed through a running flow instance identified by ID.
    """

    def __init__(self, api, id):
        """
        Initialize FlowInstance.

        Args:
            api: Parent Flow client
            id: Flow instance identifier
        """
        self.api = api
        self.id = id

    def request(self, path, request):
        """
        Make a service request on this flow instance.

        Args:
            path: Service path (e.g., "service/text-completion")
            request: Request payload dictionary

        Returns:
            dict: Service response
        """
        return self.api.request(path = f"{self.id}/{path}", request = request)

    def text_completion(self, system, prompt):
        """
        Execute text completion using the flow's LLM.

        Args:
            system: System prompt defining the assistant's behavior
            prompt: User prompt/question

        Returns:
            str: Generated response text

        Example:
            ```python
            flow = api.flow().id("default")
            response = flow.text_completion(
                system="You are a helpful assistant",
                prompt="What is quantum computing?"
            )
            print(response)
            ```
        """

        # The input consists of system and prompt strings
        input = {
            "system": system,
            "prompt": prompt
        }

        return self.request(
            "service/text-completion",
            input
        )["response"]

    def agent(self, question, user="trustgraph", state=None, group=None, history=None):
        """
        Execute an agent operation with reasoning and tool use capabilities.

        Agents can perform multi-step reasoning, use tools, and maintain conversation
        state across interactions. This is a synchronous non-streaming version.

        Args:
            question: User question or instruction
            user: User identifier (default: "trustgraph")
            state: Optional state dictionary for stateful conversations
            group: Optional group identifier for multi-user contexts
            history: Optional conversation history as list of message dicts

        Returns:
            str: Agent's final answer

        Example:
            ```python
            flow = api.flow().id("default")

            # Simple question
            answer = flow.agent(
                question="What is the capital of France?",
                user="trustgraph"
            )

            # With conversation history
            history = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"}
            ]
            answer = flow.agent(
                question="Tell me about Paris",
                user="trustgraph",
                history=history
            )
            ```
        """

        # The input consists of a question and optional context
        input = {
            "question": question,
            "user": user,
        }
        
        # Only include state if it has a value
        if state is not None:
            input["state"] = state
            
        # Only include group if it has a value
        if group is not None:
            input["group"] = group
            
        # Always include history (empty list if None)
        input["history"] = history or []

        return self.request(
            "service/agent",
            input
        )["answer"]

    def graph_rag(
            self, query, user="trustgraph", collection="default",
            entity_limit=50, triple_limit=30, max_subgraph_size=150,
            max_path_length=2,
    ):
        """
        Execute graph-based Retrieval-Augmented Generation (RAG) query.

        Graph RAG uses knowledge graph structure to find relevant context by
        traversing entity relationships, then generates a response using an LLM.

        Args:
            query: Natural language query
            user: User/keyspace identifier (default: "trustgraph")
            collection: Collection identifier (default: "default")
            entity_limit: Maximum entities to retrieve (default: 50)
            triple_limit: Maximum triples per entity (default: 30)
            max_subgraph_size: Maximum total triples in subgraph (default: 150)
            max_path_length: Maximum traversal depth (default: 2)

        Returns:
            str: Generated response incorporating graph context

        Example:
            ```python
            flow = api.flow().id("default")
            response = flow.graph_rag(
                query="Tell me about Marie Curie's discoveries",
                user="trustgraph",
                collection="scientists",
                entity_limit=20,
                max_path_length=3
            )
            print(response)
            ```
        """

        # The input consists of a question
        input = {
            "query": query,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-size": max_subgraph_size,
            "max-path-length": max_path_length,
        }

        return self.request(
            "service/graph-rag",
            input
        )["response"]

    def document_rag(
            self, query, user="trustgraph", collection="default",
            doc_limit=10,
    ):
        """
        Execute document-based Retrieval-Augmented Generation (RAG) query.

        Document RAG uses vector embeddings to find relevant document chunks,
        then generates a response using an LLM with those chunks as context.

        Args:
            query: Natural language query
            user: User/keyspace identifier (default: "trustgraph")
            collection: Collection identifier (default: "default")
            doc_limit: Maximum document chunks to retrieve (default: 10)

        Returns:
            str: Generated response incorporating document context

        Example:
            ```python
            flow = api.flow().id("default")
            response = flow.document_rag(
                query="Summarize the key findings",
                user="trustgraph",
                collection="research-papers",
                doc_limit=5
            )
            print(response)
            ```
        """

        # The input consists of a question
        input = {
            "query": query,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
        }

        return self.request(
            "service/document-rag",
            input
        )["response"]

    def embeddings(self, text):
        """
        Generate vector embeddings for text.

        Converts text into dense vector representations suitable for semantic
        search and similarity comparison.

        Args:
            text: Input text to embed

        Returns:
            list[float]: Vector embedding

        Example:
            ```python
            flow = api.flow().id("default")
            vectors = flow.embeddings("quantum computing")
            print(f"Embedding dimension: {len(vectors)}")
            ```
        """

        # The input consists of a text block
        input = {
            "text": text
        }

        return self.request(
            "service/embeddings",
            input
        )["vectors"]

    def graph_embeddings_query(self, text, user, collection, limit=10):
        """
        Query knowledge graph entities using semantic similarity.

        Finds entities in the knowledge graph whose descriptions are semantically
        similar to the input text, using vector embeddings.

        Args:
            text: Query text for semantic search
            user: User/keyspace identifier
            collection: Collection identifier
            limit: Maximum number of results (default: 10)

        Returns:
            dict: Query results with similar entities

        Example:
            ```python
            flow = api.flow().id("default")
            results = flow.graph_embeddings_query(
                text="physicist who discovered radioactivity",
                user="trustgraph",
                collection="scientists",
                limit=5
            )
            ```
        """

        # First convert text to embeddings vectors
        emb_result = self.embeddings(text=text)
        vectors = emb_result.get("vectors", [])

        # Query graph embeddings for semantic search
        input = {
            "vectors": vectors,
            "user": user,
            "collection": collection,
            "limit": limit
        }

        return self.request(
            "service/graph-embeddings",
            input
        )

    def document_embeddings_query(self, text, user, collection, limit=10):
        """
        Query document chunks using semantic similarity.

        Finds document chunks whose content is semantically similar to the
        input text, using vector embeddings.

        Args:
            text: Query text for semantic search
            user: User/keyspace identifier
            collection: Collection identifier
            limit: Maximum number of results (default: 10)

        Returns:
            dict: Query results with similar document chunks

        Example:
            ```python
            flow = api.flow().id("default")
            results = flow.document_embeddings_query(
                text="machine learning algorithms",
                user="trustgraph",
                collection="research-papers",
                limit=5
            )
            ```
        """

        # First convert text to embeddings vectors
        emb_result = self.embeddings(text=text)
        vectors = emb_result.get("vectors", [])

        # Query document embeddings for semantic search
        input = {
            "vectors": vectors,
            "user": user,
            "collection": collection,
            "limit": limit
        }

        return self.request(
            "service/document-embeddings",
            input
        )

    def prompt(self, id, variables):
        """
        Execute a prompt template with variable substitution.

        Prompt templates allow reusable prompt patterns with dynamic variable
        substitution, useful for consistent prompt engineering.

        Args:
            id: Prompt template identifier
            variables: Dictionary of variable name to value mappings

        Returns:
            str or dict: Rendered prompt result (text or structured object)

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            flow = api.flow().id("default")

            # Text template
            result = flow.prompt(
                id="summarize-template",
                variables={"topic": "quantum computing", "length": "brief"}
            )

            # Structured template
            result = flow.prompt(
                id="extract-entities",
                variables={"text": "Marie Curie won Nobel Prizes"}
            )
            ```
        """

        input = {
            "id": id,
            "variables": variables
        }

        object = self.request(
            "service/prompt",
            input
        )

        if "text" in object:
            return object["text"]

        if "object" in object:
            try:
                return json.loads(object["object"])
            except Exception as e:
                raise ProtocolException(
                    "Returned object not well-formed JSON"
                )

        raise ProtocolException("Response not formatted correctly")

    def mcp_tool(self, name, parameters={}):
        """
        Execute a Model Context Protocol (MCP) tool.

        MCP tools provide extensible functionality for agents and workflows,
        allowing integration with external systems and services.

        Args:
            name: Tool name/identifier
            parameters: Tool parameters dictionary (default: {})

        Returns:
            str or dict: Tool execution result

        Raises:
            ProtocolException: If response format is invalid

        Example:
            ```python
            flow = api.flow().id("default")

            # Execute a tool
            result = flow.mcp_tool(
                name="search-web",
                parameters={"query": "latest AI news", "limit": 5}
            )
            ```
        """

        # The input consists of name and parameters
        input = {
            "name": name,
            "parameters": parameters,
        }

        object = self.request(
            "service/mcp-tool",
            input
        )

        if "text" in object:
            return object["text"]

        if "object" in object:
            try:
                return object["object"]
            except Exception as e:
                raise ProtocolException(
                    "Returned object not well-formed JSON"
                )

        raise ProtocolException("Response not formatted correctly")

    def triples_query(
            self, s=None, p=None, o=None,
            user=None, collection=None, limit=10000
    ):
        """
        Query knowledge graph triples using pattern matching.

        Searches for RDF triples matching the given subject, predicate, and/or
        object patterns. Unspecified parameters act as wildcards.

        Args:
            s: Subject URI (optional, use None for wildcard)
            p: Predicate URI (optional, use None for wildcard)
            o: Object URI or Literal (optional, use None for wildcard)
            user: User/keyspace identifier (optional)
            collection: Collection identifier (optional)
            limit: Maximum results to return (default: 10000)

        Returns:
            list[Triple]: List of matching Triple objects

        Raises:
            RuntimeError: If s or p is not a Uri, or o is not Uri/Literal

        Example:
            ```python
            from trustgraph.knowledge import Uri, Literal

            flow = api.flow().id("default")

            # Find all triples about a specific subject
            triples = flow.triples_query(
                s=Uri("http://example.org/person/marie-curie"),
                user="trustgraph",
                collection="scientists"
            )

            # Find all instances of a specific relationship
            triples = flow.triples_query(
                p=Uri("http://example.org/ontology/discovered"),
                limit=100
            )
            ```
        """

        input = {
            "limit": limit
        }

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

        if s:
            if not isinstance(s, Uri):
                raise RuntimeError("s must be Uri")
            input["s"] = from_value(s)

        if p:
            if not isinstance(p, Uri):
                raise RuntimeError("p must be Uri")
            input["p"] = from_value(p)

        if o:
            if not isinstance(o, Uri) and not isinstance(o, Literal):
                raise RuntimeError("o must be Uri or Literal")
            input["o"] = from_value(o)

        object = self.request(
            "service/triples",
            input
        )

        return [
            Triple(
                s=to_value(t["s"]),
                p=to_value(t["p"]),
                o=to_value(t["o"])
            )
            for t in object["response"]
        ]

    def load_document(
            self, document, id=None, metadata=None, user=None,
            collection=None,
    ):
        """
        Load a binary document for processing.

        Uploads a document (PDF, DOCX, images, etc.) for extraction and
        processing through the flow's document pipeline.

        Args:
            document: Document content as bytes
            id: Optional document identifier (auto-generated if None)
            metadata: Optional metadata (list of Triples or object with emit method)
            user: User/keyspace identifier (optional)
            collection: Collection identifier (optional)

        Returns:
            dict: Processing response

        Raises:
            RuntimeError: If metadata is provided without id

        Example:
            ```python
            flow = api.flow().id("default")

            # Load a PDF document
            with open("research.pdf", "rb") as f:
                result = flow.load_document(
                    document=f.read(),
                    id="research-001",
                    user="trustgraph",
                    collection="papers"
                )
            ```
        """

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(document)

        triples = []

        def emit(t):
            triples.append(t)

        if metadata:
            metadata.emit(
                lambda t: triples.append({
                    "s": from_value(t["s"]),
                    "p": from_value(t["p"]),
                    "o": from_value(t["o"]),
                })
            )

        input = {
            "id": id,
            "metadata": triples,
            "data": base64.b64encode(document).decode("utf-8"),
        }

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

        return self.request(
            "service/document-load",
            input
        )

    def load_text(
            self, text, id=None, metadata=None, charset="utf-8",
            user=None, collection=None,
    ):
        """
        Load text content for processing.

        Uploads text content for extraction and processing through the flow's
        text pipeline.

        Args:
            text: Text content as bytes
            id: Optional document identifier (auto-generated if None)
            metadata: Optional metadata (list of Triples or object with emit method)
            charset: Character encoding (default: "utf-8")
            user: User/keyspace identifier (optional)
            collection: Collection identifier (optional)

        Returns:
            dict: Processing response

        Raises:
            RuntimeError: If metadata is provided without id

        Example:
            ```python
            flow = api.flow().id("default")

            # Load text content
            text_content = b"This is the document content..."
            result = flow.load_text(
                text=text_content,
                id="text-001",
                charset="utf-8",
                user="trustgraph",
                collection="documents"
            )
            ```
        """

        if id is None:

            if metadata is not None:

                # Situation makes no sense.  What can the metadata possibly
                # mean if the caller doesn't know the document ID.
                # Metadata should relate to the document by ID
                raise RuntimeError("Can't specify metadata without id")

            id = hash(text)

        triples = []

        if metadata:
            metadata.emit(
                lambda t: triples.append({
                    "s": from_value(t["s"]),
                    "p": from_value(t["p"]),
                    "o": from_value(t["o"]),
                })
            )

        input = {
            "id": id,
            "metadata": triples,
            "charset": charset,
            "text": base64.b64encode(text).decode("utf-8"),
        }

        if user:
            input["user"] = user

        if collection:
            input["collection"] = collection

        return self.request(
            "service/text-load",
            input
        )

    def objects_query(
            self, query, user="trustgraph", collection="default",
            variables=None, operation_name=None
    ):
        """
        Execute a GraphQL query against structured objects in the knowledge graph.

        Queries structured data using GraphQL syntax, allowing complex queries
        with filtering, aggregation, and relationship traversal.

        Args:
            query: GraphQL query string
            user: User/keyspace identifier (default: "trustgraph")
            collection: Collection identifier (default: "default")
            variables: Optional query variables dictionary
            operation_name: Optional operation name for multi-operation documents

        Returns:
            dict: GraphQL response with 'data', 'errors', and/or 'extensions' fields

        Raises:
            ProtocolException: If system-level error occurs

        Example:
            ```python
            flow = api.flow().id("default")

            # Simple query
            query = '''
            {
              scientists(limit: 10) {
                name
                field
                discoveries
              }
            }
            '''
            result = flow.objects_query(
                query=query,
                user="trustgraph",
                collection="scientists"
            )

            # Query with variables
            query = '''
            query GetScientist($name: String!) {
              scientists(name: $name) {
                name
                nobelPrizes
              }
            }
            '''
            result = flow.objects_query(
                query=query,
                variables={"name": "Marie Curie"}
            )
            ```
        """

        # The input consists of a GraphQL query and optional variables
        input = {
            "query": query,
            "user": user,
            "collection": collection,
        }

        if variables:
            input["variables"] = variables

        if operation_name:
            input["operation_name"] = operation_name

        response = self.request(
            "service/objects",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        # Return the GraphQL response structure
        result = {}
        
        if "data" in response:
            result["data"] = response["data"]
            
        if "errors" in response and response["errors"]:
            result["errors"] = response["errors"]
            
        if "extensions" in response and response["extensions"]:
            result["extensions"] = response["extensions"]
            
        return result

    def nlp_query(self, question, max_results=100):
        """
        Convert a natural language question to a GraphQL query.
        
        Args:
            question: Natural language question
            max_results: Maximum number of results to return (default: 100)
            
        Returns:
            dict with graphql_query, variables, detected_schemas, confidence
        """
        
        input = {
            "question": question,
            "max_results": max_results
        }
        
        response = self.request(
            "service/nlp-query",
            input
        )
        
        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")
        
        return response

    def structured_query(self, question, user="trustgraph", collection="default"):
        """
        Execute a natural language question against structured data.
        Combines NLP query conversion and GraphQL execution.
        
        Args:
            question: Natural language question
            user: Cassandra keyspace identifier (default: "trustgraph")
            collection: Data collection identifier (default: "default")
            
        Returns:
            dict with data and optional errors
        """
        
        input = {
            "question": question,
            "user": user,
            "collection": collection
        }
        
        response = self.request(
            "service/structured-query",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        return response

    def detect_type(self, sample):
        """
        Detect the data type of a structured data sample.

        Args:
            sample: Data sample to analyze (string content)

        Returns:
            dict with detected_type, confidence, and optional metadata
        """

        input = {
            "operation": "detect-type",
            "sample": sample
        }

        response = self.request(
            "service/structured-diag",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        return response["detected-type"]

    def generate_descriptor(self, sample, data_type, schema_name, options=None):
        """
        Generate a descriptor for structured data mapping to a specific schema.

        Args:
            sample: Data sample to analyze (string content)
            data_type: Data type (csv, json, xml)
            schema_name: Target schema name for descriptor generation
            options: Optional parameters (e.g., delimiter for CSV)

        Returns:
            dict with descriptor and metadata
        """

        input = {
            "operation": "generate-descriptor",
            "sample": sample,
            "type": data_type,
            "schema-name": schema_name
        }

        if options:
            input["options"] = options

        response = self.request(
            "service/structured-diag",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        return response["descriptor"]

    def diagnose_data(self, sample, schema_name=None, options=None):
        """
        Perform combined data diagnosis: detect type and generate descriptor.

        Args:
            sample: Data sample to analyze (string content)
            schema_name: Optional target schema name for descriptor generation
            options: Optional parameters (e.g., delimiter for CSV)

        Returns:
            dict with detected_type, confidence, descriptor, and metadata
        """

        input = {
            "operation": "diagnose",
            "sample": sample
        }

        if schema_name:
            input["schema-name"] = schema_name

        if options:
            input["options"] = options

        response = self.request(
            "service/structured-diag",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        return response

    def schema_selection(self, sample, options=None):
        """
        Select matching schemas for a data sample using prompt analysis.

        Args:
            sample: Data sample to analyze (string content)
            options: Optional parameters

        Returns:
            dict with schema_matches array and metadata
        """

        input = {
            "operation": "schema-selection",
            "sample": sample
        }

        if options:
            input["options"] = options

        response = self.request(
            "service/structured-diag",
            input
        )

        # Check for system-level error
        if "error" in response and response["error"]:
            error_type = response["error"].get("type", "unknown")
            error_message = response["error"].get("message", "Unknown error")
            raise ProtocolException(f"{error_type}: {error_message}")

        return response["schema-matches"]

