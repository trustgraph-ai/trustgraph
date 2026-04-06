import React, { useCallback, useMemo, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Button,
  Separator,
} from "@chakra-ui/react";
import { ArrowLeft } from "lucide-react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  ConnectionMode,
  Handle,
  Position,
} from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";
import { useFlowClasses } from "@trustgraph/react-state";
import serviceMap from "../../data/service-map.json";

interface FlowClassEditorViewProps {
  flowClassId: string;
  onBack: () => void;
}

interface ProcessorInfo {
  [key: string]: unknown;
}

// Custom node component - use role for connections, direction for positioning
const CustomNode = ({
  data,
}: {
  data: {
    label: string;
    type?: string;
    provides?: string[];
    consumes?: string[];
    processorInfo?: ProcessorInfo;
  };
}) => {
  const borderColor = data.type === "class" ? "#2563eb" : "#16a34a"; // blue for class, green for flow
  const backgroundColor = data.type === "class" ? "#eff6ff" : "#f0fdf4";

  const provides = data.provides || [];
  const consumes = data.consumes || [];
  const processorInfo = data.processorInfo || { connections: [] };

  // Group connections by direction for positioning
  const leftConnections: string[] = [];
  const rightConnections: string[] = [];

  interface Connection {
    name: string;
    role: string;
    direction?: string;
  }

  // Add provides connections to left or right based on direction
  provides.forEach((connectionName) => {
    const conn = (processorInfo.connections as Connection[] | undefined)?.find(
      (c) => c.name === connectionName && c.role === "provides",
    );
    if (conn?.direction === "in") {
      leftConnections.push(connectionName);
    } else {
      rightConnections.push(connectionName);
    }
  });

  // Add consumes connections to left or right based on direction
  consumes.forEach((connectionName) => {
    const conn = (processorInfo.connections as Connection[] | undefined)?.find(
      (c) => c.name === connectionName && c.role === "consumes",
    );
    if (conn?.direction === "in") {
      leftConnections.push(connectionName);
    } else {
      rightConnections.push(connectionName);
    }
  });

  const nodeHeight = Math.max(
    50,
    Math.max(leftConnections.length, rightConnections.length) * 25 + 30,
  );

  return (
    <div
      style={{
        padding: "10px 20px",
        border: `2px solid ${borderColor}`,
        borderRadius: "6px",
        background: backgroundColor,
        fontSize: "14px",
        fontWeight: "500",
        position: "relative",
        minWidth: "150px",
        minHeight: `${nodeHeight}px`,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* LEFT side connections */}
      {leftConnections.map((connection, index) => {
        const conn = (
          processorInfo.connections as Connection[] | undefined
        )?.find((c) => c.name === connection);
        const isProvides = conn?.role === "provides";
        return (
          <React.Fragment
            key={`${isProvides ? "provide" : "consume"}-${connection}`}
          >
            <Handle
              type="target"
              position={Position.Left}
              id={`${isProvides ? "provide" : "consume"}-${connection}`}
              style={{
                background: isProvides ? "#16a34a" : "#dc2626",
                top: `${((index + 1) / (leftConnections.length + 1)) * 100}%`,
              }}
            />
            <div
              style={{
                position: "absolute",
                right: `calc(100% + 15px)`,
                top: `calc(${((index + 1) / (leftConnections.length + 1)) * 100}% - 8px)`,
                transform: "translateY(-50%)",
                fontSize: "9px",
                color: isProvides ? "#16a34a" : "#dc2626",
                fontWeight: "normal",
                whiteSpace: "nowrap",
                textAlign: "right",
              }}
            >
              {connection}
            </div>
          </React.Fragment>
        );
      })}

      {/* RIGHT side connections */}
      {rightConnections.map((connection, index) => {
        const conn = (
          processorInfo.connections as Connection[] | undefined
        )?.find((c) => c.name === connection);
        const isProvides = conn?.role === "provides";
        return (
          <React.Fragment
            key={`${isProvides ? "provide" : "consume"}-${connection}`}
          >
            <Handle
              type="source"
              position={Position.Right}
              id={`${isProvides ? "provide" : "consume"}-${connection}`}
              style={{
                background: isProvides ? "#16a34a" : "#dc2626",
                top: `${((index + 1) / (rightConnections.length + 1)) * 100}%`,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: `calc(100% + 15px)`,
                top: `calc(${((index + 1) / (rightConnections.length + 1)) * 100}% - 8px)`,
                transform: "translateY(-50%)",
                fontSize: "9px",
                color: isProvides ? "#16a34a" : "#dc2626",
                fontWeight: "normal",
                whiteSpace: "nowrap",
                textAlign: "left",
              }}
            >
              {connection}
            </div>
          </React.Fragment>
        );
      })}

      <div style={{ fontSize: "12px", fontWeight: "600" }}>{data.label}</div>
      {data.type && (
        <div
          style={{
            fontSize: "10px",
            color: borderColor,
            fontWeight: "normal",
            marginTop: "2px",
          }}
        >
          {data.type}
        </div>
      )}
    </div>
  );
};

// Interface node component - visually distinct from processors
const InterfaceNode = ({
  data,
}: {
  data: {
    label: string;
    interfaceKind?: string;
    description?: string;
    visible?: boolean;
    queues?: Record<string, unknown>;
  };
}) => {
  const borderColor = data.interfaceKind === "service" ? "#8b5cf6" : "#ec4899"; // purple for service, pink for flow
  const backgroundColor =
    data.interfaceKind === "service" ? "#f3e8ff" : "#fce7f3";
  const icon = data.interfaceKind === "service" ? "⚡" : "📦";

  return (
    <div
      style={{
        padding: "12px 20px",
        border: `2px dashed ${borderColor}`,
        borderRadius: "12px",
        background: backgroundColor,
        fontSize: "14px",
        fontWeight: "500",
        minWidth: "180px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "4px",
        boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
        position: "relative",
      }}
    >
      {/* Connection handle on the right side */}
      <Handle
        type="source"
        position={Position.Right}
        id={`interface-${data.label}`}
        style={{
          background: borderColor,
          width: "12px",
          height: "12px",
          border: "2px solid white",
          right: "-6px",
        }}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontSize: "16px",
          fontWeight: "600",
        }}
      >
        <span>{icon}</span>
        <span>{data.label}</span>
      </div>
      {data.description && (
        <div
          style={{
            fontSize: "11px",
            color: "#6b7280",
            fontStyle: "italic",
            textAlign: "center",
            maxWidth: "200px",
          }}
        >
          {data.description}
        </div>
      )}
      <div
        style={{
          fontSize: "10px",
          color: borderColor,
          fontWeight: "bold",
          textTransform: "uppercase",
          marginTop: "4px",
        }}
      >
        {data.interfaceKind} interface
      </div>
    </div>
  );
};

// Register custom node types
const nodeTypes = {
  custom: CustomNode,
  interface: InterfaceNode,
};

interface FlowClass {
  class?: Record<string, unknown>;
  flow?: Record<string, unknown>;
}

// Generate nodes from flow class processors
const generateNodesFromFlowClass = (flowClass: FlowClass): Node[] => {
  const nodes: Node[] = [];

  // Add class processors
  Object.keys(flowClass.class || {}).forEach((processorName) => {
    // Strip template suffix to get base processor name for service map lookup
    const baseProcessorName = processorName.replace(/:\{[^}]+\}$/, "");

    // Get connection info from service map - use role for connections, direction for positioning
    const processorInfo = serviceMap.processors[baseProcessorName] || {
      connections: [],
    };
    const provides =
      processorInfo.connections
        ?.filter((conn) => conn.role === "provides")
        .map((conn) => conn.name) || [];
    const consumes =
      processorInfo.connections
        ?.filter((conn) => conn.role === "consumes")
        .map((conn) => conn.name) || [];

    nodes.push({
      id: `class-${processorName}`,
      position: { x: 0, y: 0 }, // Will be calculated by dagre
      data: {
        label: processorName,
        type: "class",
        provides: provides,
        consumes: consumes,
        processorInfo: processorInfo, // Pass full processor info for direction lookup
      },
      type: "custom",
    });
  });

  // Add flow processors
  Object.keys(flowClass.flow || {}).forEach((processorName) => {
    // Strip template suffix to get base processor name for service map lookup
    const baseProcessorName = processorName.replace(/:\{[^}]+\}$/, "");

    // Get connection info from service map - use role for connections, direction for positioning
    const processorInfo = serviceMap.processors[baseProcessorName] || {
      connections: [],
    };
    const provides =
      processorInfo.connections
        ?.filter((conn) => conn.role === "provides")
        .map((conn) => conn.name) || [];
    const consumes =
      processorInfo.connections
        ?.filter((conn) => conn.role === "consumes")
        .map((conn) => conn.name) || [];

    nodes.push({
      id: `flow-${processorName}`,
      position: { x: 0, y: 0 }, // Will be calculated by dagre
      data: {
        label: processorName,
        type: "flow",
        provides: provides,
        consumes: consumes,
        processorInfo: processorInfo, // Pass full processor info for direction lookup
      },
      type: "custom",
    });
  });

  // Add interface nodes
  Object.entries(flowClass.interfaces || {}).forEach(
    ([interfaceName, interfaceQueues]) => {
      // Look up interface definition in service map
      const interfaceDefinition = serviceMap.interfaces?.[interfaceName];

      nodes.push({
        id: `interface-${interfaceName}`,
        position: { x: 0, y: 0 }, // Will be calculated by dagre
        data: {
          label: interfaceName,
          type: "interface",
          interfaceKind: interfaceDefinition?.kind || "unknown",
          description: interfaceDefinition?.description || "",
          visible: interfaceDefinition?.visible,
          queues: interfaceQueues,
        },
        type: "interface", // Use a different node type for interfaces
      });
    },
  );

  return nodes;
};

// Apply dagre layout to nodes and edges for better positioning
const applyDagreLayout = (nodes: Node[], edges: Edge[]): Node[] => {
  const nodeWidth = 200;
  const nodeHeight = 120; // Increased for interface nodes

  // Create a new directed graph
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({
    rankdir: "LR", // Left to right layout
    nodesep: 80, // Increased horizontal spacing between nodes
    ranksep: 500, // Extra 50% left-right spacing between ranks
    marginx: 40, // Increased margins
    marginy: 40,
    align: "UL", // Align ranks upward-left for better interface positioning
    acyclicer: "greedy", // Better cycle removal
    ranker: "tight-tree", // Better ranking algorithm
  });

  // Add nodes to dagre graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  // Add edges to dagre graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate the layout
  dagre.layout(dagreGraph);

  // Apply the calculated positions back to the nodes
  return nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });
};

// Generate edges from flow class connections using three-way matching algorithm
const generateEdgesFromFlowClass = (flowClass: FlowClass): Edge[] => {
  const edges: Edge[] = [];
  let edgeIndex = 0;

  // Build maps of providers and consumers by connection type
  const providersByType = new Map<
    string,
    Array<{
      processorId: string;
      processorName: string;
      connectionName: string;
      queues: Record<string, unknown>;
    }>
  >();
  const consumersByType = new Map<
    string,
    Array<{
      processorId: string;
      processorName: string;
      connectionName: string;
      queues: Record<string, unknown>;
    }>
  >();

  // Collect all processors and their connections from service map + flow class queues
  const allProcessors = [
    ...Object.keys(flowClass.class || {}).map((name) => ({
      name,
      type: "class",
      baseProcessorName: name.replace(/:\{[^}]+\}$/, ""),
      flowClassConnections: flowClass.class[name],
    })),
    ...Object.keys(flowClass.flow || {}).map((name) => ({
      name,
      type: "flow",
      baseProcessorName: name.replace(/:\{[^}]+\}$/, ""),
      flowClassConnections: flowClass.flow[name],
    })),
  ];

  allProcessors.forEach(
    ({ name, type, baseProcessorName, flowClassConnections }) => {
      const processorInfo = serviceMap.processors[baseProcessorName];
      if (!processorInfo?.connections) return;

      const processorId = `${type}-${name}`;

      processorInfo.connections.forEach((connection) => {
        const connectionType = connection.type;
        const connectionKind =
          serviceMap.connection_types[connectionType]?.kind;

        // Extract queues based on connection kind
        let queues: Record<string, unknown> = {};

        if (connectionKind === "service") {
          // For service: look for {connection.name}-request and {connection.name}-response for consumers
          // For providers: look for request and response
          if (connection.role === "provides") {
            queues = {
              request: flowClassConnections.request,
              response: flowClassConnections.response,
            };
          } else if (connection.role === "consumes") {
            queues = {
              request: flowClassConnections[`${connection.name}-request`],
              response: flowClassConnections[`${connection.name}-response`],
            };
          }
        } else if (connectionKind === "flow") {
          // For flow: single queue value at connection.name
          queues = { value: flowClassConnections[connection.name] };
        } else if (connectionKind === "passive") {
          // For passive: both consumer and provider use single queue value
          queues = { value: flowClassConnections[connection.name] };
        }

        // Only add if we found valid queues
        if (Object.values(queues).some((q) => q !== undefined)) {
          if (connection.role === "provides") {
            if (!providersByType.has(connectionType)) {
              providersByType.set(connectionType, []);
            }
            providersByType.get(connectionType)!.push({
              processorId,
              processorName: name,
              connectionName: connection.name,
              queues,
            });
          } else if (connection.role === "consumes") {
            if (!consumersByType.has(connectionType)) {
              consumersByType.set(connectionType, []);
            }
            consumersByType.get(connectionType)!.push({
              processorId,
              processorName: name,
              connectionName: connection.name,
              queues,
            });
          }
        }
      });
    },
  );

  // Create edges by matching providers and consumers using the three algorithms
  consumersByType.forEach((consumers, connectionType) => {
    const providers = providersByType.get(connectionType) || [];
    const connectionKind = serviceMap.connection_types[connectionType]?.kind;

    if (connectionKind === "passive") {
      // Passive connections - no special handling needed
    }

    consumers.forEach((consumer) => {
      providers.forEach((provider) => {
        // Skip self-connections
        if (consumer.processorId === provider.processorId) return;

        let isMatch = false;

        if (connectionKind === "service") {
          // Service: consumer's {connection-name}-request/response = provider's request/response
          isMatch =
            consumer.queues.request === provider.queues.request &&
            consumer.queues.response === provider.queues.response;
        } else if (connectionKind === "flow") {
          // Flow: same queue value
          isMatch = consumer.queues.value === provider.queues.value;
        } else if (connectionKind === "passive") {
          // Passive: consumer's single queue = provider's single queue
          isMatch = consumer.queues.value === provider.queues.value;
        }

        if (isMatch) {
          // Determine edge styling
          let edgeColor = "#666666";
          if (connectionKind === "service") edgeColor = "#2563eb";
          else if (connectionKind === "flow") edgeColor = "#16a34a";
          else if (connectionKind === "passive") edgeColor = "#dc2626";

          // For logical flow direction (consumer requests → provider responds):
          // Use correct logical direction for both animation and layout
          edges.push({
            id: `edge-${edgeIndex++}`,
            source: consumer.processorId, // Logical source (consumer makes request)
            target: provider.processorId, // Logical target (provider receives request)
            sourceHandle: `consume-${consumer.connectionName}`, // Consumer's outgoing handle
            targetHandle: `provide-${provider.connectionName}`, // Provider's incoming handle
            animated: connectionKind === "service",
            style: {
              stroke: edgeColor,
              strokeWidth: connectionKind === "passive" ? 1 : 2,
            },
            label: connectionType,
            type: connectionKind === "passive" ? "step" : "default",
          });
        }
      });
    });
  });

  // Connect interfaces to their implementing processors

  Object.entries(flowClass.interfaces || {}).forEach(
    ([interfaceName, interfaceQueues]) => {
      const interfaceDefinition = serviceMap.interfaces?.[interfaceName];
      const interfaceKind = interfaceDefinition?.kind;

      if (!interfaceKind) {
        return;
      }

      // Find processors that match this interface's queue pattern
      allProcessors.forEach(
        ({ name, type, baseProcessorName, flowClassConnections }) => {
          const processorId = `${type}-${name}`;
          const processorInfo = serviceMap.processors[baseProcessorName];
          if (!processorInfo?.connections) return;

          let isMatch = false;
          let matchingConnection: Connection | null = null;

          if (interfaceKind === "service") {
            // For service interfaces: check if processor PROVIDES this service
            const interfaceRequest = (
              interfaceQueues as Record<string, unknown>
            ).request;
            const interfaceResponse = (
              interfaceQueues as Record<string, unknown>
            ).response;

            // Check if this processor provides this service
            if (
              flowClassConnections.request === interfaceRequest &&
              flowClassConnections.response === interfaceResponse
            ) {
              // Find the service connection that provides
              matchingConnection = processorInfo.connections.find(
                (c) => c.role === "provides" && c.name === "service",
              );
              if (matchingConnection) {
                isMatch = true;
              }
            }
          } else if (interfaceKind === "flow") {
            // For flow interfaces: check if processor PROVIDES this flow
            const interfaceQueue = interfaceQueues as string;

            // Check only provider connections for matching queue
            processorInfo.connections.forEach((connection) => {
              if (connection.role === "provides") {
                const connectionQueue = flowClassConnections[connection.name];
                if (connectionQueue === interfaceQueue) {
                  matchingConnection = connection;
                  isMatch = true;
                }
              }
            });
          }

          if (isMatch && matchingConnection) {
            // Create edge from interface to processor
            const edgeColor =
              interfaceKind === "service" ? "#8b5cf6" : "#ec4899";

            edges.push({
              id: `interface-edge-${edgeIndex++}`,
              source: `interface-${interfaceName}`,
              target: processorId,
              sourceHandle: `interface-${interfaceName}`,
              targetHandle:
                matchingConnection.role === "provides"
                  ? `provide-${matchingConnection.name}`
                  : `consume-${matchingConnection.name}`,
              animated: true,
              style: {
                stroke: edgeColor,
                strokeWidth: 2,
                strokeDasharray: "5,5",
              },
              label: `implements ${interfaceName}`,
              type: "default",
            });
          }
        },
      );
    },
  );

  return edges;
};

export const FlowClassEditorView: React.FC<FlowClassEditorViewProps> = ({
  flowClassId,
  onBack,
}) => {
  const { flowClasses } = useFlowClasses();
  const flowClass = flowClasses.find((fc) => fc.id === flowClassId);

  // Generate nodes and edges from flow class data using useMemo - must be before early return
  const initialNodes = useMemo(() => {
    if (!flowClass) return [];
    const nodes = generateNodesFromFlowClass(flowClass);
    return nodes;
  }, [flowClass]);

  const generatedEdges = useMemo(() => {
    if (!flowClass) return [];
    const edges = generateEdgesFromFlowClass(flowClass);
    return edges;
  }, [flowClass]);

  const layoutedNodes = useMemo(() => {
    const layouted = applyDagreLayout(initialNodes, generatedEdges);
    return layouted;
  }, [initialNodes, generatedEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Update nodes and edges when the data changes
  useEffect(() => {
    setNodes(layoutedNodes);
  }, [layoutedNodes, setNodes]);

  useEffect(() => {
    setEdges(generatedEdges);
  }, [generatedEdges, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  if (!flowClass) {
    return (
      <Box p={6}>
        <HStack spacing={4} mb={4}>
          <Button
            onClick={onBack}
            leftIcon={<ArrowLeft size={16} />}
            variant="ghost"
          >
            Back to Flow Classes
          </Button>
        </HStack>
        <Text>Flow class not found.</Text>
      </Box>
    );
  }

  return (
    <Box h="100vh" display="flex" flexDirection="column">
      {/* Header */}
      <VStack
        spacing={4}
        p={6}
        bg="white"
        borderBottom="1px"
        borderColor="gray.200"
      >
        <HStack justifyContent="space-between" w="100%">
          <HStack spacing={4}>
            <Button
              onClick={onBack}
              leftIcon={<ArrowLeft size={16} />}
              variant="ghost"
            >
              Back to Flow Classes
            </Button>
          </HStack>
          <HStack spacing={4}>
            {/*
            <Button leftIcon={<FileCode size={16} />} variant="outline" size="sm">
              Export
            </Button>
            <Button leftIcon={<Construction size={16} />} variant="outline" size="sm">
              Build
            </Button>
*/}
          </HStack>
        </HStack>

        <VStack spacing={2} align="start" w="100%">
          <Heading size="lg">{flowClass.name}</Heading>
        </VStack>

        <Separator />
      </VStack>

      {/* ReactFlow Canvas */}
      <Box flex={1} position="relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          attributionPosition="bottom-left"
        >
          <Background />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              return node.data?.type === "class" ? "#2563eb" : "#16a34a";
            }}
            position="top-right"
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.8)",
            }}
          />
        </ReactFlow>
      </Box>
    </Box>
  );
};
