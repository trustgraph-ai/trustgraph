#!/usr/bin/env python3

"""
Docker Hub tag cleanup script.

Lists and optionally deletes container image tags from Docker Hub
that fall within a specified semver version range.

Dry-run by default. Pass --delete to actually remove tags.

Usage examples:
  # List what would be deleted across all trustgraph-* repos, versions <= 1.4.21
  python scripts/dockerhub-cleanup.py \
    --repo-pattern 'trustgraph/trustgraph-*' \
    --min-version 0.0.0 --max-version 1.4.21

  # Actually delete them
  python scripts/dockerhub-cleanup.py \
    --repo-pattern 'trustgraph/trustgraph-*' \
    --min-version 0.0.0 --max-version 1.4.21 \
    --delete

  # Target a single repo
  python scripts/dockerhub-cleanup.py \
    --repo-pattern 'trustgraph/trustgraph-flow' \
    --min-version 0.0.0 --max-version 1.4.21

  # Also include tags matching a glob pattern
  python scripts/dockerhub-cleanup.py \
    --repo-pattern 'trustgraph/trustgraph-*' \
    --min-version 0.0.0 --max-version 1.4.21 \
    --include-pattern '*-rc*'
"""

import argparse
import fnmatch
import re
import sys
import time

import requests

HUB_API = "https://hub.docker.com/v2"


def parse_semver(tag):
    """
    Parse a tag as semver (major.minor.patch), ignoring any trailing suffix.
    e.g. '2.4.9' -> (2, 4, 9)
         '2.4.9-amd64' -> (2, 4, 9)
         'v1.0.0-rc1' -> (1, 0, 0)
         'latest' -> None
    """
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", tag)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def authenticate(username, password):
    """Authenticate with Docker Hub and return a JWT token."""
    resp = requests.post(
        f"{HUB_API}/users/login/",
        json={"username": username, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["token"]


def authenticate_pat(pat):
    """Authenticate with a Personal Access Token."""
    resp = requests.post(
        f"{HUB_API}/users/login/",
        json={"username": "", "password": pat},
        headers={"Content-Type": "application/json"},
    )
    # PATs may work differently - try the token-based approach
    if resp.status_code != 200:
        # Use PAT directly as bearer token
        return pat
    return resp.json()["token"]


def get_repos(namespace, token):
    """Fetch all repositories for a namespace, handling pagination."""
    repos = []
    url = f"{HUB_API}/repositories/{namespace}/?page_size=100"
    while url:
        resp = requests.get(url, headers={"Authorization": f"JWT {token}"})
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        data = resp.json()
        repos.extend(data["results"])
        url = data.get("next")
    return repos


def get_tags(namespace, repo, token):
    """Fetch all tags for a repository, handling pagination."""
    tags = []
    url = f"{HUB_API}/repositories/{namespace}/{repo}/tags/?page_size=100"
    while url:
        resp = requests.get(url, headers={"Authorization": f"JWT {token}"})
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        data = resp.json()
        tags.extend(data["results"])
        url = data.get("next")
    return tags


def delete_tag(namespace, repo, tag, token):
    """Delete a single tag from a repository."""
    url = f"{HUB_API}/repositories/{namespace}/{repo}/tags/{tag}/"
    resp = requests.delete(url, headers={"Authorization": f"JWT {token}"})
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old Docker Hub tags by semver range"
    )
    parser.add_argument(
        "--repo-pattern",
        required=True,
        help="Repo pattern e.g. 'trustgraph/trustgraph-*'",
    )
    parser.add_argument(
        "--min-version",
        default="0.0.0",
        help="Minimum version to delete (inclusive, default: 0.0.0)",
    )
    parser.add_argument(
        "--max-version",
        required=True,
        help="Maximum version to delete (inclusive)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete tags (default is dry-run)",
    )
    parser.add_argument(
        "--token",
        help="Docker Hub PAT (or set DOCKER_HUB_TOKEN env var). "
             "Requires --username to exchange for a JWT.",
    )
    parser.add_argument(
        "--username",
        help="Docker Hub username (required with --token, or with --password)",
    )
    parser.add_argument(
        "--password",
        help="Docker Hub password (alternative to PAT)",
    )
    parser.add_argument(
        "--include-pattern",
        action="append",
        default=[],
        help="Additional tag glob patterns to include (e.g. '*-rc*'). "
             "Can be specified multiple times.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between deletes in seconds (default: 0.5)",
    )

    args = parser.parse_args()

    # Authenticate
    import os

    token = args.token or os.environ.get("DOCKER_HUB_TOKEN")
    if token:
        if not args.username:
            print(
                "Error: --username is required when using --token / DOCKER_HUB_TOKEN",
                file=sys.stderr,
            )
            sys.exit(1)
        auth_token = authenticate(args.username, token)
    elif args.username and args.password:
        auth_token = authenticate(args.username, args.password)
    else:
        print(
            "Error: provide --token / DOCKER_HUB_TOKEN, "
            "or --username and --password",
            file=sys.stderr,
        )
        sys.exit(1)

    # Parse the namespace/pattern
    pattern = args.repo_pattern
    if "/" not in pattern:
        print("Error: --repo-pattern must include namespace e.g. 'trustgraph/trustgraph-*'", file=sys.stderr)
        sys.exit(1)

    namespace, repo_glob = pattern.split("/", 1)

    # Parse version range
    min_ver = parse_semver(args.min_version)
    max_ver = parse_semver(args.max_version)
    if not min_ver or not max_ver:
        print("Error: versions must be in semver format (e.g. 1.4.21)", file=sys.stderr)
        sys.exit(1)

    if not args.delete:
        print("=" * 60)
        print("  DRY RUN - no tags will be deleted")
        print("  Pass --delete to actually remove tags")
        print("=" * 60)
        print()

    # Fetch repos
    print(f"Fetching repos for namespace '{namespace}'...")
    repos = get_repos(namespace, auth_token)
    matched_repos = [
        r for r in repos if fnmatch.fnmatch(r["name"], repo_glob)
    ]
    print(f"Found {len(matched_repos)} repos matching '{repo_glob}'")
    print()

    total_delete = 0
    total_skip = 0

    for repo_info in sorted(matched_repos, key=lambda r: r["name"]):
        repo_name = repo_info["name"]
        tags = get_tags(namespace, repo_name, auth_token)

        to_delete = []
        skipped = []

        for tag_info in tags:
            tag = tag_info["name"]

            # Check semver range match
            ver = parse_semver(tag)
            if ver is not None and min_ver <= ver <= max_ver:
                to_delete.append(tag)
                continue

            # Check optional include patterns
            if any(fnmatch.fnmatch(tag, p) for p in args.include_pattern):
                to_delete.append(tag)
                continue

            skipped.append(tag)

        if not to_delete:
            continue

        to_delete.sort()

        print(f"  {namespace}/{repo_name}:")
        print(f"    Delete ({len(to_delete)}):")
        for tag in to_delete:
            print(f"      {tag}")
        if skipped:
            print(f"    Skipping ({len(skipped)}): {', '.join(sorted(skipped))}")
        print()

        total_delete += len(to_delete)
        total_skip += len(skipped)

        if args.delete:
            for tag in to_delete:
                try:
                    delete_tag(namespace, repo_name, tag, auth_token)
                    print(f"    Deleted {tag}")
                except requests.HTTPError as e:
                    print(f"    FAILED to delete {tag}: {e}", file=sys.stderr)
                time.sleep(args.delay)

    print("-" * 60)
    action = "Deleted" if args.delete else "Would delete"
    print(f"{action} {total_delete} tags, skipped {total_skip} tags")

    if not args.delete and total_delete > 0:
        print()
        print("Run again with --delete to remove these tags.")


if __name__ == "__main__":
    main()
