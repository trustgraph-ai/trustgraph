# Flow Class Visual Editor Technical Specification

## Overview

A React-based visual editor for creating and modifying TrustGraph flow class definitions using a node-and-edge graph interface. Built with React Flow, this component allows users to visually design dataflow patterns by dragging processors onto a canvas and connecting them with queues.

## Core Technologies

- **React Flow** - Node-based editor framework
- **TypeScript** - Type safety for flow definitions
- **Chakra UI v3** - UI components and theming
- **Zustand** - Editor state management
- **Zod** - Schema validation for flow class structure

## Component Architecture

### Directory Structure
```
src/components/flow-editor/
├── FlowClassEditor.tsx           # Main editor component
├── nodes/                         # Custom node components
│   ├── ClassProcessorNode.tsx    # Shared service nodes
│   ├── FlowProcessorNode.tsx     # Flow-specific nodes
│   └── InterfaceNode.tsx         # Entry/exit point nodes
├── edges/                         # Custom edge components
│   ├── PersistentQueueEdge.tsx   # Persistent queue connections
│   └── RequestResponseEdge.tsx   # Request/response pairs
├── panels/                        # Editor UI panels
│   ├── NodePalette.tsx           # Drag-and-drop processor library
│   ├── PropertiesPanel.tsx       # Node/edge configuration
│   └── ValidationPanel.tsx       # Real-time validation feedback
├── hooks/
│   ├── useFlowValidation.ts      # Validation logic
│   ├── useFlowExport.ts          # JSON export/import
│   └── useAutoLayout.ts          # Automatic graph layout
└── types/
    └── flowEditorTypes.ts        # TypeScript definitions
```

## Visual Design

### Node Types

#### 1. Class Processor Node ({class})
```tsx
{
  type: 'classProcessor',
  data: {
    processorName: string,      // e.g., "embeddings"
    queues: {
      request?: string,          // Queue pattern
      response?: string,         // Queue pattern
      [key: string]: string      // Additional queues
    }
  },
  style: {
    background: 'accent.subtle', // Shared service color
    border: '2px solid accent.solid',
    icon: <Share2 />            // Lucide icon indicating shared
  }
}
```

#### 2. Flow Processor Node ({id})
```tsx
{
  type: 'flowProcessor',
  data: {
    processorName: string,       // e.g., "chunker"
    queues: {
      input?: string,            // Input queue
      output?: string,           // Output queue
      [key: string]: string      // Additional queues
    }
  },
  style: {
    background: 'primary.subtle', // Flow-specific color
    border: '2px solid primary.solid',
    icon: <Box />                // Lucide icon for isolated
  }
}
```

#### 3. Interface Node
```tsx
{
  type: 'interfaceNode',
  data: {
    interfaceName: string,       // e.g., "document-load"
    interfaceType: 'fire-and-forget' | 'request-response',
    queuePattern?: string,       // For fire-and-forget
    request?: string,            // For request-response
    response?: string            // For request-response
  },
  style: {
    background: 'bg.muted',
    border: '2px dashed border.muted',
    icon: <Plug />               // Entry/exit point indicator
  }
}
```

### Edge Types

#### 1. Persistent Queue Edge
- **Visual**: Solid line with arrow
- **Color**: Based on namespace (flow: green, request: blue, response: purple)
- **Label**: Queue name displayed on hover
- **Validation**: Source/target compatibility checking

#### 2. Non-Persistent Queue Edge  
- **Visual**: Dashed line with arrow
- **Color**: Lighter variant of namespace colors
- **Label**: Queue name with non-persistent indicator
- **Validation**: Request/response pairing validation

## User Edit Operations

### 1. Processor Management

#### Add Processor
- **Drag from palette**: Drag processor type from categorized library
- **Double-click canvas**: Quick-add with processor type selector
- **Context menu**: Right-click → Add Processor → Select type
- **Keyboard shortcut**: `A` key opens add processor dialog

#### Configure Processor
- **Rename**: Click processor name to edit inline
- **Change type**: Toggle between `{class}` and `{id}` via properties panel
- **Queue management**:
  ```tsx
  // Add new queue to processor
  addQueue(processorId, {
    name: "custom-queue",
    direction: "input" | "output" | "bidirectional",
    pattern: "persistent://tg/flow/custom:{id}"
  });
  
  // Remove queue
  removeQueue(processorId, queueName);
  
  // Edit queue pattern
  updateQueue(processorId, queueName, newPattern);
  ```

#### Delete Processor
- **Single**: Select + Delete key
- **Multiple**: Multi-select + Delete key
- **Context menu**: Right-click → Delete
- **Validation**: Warn if processor has connections

### 2. Connection Management

#### Create Connection
- **Drag connection**: From output handle to input handle
- **Validation rules**:
  - Persistence compatibility (persistent ↔ persistent preferred)
  - Namespace compatibility (flow/request/response)
  - Template variable consistency ({class} ↔ {class}, {id} ↔ {id})
  - No self-connections
  - No duplicate connections

#### Configure Connection
- **Auto-naming**: Generate queue name from source/target processors
- **Custom naming**: Override auto-generated queue name
- **Persistence mode**: Toggle persistent/non-persistent
- **Queue pattern template**:
  ```tsx
  generateQueuePattern({
    persistence: "persistent" | "non-persistent",
    tenant: "tg",
    namespace: "flow" | "request" | "response",
    topic: "document-embeddings",
    template: "{id}" | "{class}"
  });
  // Result: "persistent://tg/flow/document-embeddings:{id}"
  ```

#### Delete Connection
- **Click to select** + Delete key
- **Context menu** on edge
- **Disconnect handle**: Drag connection away from handle

### 3. Interface Operations

#### Add Interface
- **Entry points**: Document load, text input, etc.
- **Exit points**: Response outputs, storage endpoints
- **Service interfaces**: Request/response pairs

#### Configure Interface Type
```tsx
// Fire-and-forget pattern
interface FireAndForgetInterface {
  type: "fire-and-forget";
  queue: string;  // Single queue pattern
}

// Request/response pattern
interface RequestResponseInterface {
  type: "request-response";
  request: string;   // Request queue pattern
  response: string;  // Response queue pattern
}
```

### 4. Bulk Operations

#### Multi-select Actions
- **Box select**: Click and drag to select multiple nodes
- **Shift-click**: Add to selection
- **Cmd-click**: Toggle selection
- **Select all**: Cmd+A

#### Group Operations
- **Move together**: Drag any selected node moves all
- **Delete together**: Delete key removes all selected
- **Duplicate**: Cmd+D duplicates selection
- **Copy/paste**: Cmd+C/Cmd+V for cross-flow copying

### 5. Layout Operations

#### Auto-layout
```tsx
const layoutStrategies = {
  hierarchical: {
    direction: "LR" | "TB",  // Left-right or top-bottom
    nodeSpacing: 150,
    levelSpacing: 200
  },
  force: {
    strength: -1000,
    distance: 150
  },
  circular: {
    radius: 300,
    startAngle: 0
  }
};
```

#### Manual Arrangement
- **Snap to grid**: Optional grid snapping (toggle with G key)
- **Alignment tools**: Align selected nodes (top/bottom/left/right/center)
- **Distribution**: Distribute nodes evenly (horizontal/vertical)

### 6. Template Operations

#### Apply Template
```tsx
const templates = {
  "document-rag": {
    description: "Document processing with RAG",
    processors: [
      { type: "pdf-decoder", id: "{id}" },
      { type: "chunker", id: "{id}" },
      { type: "embeddings", id: "{class}" },
      { type: "de-write", id: "{id}" }
    ],
    connections: [
      { from: "pdf-decoder.output", to: "chunker.input" },
      { from: "chunker.output", to: "embeddings.input" },
      { from: "embeddings.output", to: "de-write.input" }
    ]
  }
};
```

#### Create Template
- Select nodes/edges → Right-click → "Save as template"
- Provide template name and description
- Template saved to library for reuse

### 7. Validation Operations

#### Real-time Validation
```tsx
interface ValidationRule {
  id: string;
  severity: "error" | "warning" | "info";
  check: (flowClass: FlowClass) => ValidationResult;
}

const validationRules = [
  {
    id: "no-orphans",
    severity: "warning",
    check: (flow) => findOrphanedNodes(flow)
  },
  {
    id: "queue-consistency",
    severity: "error",
    check: (flow) => validateQueuePatterns(flow)
  },
  {
    id: "template-consistency",
    severity: "error",
    check: (flow) => validateTemplateVariables(flow)
  }
];
```

#### Fix Suggestions
- **Auto-fix**: One-click fixes for common issues
- **Quick actions**: Context-aware suggestions
- **Validation overlay**: Visual indicators on invalid elements

### 8. History Management

#### Undo/Redo Stack
```tsx
interface HistoryAction {
  type: "add" | "delete" | "update" | "connect" | "disconnect";
  before: FlowState;
  after: FlowState;
  timestamp: number;
}

const historyStack: HistoryAction[] = [];
const redoStack: HistoryAction[] = [];

// Track all operations
const executeOperation = (operation: Operation) => {
  const before = getCurrentState();
  performOperation(operation);
  const after = getCurrentState();
  
  historyStack.push({
    type: operation.type,
    before,
    after,
    timestamp: Date.now()
  });
  
  redoStack.length = 0; // Clear redo on new operation
};
```

### 9. Import/Export Operations

#### Import Flow Class
- **From JSON file**: Upload or paste JSON
- **From Config API**: Select from existing flow classes
- **Validation**: Verify structure before import
- **Merge options**: Replace or merge with existing

#### Export Flow Class
- **To JSON**: Download as .json file
- **To Config API**: Save directly to backend
- **To clipboard**: Copy JSON for sharing
- **Format options**: Minified or pretty-printed

### 10. Metadata Operations

#### Edit Flow Properties
```tsx
interface FlowMetadata {
  id: string;           // Kebab-case identifier
  name: string;         // Human-readable name
  description: string;  // Detailed description
  tags: string[];       // Categorization tags
  version: string;      // Semantic version
  author: string;       // Creator identity
  created: Date;        // Creation timestamp
  modified: Date;       // Last modification
}
```

#### Tag Management
- **Add tags**: Type or select from existing
- **Remove tags**: Click X on tag chips
- **Tag suggestions**: Based on processors used
- **Tag categories**: System tags vs user tags

## Core Features

### 1. Auto-Layout
```tsx
const handleAutoLayout = () => {
  const layoutedElements = getLayoutedElements(nodes, edges, {
    direction: 'LR',  // Left to right
    nodeSpacing: 150,
    levelSpacing: 200,
    animate: true
  });
  setNodes(layoutedElements.nodes);
  setEdges(layoutedElements.edges);
};
```

### 2. Import/Export
```tsx
// Export to flow class JSON
const exportFlowClass = () => {
  const flowClass = {
    class: extractClassProcessors(nodes),
    flow: extractFlowProcessors(nodes),
    interfaces: extractInterfaces(nodes),
    description: metadata.description,
    tags: metadata.tags
  };
  return JSON.stringify(flowClass, null, 2);
};

// Import from JSON
const importFlowClass = (json: string) => {
  const flowClass = JSON.parse(json);
  const { nodes, edges } = convertToReactFlow(flowClass);
  setNodes(nodes);
  setEdges(edges);
};
```

### 3. Connection Validation
```tsx
const isValidConnection = (connection: Connection) => {
  const sourceNode = getNode(connection.source);
  const targetNode = getNode(connection.target);
  
  // Validate queue compatibility
  if (!areQueuesCompatible(sourceNode, targetNode)) {
    return false;
  }
  
  // Prevent circular dependencies
  if (createsCircularDependency(connection)) {
    return false;
  }
  
  return true;
};
```

### 4. Smart Templates
Pre-built flow patterns users can instantiate:
- **Document RAG Pipeline**: PDF → Chunker → Embeddings → Storage
- **Graph RAG Pipeline**: Knowledge extraction → Graph embeddings → Query
- **Simple Q&A**: Prompt → LLM → Response
- **Custom Template**: User-defined reusable patterns

## State Management

```tsx
interface FlowEditorState {
  // React Flow state
  nodes: Node[];
  edges: Edge[];
  
  // Editor state
  selectedElement: Node | Edge | null;
  validationErrors: ValidationError[];
  isDirty: boolean;
  
  // Metadata
  flowClassName: string;
  description: string;
  tags: string[];
  
  // Actions
  addNode: (type: NodeType, position: XYPosition) => void;
  updateNode: (nodeId: string, data: NodeData) => void;
  deleteNode: (nodeId: string) => void;
  addEdge: (edge: Edge) => void;
  deleteEdge: (edgeId: string) => void;
  validateFlow: () => ValidationResult;
  exportFlow: () => FlowClassDefinition;
  importFlow: (definition: FlowClassDefinition) => void;
}
```

## Visual Indicators

### Node States
- **Normal**: Default appearance
- **Selected**: Blue glow/border
- **Invalid**: Red border with error icon
- **Connecting**: Pulse animation on handles
- **Hover**: Slight scale increase

### Edge States
- **Normal**: Default appearance  
- **Selected**: Highlighted with thicker stroke
- **Invalid**: Red dashed line
- **Animated**: Flow animation for active connections

### Queue Handle Types
- **Input**: Left side of node, inward arrow
- **Output**: Right side of node, outward arrow
- **Bidirectional**: Both sides, for request/response

## Keyboard Shortcuts

- `Delete` - Delete selected elements
- `Cmd+Z` - Undo
- `Cmd+Shift+Z` - Redo
- `Cmd+S` - Save flow class
- `Cmd+O` - Open flow class
- `Cmd+E` - Export to JSON
- `Space` - Pan mode
- `Cmd+A` - Select all nodes
- `Cmd+D` - Duplicate selected nodes

## Integration Points

### Config API Integration

The flow class editor uses the existing Config API for all flow class operations:

#### State Management Hook
```tsx
// src/state/flow-classes.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSocket } from "./socket";

export const useFlowClasses = () => {
  const socket = useSocket();
  
  return useQuery({
    queryKey: ["flow-classes"],
    queryFn: async () => {
      const response = await socket.request({
        operation: "get-config",
        path: "flow-classes"
      });
      return response.configuration as FlowClassDefinition[];
    }
  });
};

export const useFlowClass = (flowClassId: string) => {
  const socket = useSocket();
  
  return useQuery({
    queryKey: ["flow-class", flowClassId],
    queryFn: async () => {
      const response = await socket.request({
        operation: "get-config",
        path: `flow-classes/${flowClassId}`
      });
      return response.configuration as FlowClassDefinition;
    }
  });
};

export const useUpdateFlowClass = () => {
  const socket = useSocket();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, flowClass }: { 
      id: string; 
      flowClass: FlowClassDefinition 
    }) => {
      return await socket.request({
        operation: "set-config",
        path: `flow-classes/${id}`,
        configuration: flowClass
      });
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries(["flow-class", variables.id]);
      queryClient.invalidateQueries(["flow-classes"]);
    }
  });
};

export const useDeleteFlowClass = () => {
  const socket = useSocket();
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      return await socket.request({
        operation: "delete-config",
        path: `flow-classes/${id}`
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries(["flow-classes"]);
    }
  });
};
```

#### Editor Component Integration
```tsx
// src/components/flow-editor/FlowClassEditor.tsx
import { useFlowClass, useUpdateFlowClass } from "../../state/flow-classes";
import { useActivity } from "../../state/activity";
import { useNotification } from "../../state/notify";

export const FlowClassEditor = ({ flowClassId }: { flowClassId?: string }) => {
  const notify = useNotification();
  
  // Load existing flow class if ID provided
  const { data: flowClass, isLoading } = useFlowClass(flowClassId);
  const updateMutation = useUpdateFlowClass();
  
  // Track loading state
  useActivity(isLoading, "Loading flow class");
  useActivity(updateMutation.isPending, "Saving flow class");
  
  // Initialize React Flow with loaded data
  useEffect(() => {
    if (flowClass) {
      const { nodes, edges } = convertFlowClassToReactFlow(flowClass);
      setNodes(nodes);
      setEdges(edges);
      setMetadata({
        description: flowClass.description,
        tags: flowClass.tags
      });
    }
  }, [flowClass]);
  
  // Save handler
  const handleSave = async () => {
    const flowClassData = exportFlowClass();
    
    try {
      await updateMutation.mutateAsync({
        id: flowClassId || generateFlowClassId(),
        flowClass: flowClassData
      });
      notify.success("Flow class saved successfully");
    } catch (error) {
      notify.error("Failed to save flow class");
    }
  };
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      // ... rest of React Flow config
    />
  );
};
```

#### Flow Class List Integration
```tsx
// src/components/flow-editor/FlowClassList.tsx
import { useFlowClasses, useDeleteFlowClass } from "../../state/flow-classes";

export const FlowClassList = () => {
  const { data: flowClasses, isLoading } = useFlowClasses();
  const deleteMutation = useDeleteFlowClass();
  
  useActivity(isLoading, "Loading flow classes");
  useActivity(deleteMutation.isPending, "Deleting flow class");
  
  return (
    <VStack>
      {flowClasses?.map(flowClass => (
        <Card key={flowClass.id}>
          <HStack>
            <Text>{flowClass.description}</Text>
            <Button onClick={() => openEditor(flowClass.id)}>
              Edit
            </Button>
            <Button onClick={() => deleteMutation.mutate(flowClass.id)}>
              Delete
            </Button>
          </HStack>
        </Card>
      ))}
    </VStack>
  );
};
```

#### Config API Request/Response Format
```typescript
// Request to get all flow classes
{
  operation: "get-config",
  path: "flow-classes"
}

// Response
{
  configuration: [
    {
      id: "document-rag-flow",
      class: { /* class processors */ },
      flow: { /* flow processors */ },
      interfaces: { /* interfaces */ },
      description: "Document RAG pipeline",
      tags: ["rag", "documents"]
    }
  ]
}

// Request to update flow class
{
  operation: "set-config",
  path: "flow-classes/document-rag-flow",
  configuration: {
    class: { /* updated class processors */ },
    flow: { /* updated flow processors */ },
    interfaces: { /* updated interfaces */ },
    description: "Updated description",
    tags: ["rag", "documents", "v2"]
  }
}
```

### Real-time Updates via WebSocket

The editor subscribes to configuration changes to handle external updates:

```tsx
useEffect(() => {
  const subscription = socket.subscribe(
    `config/flow-classes/${flowClassId}`,
    (update) => {
      // Handle external updates to the flow class
      if (update.source !== currentSessionId) {
        notify.warning("Flow class updated externally. Refreshing...");
        queryClient.invalidateQueries(["flow-class", flowClassId]);
      }
    }
  );
  
  return () => subscription.unsubscribe();
}, [flowClassId]);
```

### With Existing UI

#### Page Integration
The Flow Class Editor is a separate page in the workbench, controlled by a feature toggle:

```tsx
// src/components/settings/FeatureSwitchesSection.tsx
// Add to existing feature switches:
<HStack justify="space-between" align="center">
  <VStack gap={1} align="start">
    <Text fontWeight="medium">Flow Class Editor</Text>
    <HStack gap={2} align="center">
      <Text fontSize="sm" color="fg.muted">
        Enable the visual flow class editor for creating and modifying dataflow patterns
      </Text>
      <Tag.Root colorPalette="accent" size="sm">
        <Tag.Label>experimental</Tag.Label>
      </Tag.Root>
    </HStack>
  </VStack>
  <Switch.Root
    checked={flowClassEditor}
    onCheckedChange={(details) =>
      onFlowClassEditorChange(details.checked)
    }
  >
    <Switch.HiddenInput />
    <Switch.Control>
      <Switch.Thumb />
    </Switch.Control>
  </Switch.Root>
</HStack>
```

#### Sidebar Navigation
```tsx
// src/components/Sidebar.tsx
// Add conditional menu item based on feature switch:
{settings.featureSwitches.flowClassEditor && (
  <SidebarItem
    icon={<GitBranch />}
    label="Flow Class Editor"
    path="/flow-class-editor"
    isActive={location.pathname === "/flow-class-editor"}
  />
)}
```

#### Route Configuration
```tsx
// src/App.tsx
// Add route for the editor page:
{settings.featureSwitches.flowClassEditor && (
  <Route path="/flow-class-editor" element={<FlowClassEditorPage />} />
)}
```

#### Page Component
```tsx
// src/pages/FlowClassEditorPage.tsx
import React from "react";
import PageHeader from "../components/common/PageHeader";
import FlowClassEditor from "../components/flow-editor/FlowClassEditor";
import { GitBranch } from "lucide-react";

const FlowClassEditorPage: React.FC = () => {
  return (
    <>
      <PageHeader
        icon={<GitBranch />}
        title="Flow Class Editor"
        description="Visual editor for creating and modifying TrustGraph dataflow patterns"
      />
      <FlowClassEditor />
    </>
  );
};

export default FlowClassEditorPage;
```

#### Settings State Update
```tsx
// src/state/settings.ts
interface FeatureSwitches {
  ontologyEditor: boolean;
  submissions: boolean;
  agentTools: boolean;
  mcpTools: boolean;
  schemas: boolean;
  tokenCost: boolean;
  flowClasses: boolean;        // Existing flow classes management
  flowClassEditor: boolean;     // New visual editor
  structuredQuery: boolean;
}
```

#### Integration Features
- Uses consistent Chakra UI theming
- Integrates with notification system via `useNotification`
- Progress indicators via `useActivity`
- Follows existing Config API patterns
- Respects user's feature toggle preferences

## Responsive Design

### Desktop (Primary)
- Full editor with all panels visible
- Optimal canvas size for complex flows
- Properties panel as sidebar

### Tablet
- Collapsible panels to maximize canvas
- Touch-friendly node manipulation
- Simplified toolbar

### Mobile (View-only)
- Read-only flow visualization
- Pan and zoom only
- Export functionality retained

## Performance Considerations

### Optimizations
- **Virtualization** for large flows (100+ nodes)
- **Debounced validation** during editing
- **Memoized node/edge components**
- **Lazy loading** of processor templates
- **Web Workers** for layout calculations

### Limits
- Max 500 nodes per flow class
- Max 1000 edges per flow class
- Auto-layout for flows under 100 nodes
- Real-time validation for flows under 50 nodes

## Error Handling

### Validation Errors
- Inline error indicators on invalid nodes/edges
- Validation panel with detailed error list
- Prevent export/save when errors exist

### Runtime Errors
- Connection rejection with toast notification
- Import failure with detailed parsing errors
- Auto-save recovery for browser crashes

## Future Enhancements

### Phase 2
- **Processor library management** - Add custom processors
- **Collaborative editing** - Real-time multi-user support
- **Version control** - Flow class versioning and diff view
- **Simulation mode** - Visualize data flow through the graph

### Phase 3
- **AI assistance** - Suggest connections and optimizations
- **Performance profiling** - Visualize bottlenecks
- **Template marketplace** - Share flow patterns
- **Code generation** - Generate processor stubs from flow

## Testing Strategy

### Unit Tests
- Node/edge component rendering
- Validation logic
- Import/export transformations
- State management actions

### Integration Tests
- Full editor workflow
- Save/load operations
- Template instantiation
- Keyboard shortcuts

### E2E Tests
- Create flow from scratch
- Import and modify existing flow
- Export and validate JSON
- Deploy flow instance