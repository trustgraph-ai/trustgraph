import React, { useRef, useState, useEffect } from "react";

import { Box, Alert, Heading, HStack } from "@chakra-ui/react";

import { useResizeDetector } from "react-resize-detector";

import { ForceGraph3D } from "react-force-graph";
import SpriteText from "three-spritetext";

import {
  useBorderColor,
  useBackgroundColor,
  useNodeColor,
  useNodeTextColor,
  useSelectedNodeTextColor,
  useLinkColor,
  useLinkTextColor,
  useLinkParticleColor,
} from "../ui/graph-colors";

import {
  useSessionStore,
  useWorkbenchStateStore,
  useGraphSubgraph,
  useSettings,
} from "@trustgraph/react-state";
import GraphHelp from "./GraphHelp";
import NodeDetailsDrawer from "./NodeDetailsDrawer";

const GraphView = () => {
  const flowId = useSessionStore((state) => state.flowId);
  const selected = useWorkbenchStateStore((state) => state.selected);
  const { settings } = useSettings();

  const fgRef = useRef();
  const { width, height, ref } = useResizeDetector({});

  // State to track the selected node
  const [selectedNode, setSelectedNode] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const borderColor = useBorderColor();
  const backgroundColor = useBackgroundColor();
  const nodeColor = useNodeColor();
  const nodeTextColor = useNodeTextColor();
  const selectedNodeTextColor = useSelectedNodeTextColor();
  const linkColor = useLinkColor();
  const linkTextColor = useLinkTextColor();
  const linkParticleColor = useLinkParticleColor();

  // Use the new Tanstack Query hook for graph data
  const { view, isLoading, isError, navigateByRelationship } =
    useGraphSubgraph(selected?.uri, flowId, settings?.collection || "default");

  // Ensure drawer opens when node is selected
  useEffect(() => {
    if (selectedNode && !isDrawerOpen) {
      setIsDrawerOpen(true);
    }
  }, [selectedNode, isDrawerOpen]);

  if (!selected) {
    return (
      <Box>
        <Alert.Root status="info" variant="outline">
          <Alert.Indicator />
          <Alert.Title>
            No data to view. Try Chat or Search to find data.
          </Alert.Title>
        </Alert.Root>
      </Box>
    );
  }

  if (isLoading || !view)
    return (
      <Box>
        <Alert.Root status="info" variant="outline">
          <Alert.Indicator />
          <Alert.Title>
            {isLoading
              ? "Building subgraph..."
              : "No data to view. Try Chat or Search to find data."}
          </Alert.Title>
        </Alert.Root>
      </Box>
    );

  if (isError)
    return (
      <Box>
        <Alert.Root status="error" variant="outline">
          <Alert.Indicator />
          <Alert.Title>Error loading graph data.</Alert.Title>
        </Alert.Root>
      </Box>
    );

  const wrap = (s: string, w: number) =>
    s.replace(
      new RegExp(`(?![^\\n]{1,${w}}$)([^\\n]{1,${w}})\\s`, "g"),
      "$1\n",
    );

  const nodeClick = (node) => {
    // Set the selected node in state
    setSelectedNode(node);

    // Log the node ID and label when a node is clicked
    console.log("Node selected:", node.id, "Label:", node.label);

    // For now, commenting out the navigation to focus on selection
    // updateSubgraphMutation({ nodeId: node.id, currentGraph: view });
  };

  const handleCloseDrawer = () => {
    // Close drawer and unselect the node
    setIsDrawerOpen(false);
    setSelectedNode(null);
  };

  const handleRelationshipClick = (
    relationshipUri: string,
    direction: "incoming" | "outgoing",
  ) => {
    if (!selectedNode || !view) {
      console.warn("No selected node or graph view available");
      return;
    }

    console.log(
      `Following ${direction} relationship:`,
      relationshipUri,
      "from node:",
      selectedNode.id,
    );

    navigateByRelationship({
      selectedNodeId: selectedNode.id,
      relationshipUri,
      direction,
      currentGraph: view,
    });
  };

  return (
    <>
      <HStack mb={8}>
        <Heading variant="h5" component="div" sx={{ m: 0, p: 0 }}>
          {selected.label}
        </Heading>

        <GraphHelp />
      </HStack>

      <Box
        ref={ref}
        border="1px solid"
        borderColor={borderColor}
        width="calc(100% - 0.5rem)"
        height="calc(100% - 11rem)"
      >
        <ForceGraph3D
          width={width}
          height={height}
          graphData={view}
          nodeOpacity={0.8}
          nodeLabel="label"
          enableNodeDrag={true}
          nodeColor={nodeColor}
          backgroundColor={backgroundColor}
          nodeThreeObject={(node) => {
            const sprite = new SpriteText(wrap(node.label, 30));
            sprite.color =
              selectedNode?.id === node.id
                ? selectedNodeTextColor
                : nodeTextColor;
            sprite.textHeight = 4;
            return sprite;
          }}
          onNodeClick={nodeClick}
          onBackgroundClick={() => {
            console.log("Background clicked - deselecting node");
            setSelectedNode(null);
            setIsDrawerOpen(false);
          }}
          onNodeDragEnd={(node) => {
            node.fx = node.x;
            node.fy = node.y;
            node.fz = node.z;
          }}
          linkDirectionalArrowLength={2.5}
          linkDirectionalArrowRelPos={0.75}
          linkOpacity={0.6}
          linkColor={() => linkColor}
          linkWidth="2"
          linkThreeObjectExtend={true}
          linkThreeObject={(link) => {
            const sprite = new SpriteText(wrap(link.label, 30));
            sprite.color = linkTextColor;
            sprite.textHeight = 2.0;
            return sprite;
          }}
          linkPositionUpdate={(sprite, { start, end }) => {
            const middlePos = {
              x: start.x + (end.x - start.x) / 2,
              y: start.y + (end.y - start.y) / 2,
              z: start.z + (end.z - start.z) / 2,
            };
            Object.assign(sprite.position, middlePos);
          }}
          ref={fgRef}
          linkDirectionalParticleColor={() => linkParticleColor}
          linkDirectionalParticleWidth={1.4}
          linkHoverPrecision={2}
          onLinkClick={(link) => {
            if (fgRef.current != undefined) fgRef.current.emitParticle(link);
          }}
        />
      </Box>

      <NodeDetailsDrawer
        node={selectedNode}
        isOpen={isDrawerOpen}
        onClose={handleCloseDrawer}
        onRelationshipClick={handleRelationshipClick}
      />
    </>
  );
};

export default GraphView;
