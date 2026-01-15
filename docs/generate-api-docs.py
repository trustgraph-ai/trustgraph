#!/usr/bin/env python3
"""
Generate clean markdown documentation for trustgraph.api

This script introspects the trustgraph.api package and generates markdown
documentation showing the API as users actually import it.
"""

import sys
import inspect
import importlib
from dataclasses import is_dataclass, fields
from typing import get_type_hints

# Add parent directory to path
sys.path.insert(0, '../trustgraph-base')

def parse_docstring(docstring):
    """Parse Google-style docstring into sections"""
    if not docstring:
        return {"description": "", "args": [], "returns": "", "raises": [], "examples": []}

    lines = docstring.split('\n')
    result = {
        "description": [],
        "args": [],
        "returns": "",
        "raises": [],
        "examples": [],
        "attributes": []
    }

    current_section = "description"
    current_item = None

    for line in lines:
        stripped = line.strip()

        # Check for section headers
        if stripped in ["Args:", "Arguments:"]:
            current_section = "args"
            current_item = None
            continue
        elif stripped in ["Returns:", "Return:"]:
            current_section = "returns"
            current_item = None
            continue
        elif stripped in ["Raises:"]:
            current_section = "raises"
            current_item = None
            continue
        elif stripped in ["Example:", "Examples:"]:
            current_section = "examples"
            current_item = None
            continue
        elif stripped in ["Attributes:"]:
            current_section = "attributes"
            current_item = None
            continue
        elif stripped.startswith("Note:"):
            current_section = "description"
            result["description"].append(line)
            continue

        # Process content based on section
        if current_section == "description":
            result["description"].append(line)
        elif current_section == "args":
            # Check if this is a new argument (starts with word followed by colon)
            if stripped and not line.startswith(' ' * 8) and ':' in stripped:
                parts = stripped.split(':', 1)
                arg_name = parts[0].strip()
                arg_desc = parts[1].strip() if len(parts) > 1 else ""
                current_item = {"name": arg_name, "description": arg_desc}
                result["args"].append(current_item)
            elif current_item and stripped:
                # Continuation of previous arg description
                current_item["description"] += " " + stripped
        elif current_section == "returns":
            if stripped:
                result["returns"] += stripped + " "
        elif current_section == "raises":
            if stripped and ':' in stripped:
                parts = stripped.split(':', 1)
                exc_name = parts[0].strip()
                exc_desc = parts[1].strip() if len(parts) > 1 else ""
                current_item = {"name": exc_name, "description": exc_desc}
                result["raises"].append(current_item)
            elif current_item and stripped:
                current_item["description"] += " " + stripped
        elif current_section == "examples":
            result["examples"].append(line)
        elif current_section == "attributes":
            if stripped and '-' in stripped:
                parts = stripped.split('-', 1)
                if len(parts) == 2:
                    attr_name = parts[0].strip().strip('`')
                    attr_desc = parts[1].strip()
                    result["attributes"].append({"name": attr_name, "description": attr_desc})

    # Clean up description
    result["description"] = '\n'.join(result["description"]).strip()
    result["returns"] = result["returns"].strip()

    return result

def format_signature(name, obj):
    """Format function/method signature"""
    try:
        sig = inspect.signature(obj)
        return f"{name}{sig}"
    except:
        return f"{name}(...)"

def document_function(name, func, indent=0):
    """Generate markdown for a function"""
    ind = "  " * indent
    md = []

    # Function heading and signature
    md.append(f"{ind}### `{format_signature(name, func)}`\n")

    # Parse docstring
    doc = inspect.getdoc(func)
    if doc:
        parsed = parse_docstring(doc)

        # Description
        if parsed["description"]:
            md.append(f"{ind}{parsed['description']}\n")

        # Arguments
        if parsed["args"]:
            md.append(f"{ind}**Arguments:**\n")
            for arg in parsed["args"]:
                md.append(f"{ind}- `{arg['name']}`: {arg['description']}")
            md.append("")

        # Returns
        if parsed["returns"]:
            md.append(f"{ind}**Returns:** {parsed['returns']}\n")

        # Raises
        if parsed["raises"]:
            md.append(f"{ind}**Raises:**\n")
            for exc in parsed["raises"]:
                md.append(f"{ind}- `{exc['name']}`: {exc['description']}")
            md.append("")

        # Examples
        if parsed["examples"]:
            md.append(f"{ind}**Example:**\n")

            # Strip common leading whitespace from examples
            import textwrap
            example_text = '\n'.join(parsed["examples"])
            dedented = textwrap.dedent(example_text)
            example_lines = dedented.split('\n')

            # Check if examples already contain code fences
            if '```' in dedented:
                # Already has code fences, don't wrap
                for line in example_lines:
                    md.append(line.rstrip())
                md.append("")
            else:
                # No code fences, wrap in python block
                md.append("```python")
                for line in example_lines:
                    md.append(line.rstrip())
                md.append("```\n")

    return '\n'.join(md)

def document_class(name, cls):
    """Generate markdown for a class"""
    md = []

    # Class heading
    md.append(f"## `{name}`\n")

    # Import statement
    md.append(f"```python")
    md.append(f"from trustgraph.api import {name}")
    md.append(f"```\n")

    # Parse class docstring
    doc = inspect.getdoc(cls)
    if doc:
        parsed = parse_docstring(doc)

        # Description
        if parsed["description"]:
            md.append(f"{parsed['description']}\n")

        # Attributes (for class-level attributes)
        if parsed["attributes"]:
            md.append(f"**Attributes:**\n")
            for attr in parsed["attributes"]:
                md.append(f"- `{attr['name']}`: {attr['description']}")
            md.append("")

    # For dataclasses, show fields
    if is_dataclass(cls):
        md.append("**Fields:**\n")
        for field in fields(cls):
            field_doc = ""
            if cls.__doc__:
                # Try to extract field description from docstring
                pass
            md.append(f"- `{field.name}`: {field.type}")
        md.append("")

    # Document methods
    methods = []
    for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        # Skip private methods except special ones
        if method_name.startswith('_') and method_name not in ['__init__', '__enter__', '__exit__', '__aenter__', '__aexit__']:
            continue
        methods.append((method_name, method))

    if methods:
        md.append("### Methods\n")
        for method_name, method in methods:
            md.append(document_function(method_name, method, indent=0))

    return '\n'.join(md)

def document_exception(name, exc):
    """Generate markdown for an exception"""
    md = []

    md.append(f"## `{name}`\n")

    # Import statement
    md.append(f"```python")
    md.append(f"from trustgraph.api import {name}")
    md.append(f"```\n")

    doc = inspect.getdoc(exc)
    if doc:
        md.append(f"{doc}\n")
    else:
        md.append(f"Exception class for {name.replace('Exception', '').replace('Error', '')} errors.\n")

    return '\n'.join(md)

def generate_toc(items):
    """Generate table of contents"""
    md = []
    md.append("# TrustGraph Python API Reference\n")

    # Add introduction
    md.append("## Installation\n")
    md.append("```bash")
    md.append("pip install trustgraph")
    md.append("```\n")

    md.append("## Quick Start\n")
    md.append("All classes and types are imported from the `trustgraph.api` package:\n")
    md.append("```python")
    md.append("from trustgraph.api import Api, Triple, ConfigKey")
    md.append("")
    md.append("# Create API client")
    md.append("api = Api(url=\"http://localhost:8088/\")")
    md.append("")
    md.append("# Get a flow instance")
    md.append("flow = api.flow().id(\"default\")")
    md.append("")
    md.append("# Execute a graph RAG query")
    md.append("response = flow.graph_rag(")
    md.append("    query=\"What are the main topics?\",")
    md.append("    user=\"trustgraph\",")
    md.append("    collection=\"default\"")
    md.append(")")
    md.append("```\n")

    md.append("## Table of Contents\n")

    # Group by category
    categories = {
        "Core": ["Api"],
        "Flow Clients": ["Flow", "FlowInstance", "AsyncFlow", "AsyncFlowInstance"],
        "WebSocket Clients": ["SocketClient", "SocketFlowInstance", "AsyncSocketClient", "AsyncSocketFlowInstance"],
        "Bulk Operations": ["BulkClient", "AsyncBulkClient"],
        "Metrics": ["Metrics", "AsyncMetrics"],
        "Data Types": ["Triple", "ConfigKey", "ConfigValue", "DocumentMetadata", "ProcessingMetadata",
                      "CollectionMetadata", "StreamingChunk", "AgentThought", "AgentObservation",
                      "AgentAnswer", "RAGChunk"],
        "Exceptions": []
    }

    # Find exceptions
    for item in items:
        if "Exception" in item or "Error" in item:
            categories["Exceptions"].append(item)

    for category, names in categories.items():
        if not names:
            continue
        md.append(f"### {category}\n")
        for name in names:
            if name in items:
                md.append(f"- [{name}](#{name.lower()})")
        md.append("")

    return '\n'.join(md)

def main():
    """Generate API documentation"""

    # Import the package
    try:
        api_module = importlib.import_module('trustgraph.api')
    except ImportError as e:
        print(f"Error importing trustgraph.api: {e}", file=sys.stderr)
        sys.exit(1)

    # Get exported names
    if not hasattr(api_module, '__all__'):
        print("Error: trustgraph.api has no __all__", file=sys.stderr)
        sys.exit(1)

    all_names = api_module.__all__

    # Generate TOC
    print(generate_toc(all_names))
    print("---\n")

    # Document each exported item
    for name in all_names:
        try:
            obj = getattr(api_module, name)

            # Determine what kind of object it is
            if inspect.isclass(obj):
                if issubclass(obj, Exception):
                    print(document_exception(name, obj))
                else:
                    print(document_class(name, obj))
            elif inspect.isfunction(obj):
                print(document_function(name, obj))

            print("\n---\n")

        except Exception as e:
            print(f"Error documenting {name}: {e}", file=sys.stderr)
            continue

if __name__ == "__main__":
    main()
