---
layout: default
title: "Active-Flow Key Restructure"
parent: "Tech Specs"
---

# Active-Flow Key Restructure

## Problem

Active-flow config uses `('active-flow', processor)` as its key, where
each processor's value is a JSON blob containing all flow variants
assigned to that processor:

```
('active-flow', 'chunker') -> { "default": {...}, "flow2": {...} }
```

This causes two problems:

1. **Read-modify-write on every change.** Starting or stopping a flow
   requires fetching the processor's current blob, parsing it, adding
   or removing a variant, serialising it, and writing it back. This is
   a concurrency hazard if two flow operations target the same
   processor simultaneously.

2. **Noisy config pushes.** Config subscribers subscribe to a type,
   not a specific key. Every active-flow write triggers a config push
   that causes every processor in the system to fetch the full config
   and re-evaluate, even though only one processor's config changed.
   With N processors in a blueprint, a single flow start/stop causes
   N writes and N^2 config fetches across the system.

## Proposed Change

Restructure the key to `('active-flow', 'processor:variant')` where
each key holds a single flow variant's configuration:

```
('active-flow', 'chunker:default') -> { "topics": {...}, "parameters": {...} }
('active-flow', 'chunker:flow2')   -> { "topics": {...}, "parameters": {...} }
```

Starting a flow is a set of clean puts. Stopping a flow is a set of
clean deletes. No read-modify-write. No JSON blob merging.

The config push problem (all processors fetching on every change)
remains — that's a limitation of the config subscription model and
would require per-key subscriptions to solve. But eliminating the
read-modify-write removes the concurrency hazard and simplifies the
flow service code.

## What Changes

- **Flow service** (`flow.py`): `handle_start_flow` writes individual
  keys per processor:variant instead of merging into per-processor
  blobs. `handle_stop_flow` deletes individual keys instead of
  read-modify-write.
- **FlowProcessor** (`flow_processor.py`): `on_configure_flows`
  currently looks up `config["active-flow"][self.id]` to find a JSON
  blob of all its variants. Needs to scan all active-flow keys for
  entries prefixed with `self.id:` and assemble its flow list from
  those.
- **Config client**: May benefit from a prefix-scan or pattern-match
  query to support the FlowProcessor lookup efficiently.
- **Initial config / bootstrapping**: Any code that seeds active-flow
  entries at deployment time needs to use the new key format.
