import base64
from typing import Dict, Any
from ...schema import Document, TextDocument, Chunk, DocumentEmbeddings, ChunkEmbeddings
from .base import SendTranslator


def _decode_text_payload(payload: str | bytes, charset: str) -> str:
    """
    Decode text-load payloads.

    Historical clients send base64-encoded text, but direct REST callers may
    send raw UTF-8 text. Support both so Unicode text-load requests do not fail
    at the gateway translation layer.
    """
    if isinstance(payload, bytes):
        if not payload.isascii():
            return payload.decode(charset)
        candidate = payload.decode("ascii")
    else:
        if not payload.isascii():
            return payload
        candidate = payload

    try:
        return base64.b64decode(candidate, validate=True).decode(charset)
    except (ValueError, UnicodeDecodeError):
        return candidate


class DocumentTranslator(SendTranslator):
    """Translator for Document schema objects (PDF docs etc.)"""

    def decode(self, data: Dict[str, Any]) -> Document:
        # Handle base64 content validation
        doc = base64.b64decode(data["data"])

        from ...schema import Metadata
        return Document(
            metadata=Metadata(
                id=data.get("id"),
                root=data.get("root", ""),
                collection=data.get("collection", "default"),
            ),
            data=base64.b64encode(doc).decode("utf-8")
        )

    def encode(self, obj: Document) -> Dict[str, Any]:
        result = {
            "data": obj.data
        }

        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.root:
                metadata_dict["root"] = obj.metadata.root
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection

            result["metadata"] = metadata_dict

        return result


class TextDocumentTranslator(SendTranslator):
    """Translator for TextDocument schema objects"""

    def decode(self, data: Dict[str, Any]) -> TextDocument:
        charset = data.get("charset", "utf-8")

        text = _decode_text_payload(data["text"], charset)

        from ...schema import Metadata
        return TextDocument(
            metadata=Metadata(
                id=data.get("id"),
                root=data.get("root", ""),
                collection=data.get("collection", "default"),
            ),
            text=text.encode("utf-8")
        )

    def encode(self, obj: TextDocument) -> Dict[str, Any]:
        result = {
            "text": obj.text.decode("utf-8") if isinstance(obj.text, bytes) else obj.text
        }

        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.root:
                metadata_dict["root"] = obj.metadata.root
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection

            result["metadata"] = metadata_dict

        return result


class ChunkTranslator(SendTranslator):
    """Translator for Chunk schema objects"""

    def decode(self, data: Dict[str, Any]) -> Chunk:
        from ...schema import Metadata
        return Chunk(
            metadata=Metadata(
                id=data.get("id"),
                root=data.get("root", ""),
                collection=data.get("collection", "default"),
            ),
            chunk=data["chunk"].encode("utf-8") if isinstance(data["chunk"], str) else data["chunk"]
        )

    def encode(self, obj: Chunk) -> Dict[str, Any]:
        result = {
            "chunk": obj.chunk.decode("utf-8") if isinstance(obj.chunk, bytes) else obj.chunk
        }

        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.root:
                metadata_dict["root"] = obj.metadata.root
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection

            result["metadata"] = metadata_dict

        return result


class DocumentEmbeddingsTranslator(SendTranslator):
    """Translator for DocumentEmbeddings schema objects"""

    def decode(self, data: Dict[str, Any]) -> DocumentEmbeddings:
        metadata = data.get("metadata", {})

        chunks = [
            ChunkEmbeddings(
                chunk_id=chunk["chunk_id"],
                vector=chunk["vector"]
            )
            for chunk in data.get("chunks", [])
        ]

        from ...schema import Metadata
        return DocumentEmbeddings(
            metadata=Metadata(
                id=metadata.get("id"),
                root=metadata.get("root", ""),
                collection=metadata.get("collection", "default"),
            ),
            chunks=chunks
        )

    def encode(self, obj: DocumentEmbeddings) -> Dict[str, Any]:
        result = {
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "vector": chunk.vector
                }
                for chunk in obj.chunks
            ]
        }

        if obj.metadata:
            metadata_dict = {}
            if obj.metadata.id:
                metadata_dict["id"] = obj.metadata.id
            if obj.metadata.root:
                metadata_dict["root"] = obj.metadata.root
            if obj.metadata.collection:
                metadata_dict["collection"] = obj.metadata.collection

            result["metadata"] = metadata_dict

        return result
