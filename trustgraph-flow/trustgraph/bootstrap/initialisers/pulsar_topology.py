"""
PulsarTopology initialiser — creates Pulsar tenant and namespaces
with their retention policies.

Runs pre-gate (``wait_for_services = False``) because config-svc and
flow-svc can't connect to Pulsar until these namespaces exist.
Admin-API calls are idempotent so re-runs on flag change are safe.
"""

import asyncio
import requests

from .. base import Initialiser

# Namespace configs.  flow/request take broker defaults.  response
# and notify get aggressive retention — those classes carry short-lived
# request/response and notification traffic only.
NAMESPACE_CONFIG = {
    "flow": {},
    "request": {},
    "response": {
        "retention_policies": {
            "retentionSizeInMB": -1,
            "retentionTimeInMinutes": 3,
            "subscriptionExpirationTimeMinutes": 30,
        },
    },
    "notify": {
        "retention_policies": {
            "retentionSizeInMB": -1,
            "retentionTimeInMinutes": 3,
            "subscriptionExpirationTimeMinutes": 5,
        },
    },
}

REQUEST_TIMEOUT = 10


class PulsarTopology(Initialiser):

    wait_for_services = False

    def __init__(
            self,
            admin_url="http://pulsar:8080",
            tenant="tg",
            **kwargs,
    ):
        super().__init__(**kwargs)
        self.admin_url = admin_url.rstrip("/")
        self.tenant = tenant

    async def run(self, ctx, old_flag, new_flag):
        # requests is blocking; offload to executor so the loop stays
        # responsive.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._reconcile_sync, ctx.logger)

    # ------------------------------------------------------------------
    # Sync admin-API calls.
    # ------------------------------------------------------------------

    def _get_clusters(self):
        resp = requests.get(
            f"{self.admin_url}/admin/v2/clusters",
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _tenant_exists(self):
        resp = requests.get(
            f"{self.admin_url}/admin/v2/tenants/{self.tenant}",
            timeout=REQUEST_TIMEOUT,
        )
        return resp.status_code == 200

    def _create_tenant(self, clusters):
        resp = requests.put(
            f"{self.admin_url}/admin/v2/tenants/{self.tenant}",
            json={"adminRoles": [], "allowedClusters": clusters},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 204:
            raise RuntimeError(
                f"Tenant {self.tenant!r} create failed: "
                f"{resp.status_code} {resp.text}"
            )

    def _namespace_exists(self, namespace):
        resp = requests.get(
            f"{self.admin_url}/admin/v2/namespaces/"
            f"{self.tenant}/{namespace}",
            timeout=REQUEST_TIMEOUT,
        )
        return resp.status_code == 200

    def _create_namespace(self, namespace, config):
        resp = requests.put(
            f"{self.admin_url}/admin/v2/namespaces/"
            f"{self.tenant}/{namespace}",
            json=config,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 204:
            raise RuntimeError(
                f"Namespace {self.tenant}/{namespace} create failed: "
                f"{resp.status_code} {resp.text}"
            )

    def _reconcile_sync(self, logger):
        if not self._tenant_exists():
            clusters = self._get_clusters()
            logger.info(
                f"Creating tenant {self.tenant!r} with clusters {clusters}"
            )
            self._create_tenant(clusters)
        else:
            logger.debug(f"Tenant {self.tenant!r} already exists")

        for namespace, config in NAMESPACE_CONFIG.items():
            if self._namespace_exists(namespace):
                logger.debug(
                    f"Namespace {self.tenant}/{namespace} already exists"
                )
                continue
            logger.info(
                f"Creating namespace {self.tenant}/{namespace}"
            )
            self._create_namespace(namespace, config)
