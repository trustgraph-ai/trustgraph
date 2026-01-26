from typing import Dict, Any, List
from ...schema import Term, Triple, RowSchema, Field, IRI, BLANK, LITERAL, TRIPLE
from .base import Translator


class TermTranslator(Translator):
    """
    Translator for Term schema objects.

    Wire format (compact keys):
    - "t": type (i/b/l/t)
    - "i": iri (for IRI type)
    - "d": id (for BLANK type)
    - "v": value (for LITERAL type)
    - "dt": datatype (for LITERAL type)
    - "ln": language (for LITERAL type)
    - "tr": triple (for TRIPLE type, nested)
    """

    def to_pulsar(self, data: Dict[str, Any]) -> Term:
        term_type = data.get("t", "")

        if term_type == IRI:
            return Term(type=IRI, iri=data.get("i", ""))

        elif term_type == BLANK:
            return Term(type=BLANK, id=data.get("d", ""))

        elif term_type == LITERAL:
            return Term(
                type=LITERAL,
                value=data.get("v", ""),
                datatype=data.get("dt", ""),
                language=data.get("ln", ""),
            )

        elif term_type == TRIPLE:
            # Nested triple - use TripleTranslator
            triple_data = data.get("tr")
            if triple_data:
                triple = _triple_translator_to_pulsar(triple_data)
            else:
                triple = None
            return Term(type=TRIPLE, triple=triple)

        else:
            # Unknown or empty type
            return Term(type=term_type)

    def from_pulsar(self, obj: Term) -> Dict[str, Any]:
        result: Dict[str, Any] = {"t": obj.type}

        if obj.type == IRI:
            result["i"] = obj.iri

        elif obj.type == BLANK:
            result["d"] = obj.id

        elif obj.type == LITERAL:
            result["v"] = obj.value
            if obj.datatype:
                result["dt"] = obj.datatype
            if obj.language:
                result["ln"] = obj.language

        elif obj.type == TRIPLE:
            if obj.triple:
                result["tr"] = _triple_translator_from_pulsar(obj.triple)

        return result


# Module-level helper functions to avoid circular instantiation
def _triple_translator_to_pulsar(data: Dict[str, Any]) -> Triple:
    term_translator = TermTranslator()
    return Triple(
        s=term_translator.to_pulsar(data["s"]) if data.get("s") else None,
        p=term_translator.to_pulsar(data["p"]) if data.get("p") else None,
        o=term_translator.to_pulsar(data["o"]) if data.get("o") else None,
        g=data.get("g"),
    )


def _triple_translator_from_pulsar(obj: Triple) -> Dict[str, Any]:
    term_translator = TermTranslator()
    result: Dict[str, Any] = {}

    if obj.s:
        result["s"] = term_translator.from_pulsar(obj.s)
    if obj.p:
        result["p"] = term_translator.from_pulsar(obj.p)
    if obj.o:
        result["o"] = term_translator.from_pulsar(obj.o)
    if obj.g:
        result["g"] = obj.g

    return result


class TripleTranslator(Translator):
    """Translator for Triple schema objects (quads with optional graph)"""

    def __init__(self):
        self.term_translator = TermTranslator()

    def to_pulsar(self, data: Dict[str, Any]) -> Triple:
        return Triple(
            s=self.term_translator.to_pulsar(data["s"]) if data.get("s") else None,
            p=self.term_translator.to_pulsar(data["p"]) if data.get("p") else None,
            o=self.term_translator.to_pulsar(data["o"]) if data.get("o") else None,
            g=data.get("g"),
        )

    def from_pulsar(self, obj: Triple) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        if obj.s:
            result["s"] = self.term_translator.from_pulsar(obj.s)
        if obj.p:
            result["p"] = self.term_translator.from_pulsar(obj.p)
        if obj.o:
            result["o"] = self.term_translator.from_pulsar(obj.o)
        if obj.g:
            result["g"] = obj.g

        return result


# Backward compatibility alias
ValueTranslator = TermTranslator


class SubgraphTranslator(Translator):
    """Translator for lists of Triple objects (subgraphs)"""
    
    def __init__(self):
        self.triple_translator = TripleTranslator()
    
    def to_pulsar(self, data: List[Dict[str, Any]]) -> List[Triple]:
        return [self.triple_translator.to_pulsar(t) for t in data]
    
    def from_pulsar(self, obj: List[Triple]) -> List[Dict[str, Any]]:
        return [self.triple_translator.from_pulsar(t) for t in obj]


class RowSchemaTranslator(Translator):
    """Translator for RowSchema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> RowSchema:
        """Convert dict to RowSchema Pulsar object"""
        fields = []
        for field_data in data.get("fields", []):
            field = Field(
                name=field_data.get("name", ""),
                type=field_data.get("type", "string"),
                size=field_data.get("size", 0),
                primary=field_data.get("primary", False),
                description=field_data.get("description", ""),
                required=field_data.get("required", False),
                indexed=field_data.get("indexed", False),
                enum_values=field_data.get("enum_values", [])
            )
            fields.append(field)
        
        return RowSchema(
            name=data.get("name", ""),
            description=data.get("description", ""),
            fields=fields
        )
    
    def from_pulsar(self, obj: RowSchema) -> Dict[str, Any]:
        """Convert RowSchema Pulsar object to JSON-serializable dictionary"""
        result = {
            "name": obj.name,
            "description": obj.description,
            "fields": []
        }
        
        for field in obj.fields:
            field_dict = {
                "name": field.name,
                "type": field.type,
                "size": field.size,
                "primary": field.primary,
                "description": field.description,
                "required": field.required,
                "indexed": field.indexed
            }
            
            # Handle enum_values array
            if field.enum_values:
                field_dict["enum_values"] = list(field.enum_values)
            
            result["fields"].append(field_dict)
        
        return result


class FieldTranslator(Translator):
    """Translator for Field objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> Field:
        """Convert dict to Field Pulsar object"""
        return Field(
            name=data.get("name", ""),
            type=data.get("type", "string"),
            size=data.get("size", 0),
            primary=data.get("primary", False),
            description=data.get("description", ""),
            required=data.get("required", False),
            indexed=data.get("indexed", False),
            enum_values=data.get("enum_values", [])
        )
    
    def from_pulsar(self, obj: Field) -> Dict[str, Any]:
        """Convert Field Pulsar object to JSON-serializable dictionary"""
        result = {
            "name": obj.name,
            "type": obj.type,
            "size": obj.size,
            "primary": obj.primary,
            "description": obj.description,
            "required": obj.required,
            "indexed": obj.indexed
        }
        
        # Handle enum_values array
        if obj.enum_values:
            result["enum_values"] = list(obj.enum_values)
        
        return result


# Create singleton instances for easy access
row_schema_translator = RowSchemaTranslator()
field_translator = FieldTranslator()