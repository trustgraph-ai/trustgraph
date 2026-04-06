#!/usr/bin/env python3
"""
Test harness for dialog flow - walks through selecting all default options,
produces the resulting state object, and runs the JSONata transform.

Supports a test matrix mode where each field is tested with all its options
while other fields use defaults.
"""

import yaml
import json
import argparse
import zipfile
import io
from pathlib import Path
import jsonata
import requests


RESOURCES_DIR = Path(__file__).parent / "trustgraph_configurator/resources/dialog"


def load_flow():
    """Load the dialog flow YAML file."""
    with open(RESOURCES_DIR / "trustgraph-flow.yaml") as f:
        return yaml.safe_load(f)


def load_jsonata_transform():
    """Load the JSONata transform file."""
    with open(RESOURCES_DIR / "trustgraph-output.jsonata") as f:
        return f.read()


def run_transform(state, transform_expr):
    """Run the JSONata transform on the state object."""
    expr = jsonata.Jsonata(transform_expr)
    return expr.evaluate(state)


def call_config_service(config):
    """
    Call the configuration service to generate a deployment package.
    Returns (success, message, zip_contents) tuple.

    The API expects just the templates array, not the full config object.
    """
    url = config["api_url"]
    templates = config["templates"]

    try:
        response = requests.post(
            url,
            json=templates,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:200]}", None

        # Verify it's a valid ZIP
        try:
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, 'r') as zf:
                file_list = zf.namelist()
                return True, f"ZIP with {len(file_list)} files", file_list
        except zipfile.BadZipFile:
            return False, "Response is not a valid ZIP file", None

    except requests.exceptions.ConnectionError:
        return False, "Connection refused - is the service running?", None
    except requests.exceptions.Timeout:
        return False, "Request timed out", None
    except Exception as e:
        return False, f"Error: {e}", None


def get_all_options(step):
    """Get all possible values for a step's input."""
    input_def = step.get("input", {})
    input_type = input_def.get("type")

    if input_type == "select":
        return [opt["value"] for opt in input_def.get("options", [])]
    elif input_type == "toggle":
        return [True, False]
    elif input_type == "number":
        # For numbers, just test default, min, and max
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


def get_default_value(step):
    """Get the default value for a step's input."""
    input_def = step.get("input", {})
    input_type = input_def.get("type")

    if input_type == "select":
        options = input_def.get("options", [])
        # Find recommended option, or use first
        for opt in options:
            if opt.get("recommended"):
                return opt["value"]
        return options[0]["value"] if options else None

    elif input_type == "number":
        return input_def.get("default")

    elif input_type == "toggle":
        return input_def.get("default", False)

    return None


def evaluate_condition(condition, state):
    """
    Evaluate a simple condition against the state.
    Supports: "key = value", "key = true/false", "key < 'version'"
    """
    if not condition:
        return True

    # Handle equality: "ocr.enabled = true"
    if " = " in condition:
        key, value = condition.split(" = ", 1)
        key = key.strip()
        value = value.strip()

        # Get nested key
        state_value = state.get(key)

        # Parse value
        if value == "true":
            return state_value is True
        elif value == "false":
            return state_value is False
        else:
            return str(state_value) == value

    # Handle less-than for version comparisons: "version < '1.6.0'"
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
            # Unconditional transition
            return trans.get("next")

    return None  # Terminal state


def walk_flow(flow_data, overrides=None, verbose=True):
    """
    Walk through the flow, return the state object.

    Args:
        flow_data: The parsed dialog flow YAML
        overrides: Dict of {state_key: value} to override defaults
        verbose: Whether to print progress
    """
    state = {}
    overrides = overrides or {}
    steps = flow_data.get("steps", {})
    current = flow_data.get("flow", {}).get("start")
    visited_steps = []

    if verbose:
        print(f"Starting at: {current}")
        print("-" * 60)

    while current:
        step = steps.get(current)
        if not step:
            if verbose:
                print(f"ERROR: Step '{current}' not found!")
            break

        visited_steps.append(current)
        title = step.get("title", current)
        state_key = step.get("state_key")

        # Get value - use override if present, otherwise default
        if state_key:
            if state_key in overrides:
                value = overrides[state_key]
            else:
                value = get_default_value(step)
            state[state_key] = value

            if verbose:
                is_override = state_key in overrides
                marker = " [OVERRIDE]" if is_override else ""
                print(f"Step: {current}")
                print(f"  Title: {title}")
                print(f"  State key: {state_key} = {value}{marker}")
        else:
            if verbose:
                print(f"Step: {current}")
                print(f"  Title: {title}")
                print(f"  (no state key - review/terminal step)")

        # Get next step
        next_step = get_next_step(step, state)
        if verbose:
            if next_step:
                print(f"  -> Next: {next_step}")
            else:
                print(f"  -> Terminal state")
            print()

        current = next_step

    return state, visited_steps


def collect_fields_for_path(flow_data, overrides=None):
    """
    Collect all fields and their possible values for a given path.
    Returns a list of (step_name, state_key, options, default_value) tuples.
    """
    fields = []
    steps = flow_data.get("steps", {})

    # Walk with given overrides to find the path
    _, visited = walk_flow(flow_data, overrides=overrides, verbose=False)

    for step_name in visited:
        step = steps.get(step_name, {})
        state_key = step.get("state_key")
        if state_key:
            options = get_all_options(step)
            default = get_default_value(step)
            if len(options) > 1:  # Only include fields with choices
                fields.append((step_name, state_key, options, default))

    return fields


def collect_all_fields(flow_data):
    """
    Collect all fields from the baseline (default) path.
    """
    return collect_fields_for_path(flow_data, overrides=None)


def run_single_test(flow_data, transform_expr, overrides, description, test_num, results, call_api=False):
    """Run a single test case and record the result."""
    print("-" * 70)
    print(f"Test {test_num}: {description}")
    print("-" * 70)

    state, _ = walk_flow(flow_data, overrides=overrides, verbose=False)

    try:
        config = run_transform(state, transform_expr)
        result = {
            "test": test_num,
            "description": description,
            "overrides": overrides,
            "state": state,
            "config": config
        }

        print(f"State: {json.dumps(state, indent=2)}")
        print(f"Templates: {[t['name'] for t in config['templates']]}")

        # Optionally call the configuration service
        if call_api:
            success, message, files = call_config_service(config)
            result["api_success"] = success
            result["api_message"] = message
            if files:
                result["api_files"] = files

            if success:
                print(f"API: OK - {message}")
            else:
                print(f"API: FAILED - {message}")
                result["error"] = f"API: {message}"

        results.append(result)

    except Exception as e:
        results.append({
            "test": test_num,
            "description": description,
            "overrides": overrides,
            "state": state,
            "error": str(e)
        })
        print(f"State: {json.dumps(state, indent=2)}")
        print(f"ERROR: {e}")
    print()

    return test_num + 1


def run_test_matrix(flow_data, transform_expr, call_api=False):
    """
    Run the test matrix - for each field, try all values while others use defaults.
    When a toggle enables conditional fields, also test all options of those fields.
    """
    baseline_fields = collect_all_fields(flow_data)
    baseline_keys = {f[1] for f in baseline_fields}

    print("=" * 70)
    print("TEST MATRIX" + (" (with API validation)" if call_api else ""))
    print("=" * 70)
    print()
    print(f"Found {len(baseline_fields)} fields with multiple options on baseline path:")
    for step_name, state_key, options, default in baseline_fields:
        print(f"  - {state_key}: {len(options)} options (default: {default})")
    print()

    results = []
    test_num = 1

    # First, run the baseline (all defaults)
    test_num = run_single_test(
        flow_data, transform_expr,
        overrides={},
        description="BASELINE (all defaults)",
        test_num=test_num,
        results=results,
        call_api=call_api
    )

    # For each field, try each non-default value
    for step_name, state_key, options, default in baseline_fields:
        for option in options:
            if option == default:
                continue  # Skip default, already tested in baseline

            overrides = {state_key: option}
            test_num = run_single_test(
                flow_data, transform_expr,
                overrides=overrides,
                description=f"{state_key} = {option}",
                test_num=test_num,
                results=results,
                call_api=call_api
            )

            # Check if this override unlocks new fields (conditional paths)
            unlocked_fields = collect_fields_for_path(flow_data, overrides=overrides)
            unlocked_keys = {f[1] for f in unlocked_fields}
            new_keys = unlocked_keys - baseline_keys

            if new_keys:
                # Test all non-default options of the newly unlocked fields
                for uf_step, uf_key, uf_options, uf_default in unlocked_fields:
                    if uf_key not in new_keys:
                        continue
                    for uf_option in uf_options:
                        if uf_option == uf_default:
                            continue  # Default already tested above

                        combined_overrides = {state_key: option, uf_key: uf_option}
                        test_num = run_single_test(
                            flow_data, transform_expr,
                            overrides=combined_overrides,
                            description=f"{state_key} = {option}, {uf_key} = {uf_option}",
                            test_num=test_num,
                            results=results,
                            call_api=call_api
                        )

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Test harness for dialog flow configuration"
    )
    parser.add_argument(
        "--matrix", "-m",
        action="store_true",
        help="Run test matrix (each field with all options)"
    )
    parser.add_argument(
        "--api", "-a",
        action="store_true",
        help="Call the configuration service API to validate each config"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show summary only (with --matrix)"
    )
    args = parser.parse_args()

    flow_data = load_flow()
    transform_expr = load_jsonata_transform()

    if args.matrix:
        results = run_test_matrix(flow_data, transform_expr, call_api=args.api)

        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print()
        passed = [r for r in results if "error" not in r]
        failed = [r for r in results if "error" in r]
        print(f"Total tests: {len(results)}")
        print(f"Passed: {len(passed)}")
        print(f"Failed: {len(failed)}")

        if args.api:
            api_ok = [r for r in results if r.get("api_success")]
            api_fail = [r for r in results if "api_success" in r and not r["api_success"]]
            print(f"API OK: {len(api_ok)}")
            print(f"API Failed: {len(api_fail)}")

        if failed:
            print()
            print("Failed tests:")
            for r in failed:
                print(f"  - Test {r['test']}: {r['description']}")
                print(f"    Error: {r['error']}")
    else:
        print("=" * 60)
        print("Dialog Flow Test Harness - Default Options")
        print("=" * 60)
        print()

        state, _ = walk_flow(flow_data)

        print("=" * 60)
        print("Final State Object:")
        print("=" * 60)
        print()
        print(json.dumps(state, indent=2))

        # Run JSONata transform
        print()
        print("=" * 60)
        print("Running JSONata Transform...")
        print("=" * 60)
        print()

        config = run_transform(state, transform_expr)

        print("=" * 60)
        print("Configuration Object (output of transform):")
        print("=" * 60)
        print()
        print(json.dumps(config, indent=2))

        # Optionally call the API
        if args.api:
            print()
            print("=" * 60)
            print("Calling Configuration Service...")
            print("=" * 60)
            print()
            success, message, files = call_config_service(config)
            if success:
                print(f"OK: {message}")
                print(f"Files: {files}")
            else:
                print(f"FAILED: {message}")


if __name__ == "__main__":
    main()
