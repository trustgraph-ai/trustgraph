import type { DomainKey, Entity, OntologyDomain } from "../types";
import { GraphCanvasSVG as GraphCanvas, NodeDetailPanel, LoadingState, FilterBar } from "../components";
import type { FilterItem } from "../components";
import { useGraphData } from "../state";

interface GraphViewProps {
  activeFilter: DomainKey | null;
  onFilterChange: (filter: DomainKey | null) => void;
  selectedNode: Entity | null;
  onNodeSelect: (node: Entity | null) => void;
}

export function GraphView({ activeFilter, onFilterChange, selectedNode, onNodeSelect }: GraphViewProps) {
  const { entities, relationships, ontology, propertyLabels, isLoading, isError } = useGraphData();

  const highlightedEntities = selectedNode
    ? [selectedNode.id, ...relationships.filter(r => r.from === selectedNode.id || r.to === selectedNode.id).map(r => r.from === selectedNode.id ? r.to : r.from)]
    : [];

  // Compute relevant filter domains based on selected node's connections
  const relevantDomains = selectedNode
    ? (() => {
        const domains = new Set<DomainKey>([selectedNode.domain]);
        const connectedIds = relationships
          .filter(r => r.from === selectedNode.id || r.to === selectedNode.id)
          .map(r => r.from === selectedNode.id ? r.to : r.from);
        for (const id of connectedIds) {
          const entity = entities.find(e => e.id === id);
          if (entity) domains.add(entity.domain);
        }
        return domains;
      })()
    : null;

  if (isLoading) {
    return <LoadingState message="Loading graph data..." />;
  }

  if (isError || !ontology) {
    return <LoadingState variant="error" message="Error loading graph data" />;
  }

  // Build filter items from relevant domains
  const filterItems: FilterItem[] = selectedNode
    ? (Object.entries(ontology) as [DomainKey, OntologyDomain][])
        .filter(([key]) => relevantDomains?.has(key))
        .slice(0, 10)
        .map(([key, data]) => ({
          key,
          label: data.label,
          icon: data.icon,
          color: data.color,
        }))
    : [];

  return (
    <>
      {/* Domain Filter Bar */}
      <FilterBar
        items={filterItems}
        selectedKey={activeFilter}
        onSelect={(key) => onFilterChange(key as DomainKey | null)}
        stats={`${entities.length} entities · ${relationships.length} relationships`}
        emptyMessage={selectedNode ? undefined : "Select a node to filter"}
      />

      {/* Main Content */}
      <div style={{ display: "flex", height: "calc(100vh - 150px)" }}>
        <div style={{ flex: 1, minWidth: 0, position: "relative", overflow: "hidden" }}>
          <GraphCanvas
            entities={entities}
            relationships={relationships}
            ontology={ontology}
            highlightedEntities={highlightedEntities}
            onNodeClick={(node) => onNodeSelect(selectedNode?.id === node.id ? null : node)}
            activeFilter={activeFilter}
          />
        </div>
        {selectedNode && (
          <NodeDetailPanel
            node={selectedNode}
            relationships={relationships}
            entities={entities}
            ontology={ontology}
            propertyLabels={propertyLabels}
            onClose={() => onNodeSelect(null)}
            onNodeSelect={onNodeSelect}
          />
        )}
      </div>
    </>
  );
}
