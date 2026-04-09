from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class Translator(ABC):
    """Base class for bidirectional schema ↔ dict translation.

    Translates between external API dicts (JSON from HTTP/WebSocket)
    and internal schema objects (dataclasses).
    """

    @abstractmethod
    def decode(self, data: Dict[str, Any]) -> Any:
        """Convert external dict to schema object."""
        pass

    @abstractmethod
    def encode(self, obj: Any) -> Dict[str, Any]:
        """Convert schema object to external dict."""
        pass


class MessageTranslator(Translator):
    """For complete request/response message translation."""

    def encode_with_completion(self, obj: Any) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final) — for streaming responses."""
        return self.encode(obj), True


class SendTranslator(Translator):
    """For fire-and-forget send operations."""

    def encode(self, obj: Any) -> Dict[str, Any]:
        """Usually not needed for send-only operations."""
        raise NotImplementedError("Send translators don't need encode")


def handle_optional_fields(obj: Any, fields: list) -> Dict[str, Any]:
    """Helper to extract optional fields from a schema object."""
    result = {}
    for field in fields:
        value = getattr(obj, field, None)
        if value is not None:
            result[field] = value
    return result
