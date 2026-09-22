
# Developer's Guide

See https://docs.trustgraph.ai/contributing/ for the current
developer documentation.

# Maintainer's Guide

## Branch strategy

Release branches are named `release/vX.Y`. A new release branch is
created by branching from the previous `release/vX.Y`.

Contributors should code against the latest release branch.
Back-port critical bugs and security fixes to the latest stable build.

## Opening a new release branch

When opening a new release branch, update the version number in two
places:

1. Dependencies in `trustgraph-*/pyproject.toml`.
2. The release version in `.github/workflows/pull-request.yaml`
   (`make update-package-versions VERSION=X.Y.Z`).

## README and documentation changes

Changes to `README.md` are made on `master` via a PR. When starting a
new release branch, merge `master` onto the release branch to pick up
any README changes. This must be a **merge commit**, not a squash, to
avoid losing contributor attribution. Do not merge `master` mid-release
— only at the start of a new branch.

Periodically merge release branches back onto `master` (also a **merge
commit**, not a squash) to keep things in sync and maintain the
contributor panel.

## Pull requests

All code changes go through a PR onto a release branch. PRs should
pass tests before merging. If tests are skipped (e.g. the test suite
is broken), record the reason in the PR.

Keep the build green and shipping — a broken build blocks other
contributors from testing.

## Tagging and releasing

New builds are made by tagging with `vX.Y.Z` and pushing the tag. CI
handles building and releasing from there.
