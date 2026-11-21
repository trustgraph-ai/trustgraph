from typing import Dict, Any, Tuple
from ...schema import ExtractionRequest, ExtractionResponse, Triple, EntityContext
from ...schema import Error, Term, IRI, LITERAL, BLANK, TRIPLE
from .base import MessageTranslator


def _encode_term(term):
    if term is None:
        return None
    d = {"type": term.type}
    if term.type == IRI:
        d["iri"] = term.iri
    elif term.type == LITERAL:
        d["value"] = term.value
        if term.datatype:
            d["datatype"] = term.datatype
        if term.language:
            d["language"] = term.language
    elif term.type == BLANK:
        d["id"] = term.id
    elif term.type == TRIPLE and term.triple:
        d["triple"] = _encode_triple(term.triple)
    return d


def _decode_term(d):
    if d is None:
        return None
    t = d.get("type", "")
    return Term(
        type=t,
        iri=d.get("iri", ""),
        id=d.get("id", ""),
        value=d.get("value", ""),
        datatype=d.get("datatype", ""),
        language=d.get("language", ""),
        triple=_decode_triple(d["triple"]) if "triple" in d else None,
    )


def _encode_triple(triple):
    return {
        "s": _encode_term(triple.s),
        "p": _encode_term(triple.p),
        "o": _encode_term(triple.o),
    }


def _decode_triple(d):
    if d is None:
        return None
    return Triple(
        s=_decode_term(d.get("s")),
        p=_decode_term(d.get("p")),
        o=_decode_term(d.get("o")),
    )


def _encode_entity_context(ec):
    d = {
        "entity": _encode_term(ec.entity),
        "context": ec.context,
    }
    if ec.chunk_id:
        d["chunk_id"] = ec.chunk_id
    if ec.rdf_type:
        d["rdf_type"] = ec.rdf_type
    if ec.attributes:
        d["attributes"] = ec.attributes
    return d


def _decode_entity_context(d):
    if d is None:
        return None
    return EntityContext(
        entity=_decode_term(d.get("entity")),
        context=d.get("context", ""),
        chunk_id=d.get("chunk_id", ""),
        rdf_type=d.get("rdf_type", []),
        attributes=d.get("attributes", {}),
    )


class ExtractionRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ExtractionRequest:
        return ExtractionRequest(
            text=data.get("text", ""),
            document_id=data.get("document_id", ""),
        )

    def encode(self, obj: ExtractionRequest) -> Dict[str, Any]:
        return {
            "text": obj.text,
            "document_id": obj.document_id,
        }


class ExtractionResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> ExtractionResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: ExtractionResponse) -> Dict[str, Any]:
        result = {
            "kind": obj.kind,
            "end_of_stream": obj.end_of_stream,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        if obj.triples:
            result["triples"] = [
                _encode_triple(t) for t in obj.triples
            ]

        if obj.entity_contexts:
            result["entity_contexts"] = [
                _encode_entity_context(ec) for ec in obj.entity_contexts
            ]

        return result

    def encode_with_completion(
        self, obj: ExtractionResponse
    ) -> Tuple[Dict[str, Any], bool]:
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final
