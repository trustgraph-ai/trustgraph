"""
TrustGraph configuration semantic validation.
"""

import json
from typing import Dict, Any, List, Tuple, Set


def validate_service_references(config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that configured services reference valid modules.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build set of known module names (this would need to be comprehensive)
    known_modules = {
        'pulsar', 'triple-store-cassandra', 'object-store-cassandra',
        'vector-store-qdrant', 'vector-store-milvus', 'vector-store-pinecone',
        'graph-rag', 'text-completion',
        'embeddings-hf', 'embeddings-fastembed', 'embeddings-openai',
        'openai', 'anthropic', 'ollama', 'bedrock', 'vertexai',
        'trustgraph-base', 'grafana', 'prometheus',
        'override-recursive-chunker', 'override-text-splitter',
        'neo4j', 'astra'
    }

    for idx, service in enumerate(config):
        if not isinstance(service, dict):
            errors.append(f"Configuration item {idx}: not a dictionary")
            continue

        name = service.get('name')
        if not name:
            errors.append(f"Configuration item {idx}: missing 'name' field")
        elif name not in known_modules:
            # This might be intentional for new modules, so just warn
            pass

    return errors


def validate_parameter_types(config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that module parameters are reasonable.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for idx, service in enumerate(config):
        if not isinstance(service, dict):
            continue

        name = service.get('name', f'item-{idx}')
        parameters = service.get('parameters', {})

        if not isinstance(parameters, dict):
            errors.append(f"Service '{name}': parameters must be a dictionary")
            continue

        # Check for common parameter issues
        for param_name, param_value in parameters.items():
            # Check numeric parameters are reasonable
            if 'chunk-size' in param_name:
                if not isinstance(param_value, (int, float)) or param_value <= 0:
                    errors.append(
                        f"Service '{name}': parameter '{param_name}' should be positive number"
                    )

            if 'chunk-overlap' in param_name:
                if not isinstance(param_value, (int, float)) or param_value < 0:
                    errors.append(
                        f"Service '{name}': parameter '{param_name}' should be non-negative number"
                    )

            if 'max-output-tokens' in param_name:
                if not isinstance(param_value, int) or param_value <= 0:
                    errors.append(
                        f"Service '{name}': parameter '{param_name}' should be positive integer"
                    )

            if 'temperature' in param_name:
                if not isinstance(param_value, (int, float)) or not (0 <= param_value <= 2):
                    errors.append(
                        f"Service '{name}': parameter '{param_name}' should be between 0 and 2"
                    )

    return errors


def validate_storage_consistency(config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that graph/object/vector stores are configured consistently.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    service_names = [s.get('name') for s in config if isinstance(s, dict)]

    # Check for storage backends
    has_triple_store = any('triple-store' in name for name in service_names)
    has_object_store = any('object-store' in name for name in service_names)
    has_vector_store = any('vector-store' in name for name in service_names)

    # If using graph-rag, should have all three stores
    if 'graph-rag' in service_names:
        if not has_triple_store:
            errors.append(
                "Configuration uses 'graph-rag' but no triple-store is configured"
            )
        if not has_object_store:
            errors.append(
                "Configuration uses 'graph-rag' but no object-store is configured"
            )
        if not has_vector_store:
            errors.append(
                "Configuration uses 'graph-rag' but no vector-store is configured"
            )

    return errors


def validate_llm_configuration(config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate LLM configuration is present and reasonable.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    service_names = [s.get('name') for s in config if isinstance(s, dict)]

    # Check for at least one LLM provider
    llm_providers = {'openai', 'anthropic', 'ollama', 'bedrock', 'vertexai', 'vllm', 'llamacpp'}
    has_llm = any(name in llm_providers for name in service_names)

    if not has_llm:
        errors.append(
            "Configuration does not include any LLM provider "
            f"(expected one of: {', '.join(llm_providers)})"
        )

    # Check for embeddings
    has_embeddings = any('embeddings' in name for name in service_names)
    if not has_embeddings:
        errors.append(
            "Configuration does not include any embeddings provider"
        )

    return errors


def validate_required_structure(config: Any) -> List[str]:
    """
    Validate basic configuration structure.

    Handles both input format (list of services) and output format (dict).

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Handle output format (dict with tools, collection, etc.)
    if isinstance(config, dict):
        # Just check it's not empty
        if not config:
            errors.append("Configuration is empty")
        return errors

    # Handle input format (list of services)
    if not isinstance(config, list):
        errors.append("Configuration must be a list or dict")
        return errors

    if not config:
        errors.append("Configuration is empty")

    for idx, service in enumerate(config):
        if not isinstance(service, dict):
            errors.append(f"Configuration item {idx}: must be a dictionary")
            continue

        if 'name' not in service:
            errors.append(f"Configuration item {idx}: missing required field 'name'")

        if 'parameters' not in service:
            errors.append(f"Configuration item {idx}: missing required field 'parameters'")

    return errors


def parse_trustgraph_config(json_content: str):
    """
    Parse TrustGraph configuration JSON.

    Args:
        json_content: JSON string

    Returns:
        Configuration (dict or list depending on format)
    """
    return json.loads(json_content)


def validate_trustgraph_config(json_content: str) -> Tuple[bool, List[str]]:
    """
    Comprehensive validation of TrustGraph configuration.

    Args:
        json_content: JSON string of TrustGraph configuration

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        config = parse_trustgraph_config(json_content)
    except json.JSONDecodeError as e:
        return False, [f"JSON parsing error: {e}"]

    errors = []
    errors.extend(validate_required_structure(config))
    errors.extend(validate_service_references(config))
    errors.extend(validate_parameter_types(config))
    errors.extend(validate_storage_consistency(config))
    errors.extend(validate_llm_configuration(config))

    return len(errors) == 0, errors
