import { useState, useEffect, useRef } from "react";
import { GraphCanvasSVG as GraphCanvas, NodeDetailPanel, SectionLabel, Badge, LoadingState, SearchInput, MessageBubble } from "../components";
import { useGraphData } from "../state";
import { COLLECTION } from "../config";
import type { Entity } from "../types";
import { useChat, useConversation, useEmbeddings, useGraphEmbeddings } from "@trustgraph/react-state";
import { getLocalName } from "../utils";
import { palette, text, border, withGlow } from "../theme";

// Type for embedding result items
interface EmbeddingResultItem {
  id: string;
  uri: string;
  label: string;
  color: string;
  icon: string;
  isEntity: boolean;
}

export function QueryView() {
  const [customInput, setCustomInput] = useState("");
  const [queryForEmbeddings, setQueryForEmbeddings] = useState<string | undefined>(undefined);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Entity | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { entities, relationships, ontology, propertyLabels, isLoading: graphLoading } = useGraphData();
  const { submitMessage, isSubmitting } = useChat();
  const messages = useConversation((state) => state.messages);
  const setChatMode = useConversation((state) => state.setChatMode);

  // Get embeddings for the query text - only fetch when we have a committed query
  const { embeddings, isLoading: embeddingsLoading } = useEmbeddings({
    flow: "default",
    term: queryForEmbeddings || undefined,
  });

  // Get graph entities from embeddings - only fetch when we have embeddings
  const hasEmbeddings = embeddings && embeddings.length > 0;
  const { graphEmbeddings, isLoading: graphEmbeddingsLoading } = useGraphEmbeddings({
    vecs: hasEmbeddings ? embeddings : [[]],
    limit: hasEmbeddings ? 10 : 0,
    collection: COLLECTION,
  });

  // Set chat mode to agent on mount
  useEffect(() => {
    setChatMode("agent");
  }, [setChatMode]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (query: string) => {
    if (query.trim() && !isSubmitting) {
      const trimmedQuery = query.trim();
      submitMessage({ input: trimmedQuery });
      setQueryForEmbeddings(trimmedQuery);
      setSelectedEntityId(null);
      setSelectedNode(null);
      setCustomInput("");
    }
  };


  // Match graph embedding entities to our loaded entities for labels and highlighting
  // graphEmbeddings returns RDF terms: { t: "i", i: "http://..." }
  // Only show matched entities, deduplicated by URI
  const embeddingResults: EmbeddingResultItem[] = [];
  const seenUris = new Set<string>();

  for (const ge of (hasEmbeddings && graphEmbeddings || []) as { t: string; i?: string }[]) {
    const uri = ge.i;
    if (!uri || seenUris.has(uri)) continue;

    const entityId = getLocalName(uri);
    const found = entities.find(e => e.id === entityId || e.uri === uri);

    // Only include actual entities, not properties/concepts
    if (found) {
      seenUris.add(uri);
      embeddingResults.push({
        id: entityId,
        uri,
        label: found.label,
        color: found.color,
        icon: found.icon,
        isEntity: true,
      });
    }
  }

  // Auto-select first embedding result when results arrive
  useEffect(() => {
    if (embeddingResults.length > 0 && !selectedEntityId && !selectedNode) {
      setSelectedEntityId(embeddingResults[0].id);
    }
  }, [embeddingResults.length, selectedEntityId, selectedNode]);

  // Extract entity IDs for highlighting on graph
  // Priority: selectedNode (graph click) > selectedEntityId (button click) > all embedding results
  const highlightedEntities = (() => {
    const focusId = selectedNode?.id || selectedEntityId;
    if (!focusId) {
      return embeddingResults.map(e => e.id);
    }
    // Find all entities connected to the focused entity
    const connected = new Set<string>([focusId]);
    for (const rel of relationships) {
      if (rel.from === focusId) {
        connected.add(rel.to);
      } else if (rel.to === focusId) {
        connected.add(rel.from);
      }
    }
    return Array.from(connected);
  })();

  if (graphLoading || !ontology) {
    return <LoadingState />;
  }

  return (
    <div style={{ display: "flex", height: "calc(100vh - 110px)" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Query input area */}
        <div style={{ padding: "20px 28px", borderBottom: `1px solid ${border.default}` }}>
          <SectionLabel marginBottom={12}>AGENT QUERIES</SectionLabel>

          <SearchInput
            value={customInput}
            onChange={setCustomInput}
            onSubmit={() => handleSubmit(customInput)}
            placeholder="Type your own question..."
            buttonText="Ask"
            isLoading={isSubmitting}
            buttonColor={palette.amber}
          />
        </div>

        {/* Related entities from graph embeddings */}
        {queryForEmbeddings && (
          <div style={{ padding: "16px 28px", borderBottom: `1px solid ${border.default}` }}>
            <SectionLabel>
              RELATED ENTITIES {(embeddingsLoading || graphEmbeddingsLoading) && <span style={{ color: palette.amber }}>loading...</span>}
            </SectionLabel>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {embeddingResults.length === 0 && !embeddingsLoading && !graphEmbeddingsLoading && (
                <span style={{ fontSize: 11, color: text.disabled, fontStyle: "italic" }}>No related concepts found</span>
              )}
              {embeddingResults.map((item) => {
                const isSelected = selectedEntityId === item.id;
                return (
                  <Badge
                    key={item.uri}
                    color={item.color}
                    selected={isSelected}
                    onClick={() => {
                      setSelectedEntityId(isSelected ? null : item.id);
                      setSelectedNode(null);
                    }}
                  >
                    <span style={{ fontSize: 10 }}>{item.icon}</span>
                    {item.label}
                  </Badge>
                );
              })}
            </div>
          </div>
        )}

        {/* Response area */}
        <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>
          {messages.length === 0 ? (
            <div style={{ color: text.hint, fontSize: 13, fontStyle: "italic" }}>
              Type your question to get started.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} />
              ))}
              {isSubmitting && (
                <div style={{
                  padding: "8px 12px",
                  fontSize: 11,
                  color: withGlow(palette.amber, 0.4),
                  fontFamily: "'IBM Plex Mono', monospace"
                }}>
                  Processing...
                </div>
              )}
              <div ref={scrollRef} />
            </div>
          )}
        </div>
      </div>

      {/* Graph visualization */}
      <div style={{ width: selectedNode ? "30%" : "45%", borderLeft: `1px solid ${border.default}`, transition: "width 0.2s" }}>
        <GraphCanvas
          entities={entities}
          relationships={relationships}
          ontology={ontology}
          highlightedEntities={highlightedEntities}
          onNodeClick={(node) => {
            setSelectedNode(selectedNode?.id === node.id ? null : node);
            setSelectedEntityId(null);
          }}
          activeFilter={null}
        />
      </div>
      {selectedNode && (
        <NodeDetailPanel
          node={selectedNode}
          relationships={relationships}
          entities={entities}
          ontology={ontology}
          propertyLabels={propertyLabels}
          onClose={() => setSelectedNode(null)}
          onNodeSelect={(node) => {
            setSelectedNode(node);
            setSelectedEntityId(null);
          }}
        />
      )}
    </div>
  );
}
