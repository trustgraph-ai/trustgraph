"""
Initialises TrustGraph pub/sub infrastructure and pushes initial config.

For Pulsar: creates tenant, namespaces, and retention policies.
For RabbitMQ: queues are auto-declared, so only config push is needed.
"""

import requests
import time
import argparse
import json

from trustgraph.clients.config_client import ConfigClient
from trustgraph.base.pubsub import add_pubsub_args

default_pulsar_admin_url = "http://pulsar:8080"
subscriber = "tg-init-pubsub"


def get_clusters(url):

    print("Get clusters...", flush=True)

    resp = requests.get(f"{url}/admin/v2/clusters")

    if resp.status_code != 200: raise RuntimeError("Could not fetch clusters")

    return resp.json()

def ensure_tenant(url, tenant, clusters):

    resp = requests.get(f"{url}/admin/v2/tenants/{tenant}")

    if resp.status_code == 200:
        print(f"Tenant {tenant} already exists.", flush=True)
        return

    resp = requests.put(
        f"{url}/admin/v2/tenants/{tenant}",
        json={
            "adminRoles": [],
            "allowedClusters": clusters,
        }
    )

    if resp.status_code != 204:
        print(resp.text, flush=True)
        raise RuntimeError("Tenant creation failed.")

    print(f"Tenant {tenant} created.", flush=True)

def ensure_namespace(url, tenant, namespace, config):

    resp = requests.get(f"{url}/admin/v2/namespaces/{tenant}/{namespace}")

    if resp.status_code == 200:
        print(f"Namespace {tenant}/{namespace} already exists.", flush=True)
        return

    resp = requests.put(
        f"{url}/admin/v2/namespaces/{tenant}/{namespace}",
        json=config,
    )

    if resp.status_code != 204:
        print(resp.status_code, flush=True)
        print(resp.text, flush=True)
        raise RuntimeError(f"Namespace {tenant}/{namespace} creation failed.")

    print(f"Namespace {tenant}/{namespace} created.", flush=True)

def ensure_config(config, **pubsub_config):

    cli = ConfigClient(
        subscriber=subscriber,
        **pubsub_config,
    )

    while True:

        try:

            print("Get current config...", flush=True)
            current, version = cli.config(timeout=5)

        except Exception as e:

            print("Exception:", e, flush=True)
            time.sleep(2)
            print("Retrying...", flush=True)
            continue

        print("Current config version is", version, flush=True)

        if version != 0:
            print("Already updated, not updating config.  Done.", flush=True)
            return

        print("Config is version 0, updating...", flush=True)

        batch = []

        for type in config:
            for key in config[type]:
                print(f"Adding {type}/{key} to update.", flush=True)
                batch.append({
                    "type": type,
                    "key": key,
                    "value": json.dumps(config[type][key]),
                })

        try:
            cli.put(batch, timeout=10)
            print("Update succeeded.", flush=True)
            break
        except Exception as e:
            print("Exception:", e, flush=True)
            time.sleep(2)
            print("Retrying...", flush=True)
            continue

def init_pulsar(pulsar_admin_url, tenant):
    """Pulsar-specific setup: create tenant, namespaces, retention policies."""

    clusters = get_clusters(pulsar_admin_url)

    ensure_tenant(pulsar_admin_url, tenant, clusters)

    ensure_namespace(pulsar_admin_url, tenant, "flow", {})

    ensure_namespace(pulsar_admin_url, tenant, "request", {})

    ensure_namespace(pulsar_admin_url, tenant, "response", {
        "retention_policies": {
            "retentionSizeInMB": -1,
            "retentionTimeInMinutes": 3,
            "subscriptionExpirationTimeMinutes": 30,
        }
    })

    ensure_namespace(pulsar_admin_url, tenant, "state", {
        "retention_policies": {
            "retentionSizeInMB": 10,
            "retentionTimeInMinutes": -1,
            "subscriptionExpirationTimeMinutes": 5,
        }
    })


def push_config(config_json, config_file, **pubsub_config):
    """Push initial config if provided."""

    if config_json is not None:

        try:
            print("Decoding config...", flush=True)
            dec = json.loads(config_json)
            print("Decoded.", flush=True)
        except Exception as e:
            print("Exception:", e, flush=True)
            raise e

        ensure_config(dec, **pubsub_config)

    elif config_file is not None:

        try:
            print("Decoding config...", flush=True)
            dec = json.load(open(config_file))
            print("Decoded.", flush=True)
        except Exception as e:
            print("Exception:", e, flush=True)
            raise e

        ensure_config(dec, **pubsub_config)

    else:
        print("No config to update.", flush=True)


def main():

    parser = argparse.ArgumentParser(
        prog='tg-init-trustgraph',
        description=__doc__,
    )

    parser.add_argument(
        '--pulsar-admin-url',
        default=default_pulsar_admin_url,
        help=f'Pulsar admin URL (default: {default_pulsar_admin_url})',
    )

    parser.add_argument(
        '-c', '--config',
        help=f'Initial configuration to load',
    )

    parser.add_argument(
        '-C', '--config-file',
        help=f'Initial configuration to load from file',
    )

    parser.add_argument(
        '-t', '--tenant',
        default="tg",
        help=f'Tenant (default: tg)',
    )

    add_pubsub_args(parser)

    args = parser.parse_args()

    backend_type = args.pubsub_backend

    # Extract pubsub config from args
    pubsub_config = {
        k: v for k, v in vars(args).items()
        if k not in ('pulsar_admin_url', 'config', 'config_file', 'tenant')
    }

    while True:

        try:

            # Pulsar-specific setup (tenants, namespaces)
            if backend_type == 'pulsar':
                print(flush=True)
                print(
                    f"Initialising Pulsar at {args.pulsar_admin_url}...",
                    flush=True,
                )
                init_pulsar(args.pulsar_admin_url, args.tenant)
            else:
                print(flush=True)
                print(
                    f"Using {backend_type} backend (no admin setup needed).",
                    flush=True,
                )

            # Push config (works with any backend)
            push_config(
                args.config, args.config_file,
                **pubsub_config,
            )

            print("Initialisation complete.", flush=True)
            break

        except Exception as e:

            print("Exception:", e, flush=True)

            print("Sleeping...", flush=True)
            time.sleep(2)
            print("Will retry...", flush=True)

if __name__ == "__main__":
    main()
