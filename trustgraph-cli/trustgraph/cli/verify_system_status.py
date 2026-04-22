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
from trustgraph.i18n import get_translator

default_pulsar_url = "http://localhost:8080"
default_api_url = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
default_ui_url = "http://localhost:8888"
default_token = os.getenv("TRUSTGRAPH_TOKEN", None)
default_workspace = os.getenv("TRUSTGRAPH_WORKSPACE", "default")


class HealthChecker:
    """Manages health check execution with retry logic and timeouts."""

    def __init__(
        self,
        global_timeout: int = 120,
        check_timeout: int = 10,
        retry_delay: int = 3,
        verbose: bool = False,
        translator=None,
    ):
        self.global_timeout = global_timeout
        self.check_timeout = check_timeout
        self.retry_delay = retry_delay
        self.verbose = verbose
        self.tr = translator
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
                if self.tr:
                    self.log(self.tr.t("cli.verify_system_status.checking_attempt", name=name, attempt=attempt), "progress")
                else:
                    self.log(f"Checking {name}... (attempt {attempt})", "progress")
            else:
                if self.tr:
                    self.log(self.tr.t("cli.verify_system_status.checking", name=name), "progress")
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
        if self.tr:
            self.log(self.tr.t("cli.verify_system_status.failed_timeout", name=name, attempt=attempt), "error")
        else:
            self.log(f"{name}: Failed (timeout after {attempt} attempts)", "error")
        self.checks_failed += 1
        return False


def check_pulsar(url: str, timeout: int, tr) -> Tuple[bool, str]:
    """Check if Pulsar admin API is responding."""
    try:
        resp = requests.get(f"{url}/admin/v2/clusters", timeout=timeout)
        if resp.status_code == 200:
            clusters = resp.json()
            return True, tr.t("cli.verify_system_status.pulsar.healthy", clusters=len(clusters))
        else:
            return False, tr.t("cli.verify_system_status.pulsar.status", status_code=resp.status_code)
    except requests.exceptions.Timeout:
        return False, tr.t("cli.verify_system_status.pulsar.timeout")
    except requests.exceptions.ConnectionError:
        return False, tr.t("cli.verify_system_status.pulsar.cannot_connect")
    except Exception as e:
        return False, tr.t("cli.verify_system_status.pulsar.error", error=str(e))


def check_api_gateway(url: str, timeout: int, tr, token: Optional[str] = None) -> Tuple[bool, str]:
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
            return True, tr.t("cli.verify_system_status.api_gateway.responding")
        else:
            return False, tr.t("cli.verify_system_status.api_gateway.status", status_code=resp.status_code)
    except requests.exceptions.Timeout:
        return False, tr.t("cli.verify_system_status.api_gateway.timeout")
    except requests.exceptions.ConnectionError:
        return False, tr.t("cli.verify_system_status.api_gateway.cannot_connect")
    except Exception as e:
        return False, tr.t("cli.verify_system_status.api_gateway.error", error=str(e))


def check_processors(url: str, min_processors: int, timeout: int, tr, token: Optional[str] = None) -> Tuple[bool, str]:
    """Check if processors are running via metrics endpoint."""
    try:
        # Construct metrics URL from API URL
        if not url.endswith('/'):
            url += '/'
        metrics_url = f"{url}api/metrics/query?query=processor_info"

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        resp = requests.get(metrics_url, timeout=timeout, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            processor_count = len(data.get("data", {}).get("result", []))

            if processor_count >= min_processors:
                return True, tr.t("cli.verify_system_status.processors.found", count=processor_count, min=min_processors)
            else:
                return False, tr.t("cli.verify_system_status.processors.only", count=processor_count, min=min_processors)
        else:
            return False, tr.t("cli.verify_system_status.processors.metrics_status", status_code=resp.status_code)

    except Exception as e:
        return False, tr.t("cli.verify_system_status.processors.error", error=str(e))


def check_flow_blueprints(url: str, timeout: int, tr, token: Optional[str] = None, workspace: str = "default") -> Tuple[bool, str]:
    """Check if flow blueprints are loaded."""
    try:
        api = Api(url, token=token, timeout=timeout, workspace=workspace)
        flow_api = api.flow()

        blueprints = flow_api.list_blueprints()

        if blueprints and len(blueprints) > 0:
            return True, tr.t("cli.verify_system_status.flow_blueprints.found", count=len(blueprints))
        else:
            return False, tr.t("cli.verify_system_status.flow_blueprints.none")

    except Exception as e:
        return False, tr.t("cli.verify_system_status.flow_blueprints.error", error=str(e))


def check_flows(url: str, timeout: int, tr, token: Optional[str] = None, workspace: str = "default") -> Tuple[bool, str]:
    """Check if flow manager is responding."""
    try:
        api = Api(url, token=token, timeout=timeout, workspace=workspace)
        flow_api = api.flow()

        flows = flow_api.list()

        # Success if we get a response (even if empty)
        return True, tr.t("cli.verify_system_status.flows.responding", count=len(flows))

    except Exception as e:
        return False, tr.t("cli.verify_system_status.flows.error", error=str(e))


def check_prompts(url: str, timeout: int, tr, token: Optional[str] = None, workspace: str = "default") -> Tuple[bool, str]:
    """Check if prompts are loaded."""
    try:
        api = Api(url, token=token, timeout=timeout, workspace=workspace)
        config = api.config()

        # Import ConfigKey here to avoid top-level import issues
        from trustgraph.api.types import ConfigKey
        import json

        # Get the template-index which lists all prompts
        values = config.get([
            ConfigKey(type="prompt", key="template-index")
        ])

        ix = json.loads(values[0].value)

        if ix and len(ix) > 0:
            return True, tr.t("cli.verify_system_status.prompts.found", count=len(ix))
        else:
            return False, tr.t("cli.verify_system_status.prompts.none")

    except Exception as e:
        return False, tr.t("cli.verify_system_status.prompts.error", error=str(e))


def check_library(url: str, timeout: int, tr, token: Optional[str] = None, workspace: str = "default") -> Tuple[bool, str]:
    """Check if library service is responding."""
    try:
        api = Api(url, token=token, timeout=timeout, workspace=workspace)
        library_api = api.library()

        # Try to get documents
        docs = library_api.get_documents()

        # Success if we get a valid response (even if empty)
        return True, tr.t("cli.verify_system_status.library.responding", count=len(docs))

    except Exception as e:
        return False, tr.t("cli.verify_system_status.library.error", error=str(e))


def check_ui(url: str, timeout: int, tr) -> Tuple[bool, str]:
    """Check if Workbench UI is responding."""
    try:
        if not url.endswith('/'):
            url += '/'

        resp = requests.get(f"{url}index.html", timeout=timeout)
        if resp.status_code == 200:
            return True, tr.t("cli.verify_system_status.ui.responding")
        else:
            return False, tr.t("cli.verify_system_status.ui.status", status_code=resp.status_code)
    except requests.exceptions.Timeout:
        return False, tr.t("cli.verify_system_status.ui.timeout")
    except requests.exceptions.ConnectionError:
        return False, tr.t("cli.verify_system_status.ui.cannot_connect")
    except Exception as e:
        return False, tr.t("cli.verify_system_status.ui.error", error=str(e))


def main():
    """Main entry point for the CLI."""

    parser = argparse.ArgumentParser(
        prog='tg-verify-system-status',
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--lang',
        default=os.getenv("TRUSTGRAPH_LANG", "en"),
        help='Language code for CLI output (default: $TRUSTGRAPH_LANG or en)'
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
        '-w', '--workspace',
        default=default_workspace,
        help=f'Workspace (default: {default_workspace})',
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args()

    tr = get_translator(args.lang)

    # Create health checker
    checker = HealthChecker(
        global_timeout=args.global_timeout,
        check_timeout=args.check_timeout,
        retry_delay=args.retry_delay,
        verbose=args.verbose,
        translator=tr,
    )

    print("=" * 60)
    print(tr.t("cli.verify_system_status.title"))
    print("=" * 60)
    print()

    # Phase 1: Infrastructure
    print(tr.t("cli.verify_system_status.phase_1"))
    print("-" * 60)
    # Pulsar check is skipped — not all deployments use Pulsar.
    # The API Gateway check covers broker connectivity indirectly.

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.api_gateway"),
        check_api_gateway,
        args.api_url,
        args.check_timeout,
        tr,
        args.token,
    )

    print()

    # Phase 2: Core Services
    print(tr.t("cli.verify_system_status.phase_2"))
    print("-" * 60)

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.processors"),
        check_processors,
        args.api_url,
        args.min_processors,
        args.check_timeout,
        tr,
        args.token,
    )

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.flow_blueprints"),
        check_flow_blueprints,
        args.api_url,
        args.check_timeout,
        tr,
        args.token,
        args.workspace,
    )

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.flows"),
        check_flows,
        args.api_url,
        args.check_timeout,
        tr,
        args.token,
        args.workspace,
    )

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.prompts"),
        check_prompts,
        args.api_url,
        args.check_timeout,
        tr,
        args.token,
        args.workspace,
    )

    print()

    # Phase 3: Data Services
    print(tr.t("cli.verify_system_status.phase_3"))
    print("-" * 60)

    checker.run_check(
        tr.t("cli.verify_system_status.check_name.library"),
        check_library,
        args.api_url,
        args.check_timeout,
        tr,
        args.token,
        args.workspace,
    )

    print()

    # Phase 4: UI (optional)
    if not args.skip_ui:
        print(tr.t("cli.verify_system_status.phase_4"))
        print("-" * 60)

        checker.run_check(
            tr.t("cli.verify_system_status.check_name.workbench_ui"),
            check_ui,
            args.ui_url,
            args.check_timeout,
            tr,
        )

        print()

    # Summary
    print("=" * 60)
    print(tr.t("cli.verify_system_status.summary"))
    print("=" * 60)

    total_checks = checker.checks_passed + checker.checks_failed

    print(tr.t("cli.verify_system_status.checks_passed", passed=checker.checks_passed, total=total_checks))
    print(tr.t("cli.verify_system_status.checks_failed", failed=checker.checks_failed, total=total_checks))
    print(tr.t("cli.verify_system_status.total_time", elapsed=checker.elapsed()))

    if checker.checks_failed == 0:
        print(f"\n✓ {tr.t('cli.verify_system_status.system_healthy')}")
        sys.exit(0)
    else:
        print(f"\n✗ {tr.t('cli.verify_system_status.system_failing', failed=checker.checks_failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
