"""
Verifies TrustGraph system health by running comprehensive checks.

This utility monitors system startup and health by checking:
1. Infrastructure (Pulsar, API Gateway)
2. Core services (processors, flows, prompts)
3. Data services (library)
4. UI (workbench)

Includes intelligent retry logic with configurable timeouts.
"""

import argparse
import os
import sys
import time
import requests
from typing import Tuple, Optional

# Import existing CLI functions to reuse logic
from trustgraph.api import Api

default_pulsar_url = "http://localhost:8080"
default_api_url = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
default_ui_url = "http://localhost:8888"
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)


class HealthChecker:
    """Manages health check execution with retry logic and timeouts."""

    def __init__(
        self,
        global_timeout: int = 120,
        check_timeout: int = 10,
        retry_delay: int = 3,
        verbose: bool = False
    ):
        self.global_timeout = global_timeout
        self.check_timeout = check_timeout
        self.retry_delay = retry_delay
        self.verbose = verbose
        self.start_time = time.time()
        self.checks_passed = 0
        self.checks_failed = 0

    def elapsed(self) -> str:
        """Return formatted elapsed time MM:SS."""
        elapsed_sec = int(time.time() - self.start_time)
        minutes = elapsed_sec // 60
        seconds = elapsed_sec % 60
        return f"{minutes:02d}:{seconds:02d}"

    def time_remaining(self) -> float:
        """Return seconds remaining in global timeout."""
        return self.global_timeout - (time.time() - self.start_time)

    def log(self, message: str, level: str = "info"):
        """Log a message with timestamp."""
        timestamp = self.elapsed()
        if level == "success":
            icon = "✓"
        elif level == "error":
            icon = "✗"
        elif level == "progress":
            icon = "⏳"
        else:
            icon = " "
        print(f"[{timestamp}] {icon} {message}", flush=True)

    def debug(self, message: str):
        """Log a debug message if verbose mode is enabled."""
        if self.verbose:
            timestamp = self.elapsed()
            print(f"[{timestamp}]   {message}", flush=True)

    def run_check(
        self,
        name: str,
        check_func,
        *args,
        **kwargs
    ) -> bool:
        """
        Run a check with retry logic until success or global timeout.

        Args:
            name: Human-readable name of the check
            check_func: Function that returns (success: bool, message: str)
            *args, **kwargs: Arguments to pass to check_func

        Returns:
            True if check passed, False otherwise
        """
        attempt = 0

        while self.time_remaining() > 0:
            attempt += 1

            if attempt > 1:
                self.log(f"Checking {name}... (attempt {attempt})", "progress")
            else:
                self.log(f"Checking {name}...", "progress")

            try:
                # Run the check with timeout
                success, message = check_func(*args, **kwargs)

                if success:
                    self.log(f"{name}: {message}", "success")
                    self.checks_passed += 1
                    return True
                else:
                    self.debug(f"{name} not ready: {message}")

            except Exception as e:
                self.debug(f"{name} check failed with exception: {e}")

            # Check if we have time for another attempt
            if self.time_remaining() < self.retry_delay:
                break

            # Wait before retry
            time.sleep(self.retry_delay)

        # Check failed
        self.log(f"{name}: Failed (timeout after {attempt} attempts)", "error")
        self.checks_failed += 1
        return False


def check_pulsar(url: str, timeout: int) -> Tuple[bool, str]:
    """Check if Pulsar admin API is responding."""
    try:
        resp = requests.get(f"{url}/admin/v2/clusters", timeout=timeout)
        if resp.status_code == 200:
            clusters = resp.json()
            return True, f"Pulsar healthy ({len(clusters)} cluster(s))"
        else:
            return False, f"Pulsar returned status {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Pulsar connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Pulsar"
    except Exception as e:
        return False, f"Pulsar error: {e}"


def check_api_gateway(url: str, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if API Gateway is responding."""
    try:
        # Try to hit the base URL
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if not url.endswith('/'):
            url += '/'

        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code in [200, 404]:  # 404 is OK, means gateway is up
            return True, "API Gateway is responding"
        else:
            return False, f"API Gateway returned status {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "API Gateway connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to API Gateway"
    except Exception as e:
        return False, f"API Gateway error: {e}"


def check_processors(url: str, min_processors: int, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if processors are running via show-processor-state."""
    try:
        api = Api(url, token=token)

        # Use the metrics endpoint similar to show_processor_state
        # This is a simplified check - we'll use requests to check the metrics
        metrics_url = url.replace('http://', '').replace('https://', '').split('/')[0]
        metrics_url = f"http://{metrics_url}:8088/api/metrics/query?query=processor_info"

        resp = requests.get(metrics_url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            processor_count = len(data.get("data", {}).get("result", []))

            if processor_count >= min_processors:
                return True, f"Found {processor_count} processors (≥ {min_processors})"
            else:
                return False, f"Only {processor_count} processors running (need {min_processors})"
        else:
            return False, f"Metrics returned status {resp.status_code}"

    except Exception as e:
        return False, f"Processor check error: {e}"


def check_flow_classes(url: str, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if flow classes are loaded."""
    try:
        api = Api(url, token=token)
        flow_api = api.flow()

        classes = flow_api.list_classes()

        if classes and len(classes) > 0:
            return True, f"Found {len(classes)} flow class(es)"
        else:
            return False, "No flow classes found"

    except Exception as e:
        return False, f"Flow classes check error: {e}"


def check_flows(url: str, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if flow manager is responding."""
    try:
        api = Api(url, token=token)
        flow_api = api.flow()

        flows = flow_api.list()

        # Success if we get a response (even if empty)
        return True, f"Flow manager responding ({len(flows)} flow(s))"

    except Exception as e:
        return False, f"Flow manager check error: {e}"


def check_prompts(url: str, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if prompts are loaded."""
    try:
        api = Api(url, token=token)

        prompts = api.prompts().list()

        if prompts and len(prompts) > 0:
            return True, f"Found {len(prompts)} prompt(s)"
        else:
            return False, "No prompts found"

    except Exception as e:
        return False, f"Prompts check error: {e}"


def check_library(url: str, timeout: int, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if library service is responding."""
    try:
        api = Api(url, token=token)
        library_api = api.library()

        # Try to get documents (with default user)
        docs = library_api.get_documents(user="trustgraph")

        # Success if we get a valid response (even if empty)
        return True, f"Library responding ({len(docs)} document(s))"

    except Exception as e:
        return False, f"Library check error: {e}"


def check_ui(url: str, timeout: int) -> Tuple[bool, str]:
    """Check if Workbench UI is responding."""
    try:
        if not url.endswith('/'):
            url += '/'

        resp = requests.get(f"{url}index.html", timeout=timeout)
        if resp.status_code == 200:
            return True, "Workbench UI is responding"
        else:
            return False, f"UI returned status {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "UI connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to UI"
    except Exception as e:
        return False, f"UI error: {e}"


def main():
    """Main entry point for the CLI."""

    parser = argparse.ArgumentParser(
        prog='tg-verify-system-status',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--global-timeout',
        type=int,
        default=120,
        help='Total timeout in seconds (default: 120)'
    )

    parser.add_argument(
        '--check-timeout',
        type=int,
        default=10,
        help='Per-check timeout in seconds (default: 10)'
    )

    parser.add_argument(
        '--retry-delay',
        type=int,
        default=3,
        help='Delay between retries in seconds (default: 3)'
    )

    parser.add_argument(
        '--min-processors',
        type=int,
        default=15,
        help='Minimum processors required (default: 15)'
    )

    parser.add_argument(
        '--pulsar-url',
        default=default_pulsar_url,
        help=f'Pulsar admin URL (default: {default_pulsar_url})'
    )

    parser.add_argument(
        '--api-url',
        default=default_api_url,
        help=f'API Gateway URL (default: {default_api_url})'
    )

    parser.add_argument(
        '--ui-url',
        default=default_ui_url,
        help=f'Workbench UI URL (default: {default_ui_url})'
    )

    parser.add_argument(
        '--skip-ui',
        action='store_true',
        help='Skip UI check (for headless deployments)'
    )

    parser.add_argument(
        '-t', '--token',
        default=default_token,
        help='Authentication token (default: $TRUSTGRAPH_TOKEN)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    # Create health checker
    checker = HealthChecker(
        global_timeout=args.global_timeout,
        check_timeout=args.check_timeout,
        retry_delay=args.retry_delay,
        verbose=args.verbose
    )

    print("=" * 60)
    print("TrustGraph System Status Verification")
    print("=" * 60)
    print(f"Global timeout: {args.global_timeout}s")
    print(f"Check timeout: {args.check_timeout}s")
    print(f"Retry delay: {args.retry_delay}s")
    print("=" * 60)
    print()

    # Phase 1: Infrastructure
    print("Phase 1: Infrastructure")
    print("-" * 60)

    if not checker.run_check(
        "Pulsar",
        check_pulsar,
        args.pulsar_url,
        args.check_timeout
    ):
        print("\n⚠️  Pulsar is not responding - other checks may fail")
        print()

    checker.run_check(
        "API Gateway",
        check_api_gateway,
        args.api_url,
        args.check_timeout,
        args.token
    )

    print()

    # Phase 2: Core Services
    print("Phase 2: Core Services")
    print("-" * 60)

    checker.run_check(
        "Processors",
        check_processors,
        args.api_url,
        args.min_processors,
        args.check_timeout,
        args.token
    )

    checker.run_check(
        "Flow Classes",
        check_flow_classes,
        args.api_url,
        args.check_timeout,
        args.token
    )

    checker.run_check(
        "Flows",
        check_flows,
        args.api_url,
        args.check_timeout,
        args.token
    )

    checker.run_check(
        "Prompts",
        check_prompts,
        args.api_url,
        args.check_timeout,
        args.token
    )

    print()

    # Phase 3: Data Services
    print("Phase 3: Data Services")
    print("-" * 60)

    checker.run_check(
        "Library",
        check_library,
        args.api_url,
        args.check_timeout,
        args.token
    )

    print()

    # Phase 4: UI (optional)
    if not args.skip_ui:
        print("Phase 4: User Interface")
        print("-" * 60)

        checker.run_check(
            "Workbench UI",
            check_ui,
            args.ui_url,
            args.check_timeout
        )

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    total_checks = checker.checks_passed + checker.checks_failed

    print(f"Checks passed: {checker.checks_passed}/{total_checks}")
    print(f"Checks failed: {checker.checks_failed}/{total_checks}")
    print(f"Total time: {checker.elapsed()}")

    if checker.checks_failed == 0:
        print("\n✓ System is healthy!")
        sys.exit(0)
    else:
        print(f"\n✗ System has {checker.checks_failed} failing check(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
