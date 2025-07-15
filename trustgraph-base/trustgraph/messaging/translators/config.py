from typing import Dict, Any, Tuple
from ...schema import ConfigRequest, ConfigResponse, ConfigKey, ConfigValue
from .base import MessageTranslator


class ConfigRequestTranslator(MessageTranslator):
    """Translator for ConfigRequest schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> ConfigRequest:
        keys = None
        if "keys" in data:
            keys = [
                ConfigKey(
                    type=k["type"],
                    key=k["key"]
                )
                for k in data["keys"]
            ]
        
        values = None
        if "values" in data:
            values = [
                ConfigValue(
                    type=v["type"],
                    key=v["key"],
                    value=v["value"]
                )
                for v in data["values"]
            ]
        
        return ConfigRequest(
            operation=data.get("operation"),
            keys=keys,
            type=data.get("type"),
            values=values
        )
    
    def from_pulsar(self, obj: ConfigRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.operation is not None:
            result["operation"] = obj.operation

        if obj.type is not None:
            result["type"] = obj.type
        
        if obj.keys is not None:
            result["keys"] = [
                {
                    "type": k.type,
                    "key": k.key
                }
                for k in obj.keys
            ]
        
        if obj.values is not None:
            result["values"] = [
                {
                    "type": v.type,
                    "key": v.key,
                    "value": v.value
                }
                for v in obj.values
            ]
        
        return result


class ConfigResponseTranslator(MessageTranslator):
    """Translator for ConfigResponse schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> ConfigResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: ConfigResponse) -> Dict[str, Any]:
        result = {}
        
        if obj.version is not None:
            result["version"] = obj.version
        
        if obj.values is not None:
            result["values"] = [
                {
                    "type": v.type,
                    "key": v.key,
                    "value": v.value
                }
                for v in obj.values
            ]
        
        if obj.directory is not None:
            result["directory"] = obj.directory
        
        if obj.config is not None:
            result["config"] = obj.config
        
        return result
    
    def from_response_with_completion(self, obj: ConfigResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True
