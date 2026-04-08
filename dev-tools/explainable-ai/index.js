
// ============================================================================
// TrustGraph Explainability API Demo
// ============================================================================
//
// This example demonstrates how to use the TrustGraph streaming agent API
// with explainability events. It shows how to:
//
//   1. Send an agent query and receive streaming thinking/observation/answer
//   2. Receive and parse explainability events as they arrive
//   3. Resolve the provenance chain for knowledge graph edges:
//      subgraph -> chunk -> page -> document
//   4. Fetch source text from the librarian using chunk IDs
//
// Explainability events use RDF triples (W3C PROV ontology + TrustGraph
// namespace) to describe the retrieval pipeline. The key event types are:
//
//   - AgentQuestion: The initial user query
//   - Analysis/ToolUse: Agent deciding which tool to invoke
//   - GraphRagQuestion: A sub-query sent to the Graph RAG pipeline
//   - Grounding: Concepts extracted from the query for graph traversal
//   - Exploration: Entities discovered during knowledge graph traversal
//   - Focus: The selected knowledge graph edges (triples) used for context
//   - Synthesis: The RAG answer synthesised from retrieved context
//   - Observation: The tool result returned to the agent
//   - Conclusion/Answer: The agent's final answer
//
// Each event carries RDF triples that link back through the provenance chain,
// allowing full traceability from answer back to source documents.
// ============================================================================

import { createTrustGraphSocket } from '@trustgraph/client';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const USER = "trustgraph";

// Simple question
const QUESTION = "Tell me about the author of the document";

// Likely to trigger the deep research plan-and-execute pattern
//const QUESTION = "Do deep research and explain the risks posed globalisation in the modern world";

const SOCKET_URL = "ws://localhost:8088/api/v1/socket";

// ---------------------------------------------------------------------------
// RDF predicates and TrustGraph namespace constants
// ---------------------------------------------------------------------------

const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const PROV_DERIVED = "http://www.w3.org/ns/prov#wasDerivedFrom";

const TG_GROUNDING = "https://trustgraph.ai/ns/Grounding";
const TG_CONCEPT = "https://trustgraph.ai/ns/concept";
const TG_EXPLORATION = "https://trustgraph.ai/ns/Exploration";
const TG_ENTITY = "https://trustgraph.ai/ns/entity";
const TG_FOCUS = "https://trustgraph.ai/ns/Focus";
const TG_EDGE = "https://trustgraph.ai/ns/edge";
const TG_CONTAINS = "https://trustgraph.ai/ns/contains";

// ---------------------------------------------------------------------------
// Utility: check whether a set of triples assigns a given RDF type to an ID
// ---------------------------------------------------------------------------

const isType = (triples, id, type) =>
    triples.some(t => t.s.i === id && t.p.i === RDF_TYPE && t.o.i === type);

// ---------------------------------------------------------------------------
// Utility: word-wrap text for display
// ---------------------------------------------------------------------------

const wrapText = (text, width, indent, maxLines) => {
    const clean = text.replace(/\s+/g, " ").trim();
    const lines = [];
    let remaining = clean;
    while (remaining.length > 0 && lines.length < maxLines) {
        if (remaining.length <= width) {
            lines.push(remaining);
            break;
        }
        let breakAt = remaining.lastIndexOf(" ", width);
        if (breakAt <= 0) breakAt = width;
        lines.push(remaining.substring(0, breakAt));
        remaining = remaining.substring(breakAt).trimStart();
    }
    if (remaining.length > 0 && lines.length >= maxLines)
        lines[lines.length - 1] += " ...";
    return lines.map(l => indent + l).join("\n");
};

// ---------------------------------------------------------------------------
// Connect to TrustGraph
// ---------------------------------------------------------------------------

console.log("=".repeat(80));
console.log("TrustGraph Explainability API Demo");
console.log("=".repeat(80));
console.log(`Connecting to: ${SOCKET_URL}`);
console.log(`Question: ${QUESTION}`);
console.log("=".repeat(80));

const client = createTrustGraphSocket(USER, undefined, SOCKET_URL);

console.log("Connected, sending query...\n");

// Get a flow handle. Flows provide access to AI operations (agent, RAG,
// text completion, etc.) as well as knowledge graph queries.
const flow = client.flow("default");

// Get a librarian handle for fetching source document text.
const librarian = client.librarian();

// ---------------------------------------------------------------------------
// Inline explain event printing
// ---------------------------------------------------------------------------
// Explain events arrive during streaming alongside thinking/observation/
// answer chunks. We print a summary immediately and store them for
// post-processing (label resolution and provenance lookups require async
// queries that can't run inside the synchronous callback).

const explainEvents = [];

const printExplainInline = (explainEvent) => {
    const { explainId, explainTriples } = explainEvent;
    if (!explainTriples) return;

    // Extract the RDF types assigned to the explain event's own ID.
    // Every explain event has rdf:type triples that identify what kind
    // of pipeline step it represents (Grounding, Exploration, Focus, etc.)
    const types = explainTriples
        .filter(t => t.s.i === explainId && t.p.i === RDF_TYPE)
        .map(t => t.o.i);

    // Show short type names (e.g. "Grounding" instead of full URI)
    const shortTypes = types
        .map(t => t.split("/").pop().split("#").pop())
        .join(", ");
    console.log(`  [explain] ${shortTypes}`);

    // Grounding events contain the concepts extracted from the query.
    // These are the seed terms used to begin knowledge graph traversal.
    if (isType(explainTriples, explainId, TG_GROUNDING)) {
        const concepts = explainTriples
            .filter(t => t.s.i === explainId && t.p.i === TG_CONCEPT)
            .map(t => t.o.v);
        console.log(`    Grounding concepts: ${concepts.join(", ")}`);
    }

    // Exploration events list the entities found during graph traversal.
    // We show the count here; labelled names are printed after resolution.
    if (isType(explainTriples, explainId, TG_EXPLORATION)) {
        const count = explainTriples
            .filter(t => t.s.i === explainId && t.p.i === TG_ENTITY).length;
        console.log(`    Entities: ${count} found (see below)`);
    }
};

const collectExplain = (explainEvent) => {
    printExplainInline(explainEvent);
    explainEvents.push(explainEvent);
};

// ---------------------------------------------------------------------------
// Label resolution
// ---------------------------------------------------------------------------
// Many explain triples reference entities and predicates by URI. We query
// the knowledge graph for rdfs:label to get human-readable names.

const resolveLabels = async (uris) => {
    const labels = new Map();
    await Promise.all(uris.map(async (uri) => {
        try {
            const results = await flow.triplesQuery(
                { t: "i", i: uri },
                { t: "i", i: RDFS_LABEL },
            );
            if (results.length > 0) {
                labels.set(uri, results[0].o.v);
            }
        } catch (e) {
            // No label found, fall back to URI
        }
    }));
    return labels;
};

// ---------------------------------------------------------------------------
// Provenance resolution for knowledge graph edges
// ---------------------------------------------------------------------------
// Focus events contain the knowledge graph triples (edges) that were selected
// as context for the RAG answer. Each edge can be traced back through the
// provenance chain to the original source document:
//
//   subgraph --contains--> <<edge triple>>      (RDF-star triple term)
//   subgraph --wasDerivedFrom--> chunk           (text chunk)
//   chunk    --wasDerivedFrom--> page            (document page)
//   page     --wasDerivedFrom--> document        (original document)
//
// The chunk URI also serves as the content ID in the librarian, so it can
// be used to fetch the actual source text.

const resolveEdgeSources = async (edgeTriples) => {
    const iri = (uri) => ({ t: "i", i: uri });
    const sources = new Map();

    await Promise.all(edgeTriples.map(async (tr) => {
        const key = JSON.stringify(tr);
        try {
            // Step 1: Find the subgraph that contains this edge triple.
            // The query uses an RDF-star triple term as the object: the
            // knowledge graph stores subgraph -> contains -> <<s, p, o>>.
            const subgraphResults = await flow.triplesQuery(
                undefined,
                iri(TG_CONTAINS),
                { t: "t", tr },
            );
            if (subgraphResults.length === 0) {
                if (tr.o.t === "l" || tr.o.t === "i") {
                    console.log(`  No source match for triple:`);
                    console.log(`    s: ${tr.s.i}`);
                    console.log(`    p: ${tr.p.i}`);
                    console.log(`    o: ${JSON.stringify(tr.o)}`);
                }
                return;
            }
            const subgraph = subgraphResults[0].s.i;

            // Step 2: Walk wasDerivedFrom chain: subgraph -> chunk
            const chunkResults = await flow.triplesQuery(
                iri(subgraph), iri(PROV_DERIVED),
            );
            if (chunkResults.length === 0) {
                sources.set(key, { subgraph });
                return;
            }
            const chunk = chunkResults[0].o.i;

            // Step 3: chunk -> page
            const pageResults = await flow.triplesQuery(
                iri(chunk), iri(PROV_DERIVED),
            );
            if (pageResults.length === 0) {
                sources.set(key, { subgraph, chunk });
                return;
            }
            const page = pageResults[0].o.i;

            // Step 4: page -> document
            const docResults = await flow.triplesQuery(
                iri(page), iri(PROV_DERIVED),
            );
            const document = docResults.length > 0 ? docResults[0].o.i : undefined;

            sources.set(key, { subgraph, chunk, page, document });
        } catch (e) {
            // Query failed, skip this edge
        }
    }));

    return sources;
};

// ---------------------------------------------------------------------------
// Collect URIs that need label resolution
// ---------------------------------------------------------------------------
// Scans explain events for entity URIs (from Exploration events) and edge
// term URIs (from Focus events) so we can batch-resolve their labels.

const collectUris = (events) => {
    const uris = new Set();
    for (const { explainId, explainTriples } of events) {
        if (!explainTriples) continue;

        // Entity URIs from exploration
        if (isType(explainTriples, explainId, TG_EXPLORATION)) {
            for (const t of explainTriples) {
                if (t.s.i === explainId && t.p.i === TG_ENTITY)
                    uris.add(t.o.i);
            }
        }

        // Subject, predicate, and object URIs from focus edge triples
        if (isType(explainTriples, explainId, TG_FOCUS)) {
            for (const t of explainTriples) {
                if (t.p.i === TG_EDGE && t.o.t === "t") {
                    const tr = t.o.tr;
                    if (tr.s.t === "i") uris.add(tr.s.i);
                    if (tr.p.t === "i") uris.add(tr.p.i);
                    if (tr.o.t === "i") uris.add(tr.o.i);
                }
            }
        }
    }
    return uris;
};

// ---------------------------------------------------------------------------
// Collect edge triples from Focus events
// ---------------------------------------------------------------------------
// Focus events contain selectedEdge -> edge relationships. Each edge's
// object is an RDF-star triple term ({t: "t", tr: {s, p, o}}) representing
// the actual knowledge graph triple used as RAG context.

const collectEdgeTriples = (events) => {
    const edges = [];
    for (const { explainId, explainTriples } of events) {
        if (!explainTriples) continue;
        if (isType(explainTriples, explainId, TG_FOCUS)) {
            for (const t of explainTriples) {
                if (t.p.i === TG_EDGE && t.o.t === "t")
                    edges.push(t.o.tr);
            }
        }
    }
    return edges;
};

// ---------------------------------------------------------------------------
// Print knowledge graph edges with provenance
// ---------------------------------------------------------------------------
// Displays each edge triple with resolved labels and its source location
// (chunk -> page -> document).

const printFocusEdges = (events, labels, edgeSources) => {
    const label = (uri) => labels.get(uri) || uri;

    for (const { explainId, explainTriples } of events) {
        if (!explainTriples) continue;
        if (!isType(explainTriples, explainId, TG_FOCUS)) continue;

        const termValue = (term) =>
            term.t === "i" ? label(term.i) : (term.v || "?");

        const edges = explainTriples
            .filter(t => t.p.i === TG_EDGE && t.o.t === "t")
            .map(t => t.o.tr);

        const display = edges.slice(0, 20);
        for (const tr of display) {
            console.log(`  ${termValue(tr.s)} -> ${termValue(tr.p)} -> ${termValue(tr.o)}`);
            const src = edgeSources.get(JSON.stringify(tr));
            if (src) {
                const parts = [];
                if (src.chunk) parts.push(label(src.chunk));
                if (src.page) parts.push(label(src.page));
                if (src.document) parts.push(label(src.document));
                if (parts.length > 0)
                    console.log(`    Source: ${parts.join(" -> ")}`);
            }
        }
        if (edges.length > 20)
            console.log(`  ... and ${edges.length - 20} more`);
    }
};

// ---------------------------------------------------------------------------
// Fetch chunk text from the librarian
// ---------------------------------------------------------------------------
// The chunk URI (e.g. urn:chunk:UUID) serves as a universal ID that ties
// together provenance metadata, embeddings, and the source text content.
// The librarian stores the original text keyed by this same URI, so we
// can retrieve it with streamDocument(chunkUri).

const fetchChunkText = (chunkUri) => {
    return new Promise((resolve, reject) => {
        let text = "";
        librarian.streamDocument(
            chunkUri,
            (content, chunkIndex, totalChunks, complete) => {
                text += content;
                if (complete) resolve(text);
            },
            (error) => reject(error),
        );
    });
};

// ===========================================================================
// Send the agent query
// ===========================================================================
// The agent callback receives four types of streaming content:
//   - think: the agent's reasoning (chain-of-thought)
//   - observe: tool results returned to the agent
//   - answer: the final answer being generated
//   - error: any errors during processing
//
// The onExplain callback fires for each explainability event, delivering
// RDF triples that describe what happened at each pipeline stage.

let thought = "";
let obs = "";
let ans = "";

await flow.agent(

    QUESTION,

    // Think callback: agent reasoning / chain-of-thought
    (chunk, complete, messageId, metadata) => {
        thought += chunk;
        if (complete) {
            console.log("\nThinking:", thought, "\n");
            thought = "";
        }
    },

    // Observe callback: tool results returned to the agent
    (chunk, complete, messageId, metadata) => {
        obs += chunk;
        if (complete) {
            console.log("\nObservation:", obs, "\n");
            obs = "";
        }
    },

    // Answer callback: the agent's final response
    (chunk, complete, messageId, metadata) => {
        ans += chunk;
        if (complete) {
            console.log("\nAnswer:", ans, "\n");
            ans = "";
        }
    },

    // Error callback
    (error) => {
        console.log(JSON.stringify({ type: "error", error }, null, 2));
    },

    // Explain callback: explainability events with RDF triples
    (explainEvent) => {
        collectExplain(explainEvent);
    }

);

// ===========================================================================
// Post-processing: resolve labels, provenance, and source text
// ===========================================================================
// After the agent query completes, we have all the explain events. Now we
// can make async queries to:
//   1. Trace each edge back to its source document (provenance chain)
//   2. Resolve URIs to human-readable labels
//   3. Fetch the original text for each source chunk

console.log("Resolving provenance...\n");

// Resolve the provenance chain for each knowledge graph edge
const edgeTriples = collectEdgeTriples(explainEvents);
const edgeSources = await resolveEdgeSources(edgeTriples);

// Collect all URIs that need labels: entities, edge terms, and source URIs
const uris = collectUris(explainEvents);
for (const src of edgeSources.values()) {
    if (src.chunk) uris.add(src.chunk);
    if (src.page) uris.add(src.page);
    if (src.document) uris.add(src.document);
}
const labels = await resolveLabels([...uris]);

const label = (uri) => labels.get(uri) || uri;

// ---------------------------------------------------------------------------
// Display: Entities retrieved during graph exploration
// ---------------------------------------------------------------------------

for (const { explainId, explainTriples } of explainEvents) {
    if (!explainTriples) continue;
    if (!isType(explainTriples, explainId, TG_EXPLORATION)) continue;
    const entities = explainTriples
        .filter(t => t.s.i === explainId && t.p.i === TG_ENTITY)
        .map(t => label(t.o.i));
    const display = entities.slice(0, 10);
    console.log("=".repeat(80));
    console.log("Entities Retrieved");
    console.log("=".repeat(80));
    console.log(`  ${entities.length} entities: ${display.join(", ")}${entities.length > 10 ? ", ..." : ""}`);
}

// ---------------------------------------------------------------------------
// Display: Knowledge graph edges with provenance
// ---------------------------------------------------------------------------

console.log("\n" + "=".repeat(80));
console.log("Knowledge Graph Edges");
console.log("=".repeat(80));
printFocusEdges(explainEvents, labels, edgeSources);

// ---------------------------------------------------------------------------
// Display: Source text for each chunk referenced by the edges
// ---------------------------------------------------------------------------

const uniqueChunks = new Set();
for (const src of edgeSources.values()) {
    if (src.chunk) uniqueChunks.add(src.chunk);
}

console.log(`\nFetching text for ${uniqueChunks.size} source chunks...`);
const chunkTexts = new Map();
await Promise.all([...uniqueChunks].map(async (chunkUri) => {
    try {
        // streamDocument returns base64-encoded content
        const text = await fetchChunkText(chunkUri);
        chunkTexts.set(chunkUri, text);
    } catch (e) {
        // Failed to fetch text for this chunk
    }
}));

console.log("\n" + "=".repeat(80));
console.log("Sources");
console.log("=".repeat(80));

let sourceIndex = 0;
for (const chunkUri of uniqueChunks) {
    sourceIndex++;
    const chunkLabel = labels.get(chunkUri) || chunkUri;

    // Find the page and document labels for this chunk
    let pageLabel, docLabel;
    for (const src of edgeSources.values()) {
        if (src.chunk === chunkUri) {
            if (src.page) pageLabel = labels.get(src.page) || src.page;
            if (src.document) docLabel = labels.get(src.document) || src.document;
            break;
        }
    }

    console.log(`\n  [${sourceIndex}] ${docLabel || "?"} / ${pageLabel || "?"} / ${chunkLabel}`);
    console.log("  " + "-".repeat(70));

    // Decode the base64 content and display a wrapped snippet
    const b64 = chunkTexts.get(chunkUri);
    if (b64) {
        const text = Buffer.from(b64, "base64").toString("utf-8");
        console.log(wrapText(text, 76, "    ", 6));
    }
}

// ---------------------------------------------------------------------------
// Clean up
// ---------------------------------------------------------------------------

console.log("\n" + "=".repeat(80));
console.log("Query complete");
console.log("=".repeat(80));

client.close();
process.exit(0);
