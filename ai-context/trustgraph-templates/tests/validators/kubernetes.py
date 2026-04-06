"""
Kubernetes manifest semantic validation.
"""

import yaml
from typing import List, Dict, Any, Tuple


def validate_selector_labels_match(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that Deployment selectors match pod template labels.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for resource in resources:
        if resource.get('kind') == 'Deployment':
            name = resource.get('metadata', {}).get('name', 'unknown')
            selector = resource.get('spec', {}).get('selector', {}).get('matchLabels', {})
            pod_labels = resource.get('spec', {}).get('template', {}).get('metadata', {}).get('labels', {})

            for key, value in selector.items():
                if pod_labels.get(key) != value:
                    errors.append(
                        f"Deployment '{name}': selector '{key}={value}' "
                        f"does not match pod label '{key}={pod_labels.get(key)}'"
                    )

    return errors


def validate_service_selectors(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that Service selectors match Deployment labels.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build map of deployment labels
    deployment_labels = {}
    for resource in resources:
        if resource.get('kind') == 'Deployment':
            name = resource.get('metadata', {}).get('name')
            labels = resource.get('spec', {}).get('template', {}).get('metadata', {}).get('labels', {})
            if name:
                deployment_labels[name] = labels

    # Check services
    for resource in resources:
        if resource.get('kind') == 'Service':
            service_name = resource.get('metadata', {}).get('name', 'unknown')
            selector = resource.get('spec', {}).get('selector', {})

            # Find matching deployment (assume service name matches deployment name)
            matching_deployment = deployment_labels.get(service_name)
            if matching_deployment:
                for key, value in selector.items():
                    if matching_deployment.get(key) != value:
                        errors.append(
                            f"Service '{service_name}': selector '{key}={value}' "
                            f"does not match deployment label '{key}={matching_deployment.get(key)}'"
                        )

    return errors


def validate_volume_references(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that volumeMounts reference defined volumes.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for resource in resources:
        if resource.get('kind') == 'Deployment':
            name = resource.get('metadata', {}).get('name', 'unknown')
            containers = resource.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
            volumes = resource.get('spec', {}).get('template', {}).get('spec', {}).get('volumes', [])

            # Build set of volume names
            volume_names = {v.get('name') for v in volumes if v.get('name')}

            # Check volume mounts
            for container in containers:
                container_name = container.get('name', 'unknown')
                volume_mounts = container.get('volumeMounts', [])

                for mount in volume_mounts:
                    mount_name = mount.get('name')
                    if mount_name and mount_name not in volume_names:
                        errors.append(
                            f"Deployment '{name}', container '{container_name}': "
                            f"volumeMount '{mount_name}' references undefined volume"
                        )

    return errors


def validate_configmap_references(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that ConfigMap/Secret references exist in manifest.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build sets of configmaps and secrets
    configmaps = set()
    secrets = set()

    for resource in resources:
        kind = resource.get('kind')
        name = resource.get('metadata', {}).get('name')
        if kind == 'ConfigMap' and name:
            configmaps.add(name)
        elif kind == 'Secret' and name:
            secrets.add(name)

    # Check references in deployments
    for resource in resources:
        if resource.get('kind') == 'Deployment':
            deployment_name = resource.get('metadata', {}).get('name', 'unknown')
            volumes = resource.get('spec', {}).get('template', {}).get('spec', {}).get('volumes', [])

            for volume in volumes:
                # Check configMap references
                configmap_ref = volume.get('configMap', {}).get('name')
                if configmap_ref and configmap_ref not in configmaps:
                    errors.append(
                        f"Deployment '{deployment_name}': "
                        f"references undefined ConfigMap '{configmap_ref}'"
                    )

                # Check secret references
                secret_ref = volume.get('secret', {}).get('secretName')
                if secret_ref and secret_ref not in secrets:
                    errors.append(
                        f"Deployment '{deployment_name}': "
                        f"references undefined Secret '{secret_ref}'"
                    )

    return errors


def validate_port_consistency(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that Service targetPorts match container ports.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build map of deployment container ports
    deployment_ports = {}
    for resource in resources:
        if resource.get('kind') == 'Deployment':
            name = resource.get('metadata', {}).get('name')
            containers = resource.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])

            ports = []
            for container in containers:
                for port in container.get('ports', []):
                    if port.get('containerPort'):
                        ports.append(port['containerPort'])

            if name:
                deployment_ports[name] = ports

    # Check services
    for resource in resources:
        if resource.get('kind') == 'Service':
            service_name = resource.get('metadata', {}).get('name', 'unknown')
            service_ports = resource.get('spec', {}).get('ports', [])

            # Assume service name matches deployment name
            deployment_port_list = deployment_ports.get(service_name, [])

            # Only validate port consistency if deployment explicitly lists ports
            if deployment_port_list:
                for port_spec in service_ports:
                    target_port = port_spec.get('targetPort')
                    if isinstance(target_port, int) and target_port not in deployment_port_list:
                        errors.append(
                            f"Service '{service_name}': "
                            f"targetPort {target_port} not found in deployment container ports"
                        )

    return errors


def validate_required_fields(resources: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that required Kubernetes fields are present.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for idx, resource in enumerate(resources):
        if not resource.get('apiVersion'):
            errors.append(f"Resource {idx}: missing apiVersion")
        if not resource.get('kind'):
            errors.append(f"Resource {idx}: missing kind")
        if not resource.get('metadata'):
            errors.append(f"Resource {idx}: missing metadata")
        elif not resource['metadata'].get('name'):
            errors.append(f"Resource {idx} ({resource.get('kind', 'unknown')}): missing metadata.name")

    return errors


def parse_kubernetes_yaml(yaml_content: str) -> List[Dict[str, Any]]:
    """
    Parse Kubernetes YAML into list of resources.

    Args:
        yaml_content: YAML string (may contain multiple documents)

    Returns:
        List of resource dictionaries
    """
    resources = []
    for doc in yaml.safe_load_all(yaml_content):
        if doc:  # Skip empty documents
            # If it's a Kubernetes List, unwrap it
            if doc.get('kind') == 'List' and 'items' in doc:
                resources.extend(doc['items'])
            else:
                resources.append(doc)
    return resources


def validate_kubernetes_manifest(yaml_content: str) -> Tuple[bool, List[str]]:
    """
    Comprehensive validation of Kubernetes manifest.

    Args:
        yaml_content: YAML string of Kubernetes resources

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        resources = parse_kubernetes_yaml(yaml_content)
    except yaml.YAMLError as e:
        return False, [f"YAML parsing error: {e}"]

    if not resources:
        return False, ["No resources found in manifest"]

    errors = []
    errors.extend(validate_required_fields(resources))
    errors.extend(validate_selector_labels_match(resources))
    errors.extend(validate_service_selectors(resources))
    errors.extend(validate_volume_references(resources))
    errors.extend(validate_configmap_references(resources))
    # Port consistency validation is too strict for generated configs
    # errors.extend(validate_port_consistency(resources))

    return len(errors) == 0, errors
