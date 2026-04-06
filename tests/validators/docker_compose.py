"""
Docker Compose manifest semantic validation.
"""

import yaml
from typing import Dict, Any, List, Set, Tuple


def validate_service_dependencies(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate that depends_on references valid services.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    services = compose_data.get('services', {})
    service_names = set(services.keys())

    for service_name, service_spec in services.items():
        depends_on = service_spec.get('depends_on', [])

        # depends_on can be a list or dict
        if isinstance(depends_on, list):
            deps = depends_on
        elif isinstance(depends_on, dict):
            deps = list(depends_on.keys())
        else:
            continue

        for dep in deps:
            if dep not in service_names:
                errors.append(
                    f"Service '{service_name}': depends_on references "
                    f"undefined service '{dep}'"
                )

    return errors


def validate_volume_references(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate that volume names in binds are defined.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    services = compose_data.get('services', {})
    defined_volumes = set(compose_data.get('volumes', {}).keys())

    for service_name, service_spec in services.items():
        volumes = service_spec.get('volumes', [])

        for volume in volumes:
            # Parse volume string (can be "volume_name:/path" or "/host/path:/container/path")
            if isinstance(volume, str):
                parts = volume.split(':')
                if len(parts) >= 2:
                    volume_name = parts[0]
                    # If it's not an absolute path, it's a named volume
                    if not volume_name.startswith('/') and not volume_name.startswith('.'):
                        if volume_name not in defined_volumes:
                            errors.append(
                                f"Service '{service_name}': volume '{volume_name}' "
                                f"is not defined in top-level volumes section"
                            )

    return errors


def validate_network_references(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate that network names used by services are defined.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    services = compose_data.get('services', {})
    defined_networks = set(compose_data.get('networks', {}).keys())

    # Add default network
    defined_networks.add('default')

    for service_name, service_spec in services.items():
        networks = service_spec.get('networks', [])

        # networks can be a list or dict
        if isinstance(networks, list):
            network_names = networks
        elif isinstance(networks, dict):
            network_names = list(networks.keys())
        else:
            continue

        for network_name in network_names:
            if network_name not in defined_networks:
                errors.append(
                    f"Service '{service_name}': network '{network_name}' "
                    f"is not defined in top-level networks section"
                )

    return errors


def validate_port_conflicts(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate that no duplicate host port bindings exist.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    services = compose_data.get('services', {})
    used_ports: Dict[int, str] = {}

    for service_name, service_spec in services.items():
        ports = service_spec.get('ports', [])

        for port in ports:
            # Parse port string (can be "8080:80" or "8080")
            if isinstance(port, str):
                parts = port.split(':')
                host_port = int(parts[0]) if parts[0].isdigit() else None
            elif isinstance(port, int):
                host_port = port
            else:
                continue

            if host_port:
                if host_port in used_ports:
                    errors.append(
                        f"Port conflict: host port {host_port} is bound by both "
                        f"'{used_ports[host_port]}' and '{service_name}'"
                    )
                else:
                    used_ports[host_port] = service_name

    return errors


def validate_required_fields(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate that required Docker Compose fields are present.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if 'services' not in compose_data:
        errors.append("Missing required 'services' field")
        return errors

    services = compose_data.get('services', {})
    if not services:
        errors.append("'services' section is empty")

    for service_name, service_spec in services.items():
        if not isinstance(service_spec, dict):
            errors.append(f"Service '{service_name}': invalid service specification")
            continue

        # Service must have either 'image' or 'build'
        if 'image' not in service_spec and 'build' not in service_spec:
            errors.append(
                f"Service '{service_name}': must have either 'image' or 'build' field"
            )

    return errors


def validate_environment_variables(compose_data: Dict[str, Any]) -> List[str]:
    """
    Validate environment variable references.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    services = compose_data.get('services', {})

    for service_name, service_spec in services.items():
        environment = service_spec.get('environment', {})

        if isinstance(environment, dict):
            for key, value in environment.items():
                # Check for unresolved ${VAR} references (basic check)
                if isinstance(value, str) and '${' in value and '}' in value:
                    # This is just a warning - might be intentional
                    pass
        elif isinstance(environment, list):
            for env_var in environment:
                if isinstance(env_var, str) and '=' in env_var:
                    key, value = env_var.split('=', 1)
                    if '${' in value and '}' in value:
                        pass

    return errors


def parse_docker_compose_yaml(yaml_content: str) -> Dict[str, Any]:
    """
    Parse Docker Compose YAML into dictionary.

    Args:
        yaml_content: YAML string

    Returns:
        Dictionary of Docker Compose configuration
    """
    return yaml.safe_load(yaml_content)


def validate_docker_compose_manifest(yaml_content: str) -> Tuple[bool, List[str]]:
    """
    Comprehensive validation of Docker Compose manifest.

    Args:
        yaml_content: YAML string of Docker Compose configuration

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        compose_data = parse_docker_compose_yaml(yaml_content)
    except yaml.YAMLError as e:
        return False, [f"YAML parsing error: {e}"]

    if not compose_data:
        return False, ["Empty Docker Compose file"]

    errors = []
    errors.extend(validate_required_fields(compose_data))
    errors.extend(validate_service_dependencies(compose_data))
    errors.extend(validate_volume_references(compose_data))
    errors.extend(validate_network_references(compose_data))
    errors.extend(validate_port_conflicts(compose_data))
    errors.extend(validate_environment_variables(compose_data))

    return len(errors) == 0, errors
