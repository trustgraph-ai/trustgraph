from typing import Dict, Any, List
from ...schema import Value, Triple, RowSchema, Field
from .base import Translator


class ValueTranslator(Translator):
    """Translator for Value schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> Value:
        return Value(value=data["v"], is_uri=data["e"])
    
    def from_pulsar(self, obj: Value) -> Dict[str, Any]:
        return {"v": obj.value, "e": obj.is_uri}


class TripleTranslator(Translator):
    """Translator for Triple schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> Triple:
        return Triple(
            s=self.value_translator.to_pulsar(data["s"]),
            p=self.value_translator.to_pulsar(data["p"]),
            o=self.value_translator.to_pulsar(data["o"])
        )
    
    def from_pulsar(self, obj: Triple) -> Dict[str, Any]:
        return {
            "s": self.value_translator.from_pulsar(obj.s),
            "p": self.value_translator.from_pulsar(obj.p),
            "o": self.value_translator.from_pulsar(obj.o)
        }


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