import { createColumnHelper } from "@tanstack/react-table";
import { ArrowRight, ArrowLeft } from "lucide-react";
import { Button } from "@chakra-ui/react";

/**
 * Node relationship data structure for the relationships table
 * Represents a single relationship with direction and label
 */
export type NodeRelationship = {
  relationship: string; // Human-readable relationship name (label)
  direction: "incoming" | "outgoing"; // Direction of the relationship
  uri?: string; // Original relationship URI (optional, for reference)
  onRelationshipClick?: (uri: string) => void; // Click handler for relationships
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<NodeRelationship>();

/**
 * Column definitions for the node relationships table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // Relationship column - displays the relationship with directional arrow as clickable button
  columnHelper.accessor("relationship", {
    header: "Relationship",
    cell: (info) => {
      const direction = info.row.original.direction;
      const relationship = info.getValue();
      const uri = info.row.original.uri;
      const onRelationshipClick = info.row.original.onRelationshipClick;

      // Determine theme variant based on direction
      const variant = direction === "outgoing" ? "primary" : "warmBrand";

      return (
        <Button
          variant="ghost"
          colorPalette={variant}
          size="sm"
          onClick={() => onRelationshipClick?.(uri || "")}
          style={{
            justifyContent: "flex-start",
            padding: "0.25rem 0.5rem",
            height: "auto",
            minHeight: "1.5rem",
            fontWeight: "normal",
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
          >
            {direction === "incoming" && <ArrowLeft size={16} />}
            <span>{relationship}</span>
            {direction === "outgoing" && <ArrowRight size={16} />}
          </div>
        </Button>
      );
    },
  }),
];
