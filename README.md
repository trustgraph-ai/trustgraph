
# Context Graph Demo

A React application that demonstrates
[TrustGraph](https://trustgraph.ai/) context graph capabilities
The demo provides an interactive graph visualisation, natural-language
querying, explainability views, and ontology browsing — all powered by
a TrustGraph backend. Load your own data to explore.

See it in action: [Context Graph demo video](https://www.youtube.com/watch?v=sWc7mkhITIo)

## Features

- **Graph view** — interactive force-directed graph of entities and
  relationships, with domain-based filtering
- **Query view** — natural-language questions answered by the TrustGraph
  knowledge graph
- **Explain view** — step-by-step explainability traces showing how
  answers were derived
- **Data view** — browse the raw documents loaded into TrustGraph
- **Ontology view** — explore the ontology (types and predicates)
  extracted from the dataset

## Prerequisites

- Node.js (v18+)
- A running [TrustGraph](https://trustgraph.ai/) instance (tested with
  TrustGraph 2.1)

## Preparing TrustGraph

This demo requires TrustGraph to be running in ontology mode:

1. Launch a flow using the `ontology` flow blueprint.
2. Load an OWL ontology into the workbench.
3. Process your data using the new flow.

## Getting started

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The Vite dev server proxies `/api/socket` (WebSocket) and other API
routes to the TrustGraph API gateway at `localhost:8088`. If your
TrustGraph instance is running on a different host or port, edit the
proxy targets in `vite.config.js`.

Build for production:

```bash
npm run build
```

## License

Copyright 2026 Knownext Inc. and Knownext Limited.
Licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for
details.
