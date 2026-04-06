#!/usr/bin/env python3
"""
Test harness for documentation assembly - verifies that for each configuration
state, the documentation can be assembled from the manifest and markdown fragments.
"""

import yaml
import json
import argparse
import re
from pathlib import Path
import jsonata

RESOURCES_DIR = Path(__file__).parent / "trustgraph_configurator/resources/dialog"


def load_flow():
    """Load the dialog flow YAML file."""
    with open(RESOURCES_DIR / "trustgraph-flow.yaml") as f:
        return yaml.safe_load(f)


def load_docs_manifest():
    """Load the documentation manifest YAML file."""
    with open(RESOURCES_DIR / "trustgraph-docs.yaml") as f:
        return yaml.safe_load(f)


def load_doc_file(filename):
    """Load a documentation markdown file."""
    path = RESOURCES_DIR / "docs" / filename
    if path.exists():
        return path.read_text()
    return None


def get_default_value(step):
    """Get the default value for a step's input."""
    input_def = step.get("input", {})
    input_type = input_def.get("type")

    if input_type == "select":
        options = input_def.get("options", [])
        for opt in options:
            if opt.get("recommended"):
                return opt["value"]
        return options[0]["value"] if options else None
    elif input_type == "number":
        return input_def.get("default")
    elif input_type == "toggle":
        return input_def.get("default", False)
    return None


def get_all_options(step):
    """Get all possible values for a step's input."""
    input_def = step.get("input", {})
    input_type = input_def.get("type")

    if input_type == "select":
        return [opt["value"] for opt in input_def.get("options", [])]
    elif input_type == "toggle":
        return [True, False]
    elif input_type == "number":
        default = input_def.get("default")
        min_val = input_def.get("min")
        max_val = input_def.get("max")
        values = []
        if min_val is not None:
            values.append(min_val)
        if default is not None and default not in values:
            values.append(default)
        if max_val is not None and max_val not in values:
            values.append(max_val)
        return values
    return []


def evaluate_condition(condition, state):
    """Evaluate a simple condition against the state."""
    if not condition:
        return True

    if " = " in condition:
        key, value = condition.split(" = ", 1)
        key = key.strip()
        value = value.strip()
        state_value = state.get(key)
        if value == "true":
            return state_value is True
        elif value == "false":
            return state_value is False
        else:
            return str(state_value) == value

    if " < " in condition:
        key, value = condition.split(" < ", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        state_value = state.get(key, "")
        return str(state_value) < value

    return False


def get_next_step(step, state):
    """Determine the next step based on transitions and current state."""
    transitions = step.get("transitions", [])
    for trans in transitions:
        when = trans.get("when")
        if when:
            if evaluate_condition(when, state):
                return trans.get("next")
        else:
            return trans.get("next")
    return None


def walk_flow(flow_data, overrides=None):
    """Walk through the flow, return the state object."""
    state = {}
    overrides = overrides or {}
    steps = flow_data.get("steps", {})
    current = flow_data.get("flow", {}).get("start")
    visited_steps = []

    while current:
        step = steps.get(current)
        if not step:
            break

        visited_steps.append(current)
        state_key = step.get("state_key")

        if state_key:
            if state_key in overrides:
                value = overrides[state_key]
            else:
                value = get_default_value(step)
            state[state_key] = value

        current = get_next_step(step, state)

    return state, visited_steps


def evaluate_when_condition(when_expr, state):
    """
    Evaluate a 'when' condition from the docs manifest against the state.
    Supports: equality, 'in' arrays, 'and' conditions.
    """
    if not when_expr:
        return False

    # Use jsonata for complex expressions
    try:
        expr = jsonata.Jsonata(when_expr)
        result = expr.evaluate(state)
        return bool(result)
    except Exception as e:
        # Fallback to simple parsing for basic cases
        return evaluate_simple_when(when_expr, state)


def evaluate_simple_when(when_expr, state):
    """Simple fallback parser for when expressions."""
    # Handle "and" conditions
    if " and " in when_expr:
        parts = when_expr.split(" and ")
        return all(evaluate_simple_when(p.strip(), state) for p in parts)

    # Handle "in" conditions: "platform in ['docker-compose', 'podman-compose']"
    in_match = re.match(r"(\w+)\s+in\s+\[([^\]]+)\]", when_expr)
    if in_match:
        key = in_match.group(1)
        values_str = in_match.group(2)
        values = [v.strip().strip("'\"") for v in values_str.split(",")]
        return state.get(key) in values

    # Handle equality: "platform = 'docker-compose'"
    eq_match = re.match(r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]", when_expr)
    if eq_match:
        key = eq_match.group(1)
        value = eq_match.group(2)
        return state.get(key) == value

    return False


def assemble_docs(state, manifest):
    """
    Assemble documentation for a given state.
    Returns (success, matched_instructions, errors).
    """
    instructions = manifest.get("documentation", {}).get("instructions", [])
    matched = []
    errors = []

    for instr in instructions:
        # Check if instruction applies
        always = instr.get("always", False)
        when = instr.get("when")

        applies = always or (when and evaluate_when_condition(when, state))

        if applies:
            file_path = instr.get("file")
            content = load_doc_file(file_path)

            if content is None:
                errors.append(f"Missing file: {file_path}")
                matched.append({
                    "id": instr.get("id"),
                    "goal": instr.get("goal"),
                    "file": file_path,
                    "found": False
                })
            else:
                matched.append({
                    "id": instr.get("id"),
                    "goal": instr.get("goal"),
                    "file": file_path,
                    "found": True,
                    "content_length": len(content)
                })

    success = len(errors) == 0 and len(matched) > 0
    return success, matched, errors


def collect_fields_for_path(flow_data, overrides=None):
    """Collect all fields and their possible values for a given path."""
    fields = []
    steps = flow_data.get("steps", {})
    _, visited = walk_flow(flow_data, overrides=overrides)

    for step_name in visited:
        step = steps.get(step_name, {})
        state_key = step.get("state_key")
        if state_key:
            options = get_all_options(step)
            default = get_default_value(step)
            if len(options) > 1:
                fields.append((step_name, state_key, options, default))

    return fields


def run_single_test(flow_data, manifest, overrides, description, test_num, results):
    """Run a single documentation assembly test."""
    print("-" * 70)
    print(f"Test {test_num}: {description}")
    print("-" * 70)

    state, _ = walk_flow(flow_data, overrides=overrides)
    success, matched, errors = assemble_docs(state, manifest)

    result = {
        "test": test_num,
        "description": description,
        "overrides": overrides,
        "state": state,
        "matched_count": len(matched),
        "matched": matched,
        "success": success
    }

    if errors:
        result["errors"] = errors

    results.append(result)

    print(f"State: {json.dumps({k: v for k, v in state.items() if not k.startswith('ocr') and not k.startswith('embed')}, indent=2)}")
    print(f"Matched instructions: {len(matched)}")
    for m in matched:
        status = "OK" if m["found"] else "MISSING"
        print(f"  - [{status}] {m['goal']} ({m['file']})")

    if errors:
        print(f"ERRORS: {errors}")
    else:
        print("Docs: OK")
    print()

    return test_num + 1


def run_test_matrix(flow_data, manifest):
    """Run the documentation test matrix."""
    baseline_fields = collect_fields_for_path(flow_data)
    baseline_keys = {f[1] for f in baseline_fields}

    print("=" * 70)
    print("DOCUMENTATION TEST MATRIX")
    print("=" * 70)
    print()
    print(f"Found {len(baseline_fields)} fields with multiple options on baseline path:")
    for step_name, state_key, options, default in baseline_fields:
        print(f"  - {state_key}: {len(options)} options (default: {default})")
    print()

    results = []
    test_num = 1

    # Baseline test
    test_num = run_single_test(
        flow_data, manifest,
        overrides={},
        description="BASELINE (all defaults)",
        test_num=test_num,
        results=results
    )

    # Test each field variation
    for step_name, state_key, options, default in baseline_fields:
        for option in options:
            if option == default:
                continue

            overrides = {state_key: option}
            test_num = run_single_test(
                flow_data, manifest,
                overrides=overrides,
                description=f"{state_key} = {option}",
                test_num=test_num,
                results=results
            )

            # Check for unlocked fields
            unlocked_fields = collect_fields_for_path(flow_data, overrides=overrides)
            unlocked_keys = {f[1] for f in unlocked_fields}
            new_keys = unlocked_keys - baseline_keys

            if new_keys:
                for uf_step, uf_key, uf_options, uf_default in unlocked_fields:
                    if uf_key not in new_keys:
                        continue
                    for uf_option in uf_options:
                        if uf_option == uf_default:
                            continue

                        combined_overrides = {state_key: option, uf_key: uf_option}
                        test_num = run_single_test(
                            flow_data, manifest,
                            overrides=combined_overrides,
                            description=f"{state_key} = {option}, {uf_key} = {uf_option}",
                            test_num=test_num,
                            results=results
                        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test harness for documentation assembly"
    )
    parser.add_argument(
        "--matrix", "-m",
        action="store_true",
        help="Run test matrix (each field with all options)"
    )
    args = parser.parse_args()

    flow_data = load_flow()
    manifest = load_docs_manifest()

    if args.matrix:
        results = run_test_matrix(flow_data, manifest)

        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print()
        passed = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        print(f"Total tests: {len(results)}")
        print(f"Passed: {len(passed)}")
        print(f"Failed: {len(failed)}")

        if failed:
            print()
            print("Failed tests:")
            for r in failed:
                print(f"  - Test {r['test']}: {r['description']}")
                if "errors" in r:
                    for err in r["errors"]:
                        print(f"    Error: {err}")
    else:
        # Single test with defaults
        print("=" * 60)
        print("Documentation Assembly Test - Default Options")
        print("=" * 60)
        print()

        state, _ = walk_flow(flow_data)
        success, matched, errors = assemble_docs(state, manifest)

        print(f"State: {json.dumps(state, indent=2)}")
        print()
        print(f"Matched {len(matched)} instructions:")
        for m in matched:
            status = "OK" if m["found"] else "MISSING"
            print(f"  [{status}] {m['goal']}")
            print(f"         File: {m['file']}")
        print()

        if errors:
            print(f"Errors: {errors}")
        else:
            print("All documentation files found!")


if __name__ == "__main__":
    main()
