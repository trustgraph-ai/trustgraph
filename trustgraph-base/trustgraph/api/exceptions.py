"""
TrustGraph API Exceptions

Exception hierarchy for errors returned by TrustGraph services.
Each service error type maps to a specific exception class.
"""

# Protocol-level exceptions (communication errors)
class ProtocolException(Exception):
    """Raised when WebSocket protocol errors occur"""
    pass


# Base class for all TrustGraph application errors
class TrustGraphException(Exception):
    """Base class for all TrustGraph service errors"""
    def __init__(self, message: str, error_type: str = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


# Service-specific exceptions
class AgentError(TrustGraphException):
    """Agent service error"""
    pass


class ConfigError(TrustGraphException):
    """Configuration service error"""
    pass


class DocumentRagError(TrustGraphException):
    """Document RAG retrieval error"""
    pass


class FlowError(TrustGraphException):
    """Flow management error"""
    pass


class GatewayError(TrustGraphException):
    """API Gateway error"""
    pass


class GraphRagError(TrustGraphException):
    """Graph RAG retrieval error"""
    pass


class LLMError(TrustGraphException):
    """LLM service error"""
    pass


class LoadError(TrustGraphException):
    """Data loading error"""
    pass


class LookupError(TrustGraphException):
    """Lookup/search error"""
    pass


class NLPQueryError(TrustGraphException):
    """NLP query service error"""
    pass


class ObjectsQueryError(TrustGraphException):
    """Objects query service error"""
    pass


class RequestError(TrustGraphException):
    """Request processing error"""
    pass


class StructuredQueryError(TrustGraphException):
    """Structured query service error"""
    pass


class UnexpectedError(TrustGraphException):
    """Unexpected/unknown error"""
    pass


# Mapping from error type string to exception class
ERROR_TYPE_MAPPING = {
    "agent-error": AgentError,
    "config-error": ConfigError,
    "document-rag-error": DocumentRagError,
    "flow-error": FlowError,
    "gateway-error": GatewayError,
    "graph-rag-error": GraphRagError,
    "llm-error": LLMError,
    "load-error": LoadError,
    "lookup-error": LookupError,
    "nlp-query-error": NLPQueryError,
    "objects-query-error": ObjectsQueryError,
    "request-error": RequestError,
    "structured-query-error": StructuredQueryError,
    "unexpected-error": UnexpectedError,
}


def raise_from_error_dict(error_dict: dict) -> None:
    """
    Raise appropriate exception from TrustGraph error dictionary.

    Args:
        error_dict: Dictionary with 'type' and 'message' keys

    Raises:
        Appropriate TrustGraphException subclass based on error type
    """
    error_type = error_dict.get("type", "unexpected-error")
    message = error_dict.get("message", "Unknown error")

    # Look up exception class, default to UnexpectedError
    exception_class = ERROR_TYPE_MAPPING.get(error_type, UnexpectedError)

    # Raise the appropriate exception
    raise exception_class(message, error_type)


# Legacy exception for backwards compatibility
ApplicationException = TrustGraphException
