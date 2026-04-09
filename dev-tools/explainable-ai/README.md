# Explainable AI Demo

Demonstrates the TrustGraph streaming agent API with inline explainability
events. Sends an agent query, receives streaming thinking/observation/answer
chunks alongside RDF provenance events, then resolves the full provenance
chain from answer back to source documents.

## What it shows

- Streaming agent responses (thinking, observation, answer)
- Inline explainability events with RDF triples (W3C PROV + TrustGraph namespace)
- Label resolution for entity and predicate URIs
- Provenance chain traversal: subgraph → chunk → page → document
- Source text retrieval from the librarian using chunk IDs

## Prerequisites

A running TrustGraph instance with at least one loaded document and a
running flow. The default configuration connects to `ws://localhost:8088`.

## Usage

```bash
npm install
node index.js
```

Edit the `QUESTION` and `SOCKET_URL` constants at the top of `index.js`
to change the query or target instance.
