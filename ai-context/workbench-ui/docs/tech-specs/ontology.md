# OWL Ontology Management UI Technical Specification

## Overview

This specification describes a user interface component for managing OWL ontologies within the existing TrustGraph system. The UI enables data architects to create, edit, and maintain formal ontologies with classes, properties, and complex relationships, supporting multiple concurrent ontologies stored as configuration items in the backend.

**Naming Convention**: This project uses kebab-case for all identifiers (configuration keys, API endpoints, module names, etc.) rather than snake_case.

The system supports four primary use cases:

1. **Ontology Creation and Management**: Create new ontologies and manage existing ones through a structured interface
2. **Class and Property Definition**: Define OWL classes, object properties, and datatype properties with domains and ranges
3. **Rich Metadata and Constraints**: Add labels, descriptions, cardinality constraints, and type specifications
4. **AI-Assisted Content Generation**: Optional wizard/getting started flow using LLM helpers to generate or enhance ontology content

## Goals

- **Class and Property Management**: Define and manage OWL classes with properties, domains, ranges, and type constraints
- **Rich Semantic Support**: Enable comprehensive editing of RDFS/OWL properties including labels, multi-language support, and formal constraints
- **Multi-Ontology Support**: Allow data architects to work with multiple ontologies simultaneously
- **AI-Enhanced Productivity**: Provide optional LLM assistance for content generation and ontology enhancement
- **Configuration Integration**: Seamlessly store and retrieve ontologies from the existing configuration backend
- **Data Architect Focus**: Design interfaces that expose technical details and provide precise control over ontology structure
- **Validation and Reasoning**: Ensure ontologies conform to OWL standards with consistency checking and inference support
- **Import/Export Capabilities**: Support standard formats (Turtle, RDF/XML, OWL/XML) for ontology interchange

## Background

TrustGraph currently stores configuration data in a flexible key-value system that can accommodate various data types. OWL ontologies represent formal knowledge models that need to be managed through dedicated tooling rather than raw configuration editing.

Data architects working with knowledge graphs need ontologies to:
- Define formal object types and their properties
- Specify property domains, ranges, and type constraints
- Enable logical reasoning and inference
- Support complex relationships and cardinality constraints
- Provide unique identifiers and external reference capabilities

Current limitations include:
- No dedicated UI for ontology management
- Manual editing of complex class and property definitions
- Difficulty maintaining OWL consistency
- No automated assistance for content generation
- Limited validation and reasoning capabilities

This specification addresses these gaps by providing a specialized interface that understands OWL/RDFS semantics while integrating with the existing configuration infrastructure.

## Technical Design

### Architecture

The taxonomy management UI requires the following components:

1. **Ontology Manager Component**
   - React-based interface component for the main ontology management workspace
   - Integrates with existing UI framework and design system
   - Provides tree view, detail panels, and editing interfaces
   - Supports undo/redo operations and change tracking
   
   Module: workbench-ui/src/components/OntologyManager

2. **Configuration API Integration** ✅ **[EXISTING]**
   - Extends existing configuration API to handle ontology-specific operations
   - Type: `ontology` for all OWL ontology configurations
   - Key: Unique ontology identifier (e.g., `domain-model`, `process-ontology`)
   - Value: Complete ontology in JSON-LD, Turtle, or OWL/XML format

3. **OWL Parser/Serializer Module**
   - Converts between internal JSON representation and standard OWL formats
   - Supports Turtle, RDF/XML, and OWL/XML import/export
   - Validates OWL compliance and logical consistency
   - Handles namespace management and URI generation

   Module: workbench-ui/src/utils/owl

4. **LLM Assistant Integration (Optional)**
   - Provides an optional wizard/getting started flow for new ontologies
   - Connects to existing LLM services for content generation
   - Offers context-aware suggestions for classes, properties, and constraints
   - Supports bulk content enhancement and ontology expansion
   - Can be bypassed entirely for manual ontology creation
   - Maintains logical consistency with existing definitions

   Module: workbench-ui/src/services/ontologyAssistant

5. **Class Hierarchy Visualization Component**
   - Tree-based visual representation of class hierarchies and property relationships
   - Drag-and-drop support for restructuring class inheritance
   - Visual indicators for class completeness, property assignments, and validation status
   - Search and filtering capabilities for classes and properties

   Module: workbench-ui/src/components/OntologyTree

6. **Class/Property Editor Component**
   - Form-based interface for editing classes and properties
   - Dedicated sections for domains, ranges, type constraints, and cardinality
   - Real-time validation and consistency checking
   - Preview of generated OWL/Turtle output

   Module: workbench-ui/src/components/OntologyEditor

7. **Ontology Import/Export Service**
   - Handles file uploads and downloads
   - Supports multiple formats (Turtle, RDF/XML, OWL/XML, JSON-LD)
   - Provides format conversion and validation
   - Manages conflict resolution during imports

   Module: workbench-ui/src/services/ontologyIO

### Data Models

#### Internal Representation

Ontologies are stored as configuration items with the following structure:

**Configuration Schema:**
```
Type: ontology
Key: [ontology_identifier]
Value: {
  "metadata": {
    "name": "Domain Ontology",
    "description": "Comprehensive domain model ontology",
    "version": "1.2",
    "created": "2025-01-15T10:30:00Z",
    "modified": "2025-08-15T14:22:00Z",
    "creator": "data-architect-001",
    "namespace": "http://example.org/domain/",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  },
  "classes": {
    "Document": {
      "uri": "http://example.org/domain/Document",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Document", "lang": "en"}, {"value": "Documento", "lang": "es"}],
      "rdfs:comment": "A document in the system",
      "rdfs:subClassOf": "Resource",
      "owl:disjointWith": ["Person", "Organization"],
      "dcterms:identifier": "DOC-001"
    },
    "Resource": {
      "uri": "http://example.org/domain/Resource",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Resource", "lang": "en"}],
      "rdfs:comment": "Base class for all resources"
    }
  },
  "objectProperties": {
    "hasAuthor": {
      "uri": "http://example.org/domain/hasAuthor",
      "type": "owl:ObjectProperty",
      "rdfs:label": [{"value": "has author", "lang": "en"}],
      "rdfs:domain": "Document",
      "rdfs:range": "Person",
      "owl:inverseOf": "authorOf",
      "rdfs:comment": "Links a document to its author"
    }
  },
  "datatypeProperties": {
    "title": {
      "uri": "http://example.org/domain/title",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "title", "lang": "en"}],
      "rdfs:domain": "Document",
      "rdfs:range": "xsd:string",
      "owl:functionalProperty": true,
      "rdfs:comment": "The title of a document"
    },
    "pageCount": {
      "uri": "http://example.org/domain/pageCount",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "page count", "lang": "en"}],
      "rdfs:domain": "Document",
      "rdfs:range": "xsd:integer",
      "rdfs:comment": "Number of pages in the document"
    }
  }
}
```

#### OWL/RDFS Property Mapping

The UI supports all essential OWL and RDFS properties:

**Class Definition Properties:**
- `owl:Class` - Define object types
- `rdfs:subClassOf` - Class hierarchy and inheritance
- `owl:equivalentClass` - Class equivalence relationships
- `owl:disjointWith` - Disjoint class declarations
- `rdfs:label` - Human-readable labels with language tags
- `rdfs:comment` - Class descriptions and documentation
- `dcterms:identifier` - External reference IDs

**Property Definition:**
- `owl:ObjectProperty` - Properties linking to other classes
- `owl:DatatypeProperty` - Properties with literal values
- `rdfs:domain` - Specifies which classes have the property
- `rdfs:range` - Specifies property value types (classes or XSD datatypes)
- `rdfs:subPropertyOf` - Property hierarchy
- `owl:inverseOf` - Inverse property relationships

**Cardinality and Constraints:**
- `owl:functionalProperty` - At most one value
- `owl:inverseFunctionalProperty` - Unique identifying property
- `owl:minCardinality` - Minimum number of values
- `owl:maxCardinality` - Maximum number of values
- `owl:cardinality` - Exact number of values

**Datatype Support (XSD):**
- `xsd:string` - Text values
- `xsd:integer` - Integer numbers
- `xsd:float` - Floating point numbers
- `xsd:boolean` - True/false values
- `xsd:dateTime` - Date and time values
- `xsd:anyURI` - URI references

### User Interface Design

#### Main Workspace Layout

```
+----------------------------------------------------------+
| Ontology Manager                                    [?] [⚙] |
+----------------------------------------------------------+
| [Ontologies ▼] [+ New] [Import] [Export] [Reasoner]     |
+------------------+---------------------------------------+
| Ontology Tree    | Element Details                       |
| +--------------+ | +-----------------------------------+ |
| | ▼ Classes    | | | Class: Document                   | |
| |   ├─ Resource| | | ┌─ Basic Info ──────────────────┐ | |
| |   │  └─ Doc. | | | │ URI: http://example.org/Doc    │ | |
| |   └─ Person  | | | │ Labels: [en: Document_____]    │ | |
| | ▼ Properties | | | │         [+ Add language]        │ | |
| |   ├─ Object  | | | │ Parent: [Resource_____▼]       │ | |
| |   │  └─ has..| | | │ Disjoint: [Person, Org.]       │ | |
| |   └─ Datatype| | | │ External ID: [DOC-001____]     │ | |
| | [+ Add Class]| | | └─────────────────────────────────┘ | |
| | [🔍 Search_] | | | ┌─ Properties ───────────────────┐ | |
| +--------------+ | | │ Domain Properties:              │ | |
|                  | | │ • title (string)                │ | |
|                  | | │ • hasAuthor → Person            │ | |
|                  | | │ [+ Add Property]                │ | |
|                  | | └─────────────────────────────────┘ | |
+------------------+---------------------------------------+
```

#### Core UI Components

**1. Ontology Selector**
- Dropdown showing all available ontologies
- Quick actions: New, Clone, Delete
- Status indicators: Modified, Validated, Consistent

**2. Ontology Tree**
- Dual-section tree: Classes and Properties
- Expandable class hierarchy with inheritance visualization
- Property organization by type (Object/Datatype)
- Visual indicators: ✓ Complete, ⚠ Missing constraints, ❌ Inconsistencies
- Context menu: Add Subclass, Add Property, Edit, Delete, Move
- Search with highlighting and filtering

**3. Element Detail Panel**
- Context-sensitive form based on selection (Class or Property):
  - **For Classes**:
    - URI, labels (multi-language), parent class
    - Equivalent/disjoint classes
    - Properties with this class as domain
    - External identifiers
  - **For Properties**:
    - Type (Object/Datatype)
    - Domain and range specifications
    - Cardinality constraints
    - Inverse relationships
    - Functional property settings

**4. AI Assistant Panel (Optional)**
- Toggle on/off for manual-only workflow
- When enabled, provides:
  - Context-aware class and property suggestions
  - Bulk operations: "Generate properties for all classes"
  - Smart templates: "Create subclasses for [parent]"
  - Consistency checking: "Find logical conflicts"
  - Domain/range recommendations
- Can be hidden completely for users preferring manual creation

### AI Assistant Features (Optional Wizard)

The AI Assistant is designed as an optional "getting started" wizard that helps users bootstrap their ontologies. Users can:
- Choose to start with the AI wizard or create ontologies manually from scratch
- Toggle AI assistance on/off at any point during editing
- Use AI for specific tasks (e.g., generating properties) while doing everything else manually
- Skip the wizard entirely and build ontologies using traditional manual methods

#### Content Generation Capabilities

**Class Definition Assistant**
- Analyzes class names and inheritance structure
- Suggests appropriate parent classes
- Recommends disjoint class relationships
- Generates class descriptions and documentation

**Property Generator**
- Creates relevant object and datatype properties for classes
- Suggests appropriate domains and ranges
- Recommends cardinality constraints
- Identifies potential inverse relationships

**Type and Constraint Suggestions**
- Recommends appropriate XSD datatypes for properties
- Suggests functional property declarations
- Identifies candidates for inverse functional properties
- Detects potential consistency issues

**Bulk Enhancement**
- Processes multiple classes simultaneously
- Maintains consistency across the ontology
- Fills in missing domains/ranges systematically
- Provides logical consistency checking

#### Implementation Details

**Assistant Integration:**
```javascript
const assistantService = {
  generateClassProperties: async (className, context) => {
    // Analyze class name and context to suggest properties
    // Return object and datatype properties with domains/ranges
  },

  suggestDomainRange: async (propertyName, ontologyContext) => {
    // Recommend appropriate domain classes and range types
    // Consider existing class hierarchy and property patterns
  },

  expandClassHierarchy: async (parentClass, depth = 2) => {
    // Suggest logical subclasses
    // Maintain naming consistency and inheritance logic
  },

  validateConsistency: async (ontology) => {
    // Check for logical inconsistencies
    // Identify missing constraints or conflicting definitions
  }
};
```

### APIs

#### Using the Existing Config API

The ontology management system uses the existing configuration API with type `ontology`. No new API endpoints are needed - all operations go through the existing socket-based config API.

**React Hook Implementation (following the established pattern):**

```typescript
// src/state/ontologies.ts
import { useQueryClient, useQuery, useMutation } from "@tanstack/react-query";
import { useSocket } from "../api/trustgraph/socket";
import { useNotification } from "./notify";
import { useActivity } from "./activity";

export const useOntologies = () => {
  const socket = useSocket();
  const queryClient = useQueryClient();
  const notify = useNotification();

  // Fetch all ontologies using getValues
  const ontologiesQuery = useQuery({
    queryKey: ["ontologies"],
    queryFn: () => {
      return socket
        .config()
        .getValues("ontology")
        .then((values) => {
          // Returns array of [id, ontologyData] tuples
          return values.map((item) => [item.key, JSON.parse(item.value)]);
        })
        .catch((err) => {
          console.log("Error:", err);
          throw err;
        });
    },
  });

  // Create/Update ontology mutation
  const updateOntologyMutation = useMutation({
    mutationFn: ({ id, ontology, onSuccess }) => {
      return socket
        .config()
        .putConfig([
          {
            type: "ontology",
            key: id,
            value: JSON.stringify(ontology),
          },
        ])
        .then((x) => {
          if (x["error"]) {
            console.log("Error:", x);
            throw x.error.message;
          }
          if (onSuccess) onSuccess();
        });
    },
    onError: (err) => {
      console.log("Error:", err);
      notify.error(err.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ontologies"] });
      notify.success("Ontology updated");
    },
  });

  // Delete ontology mutation
  const deleteOntologyMutation = useMutation({
    mutationFn: ({ id, onSuccess }) => {
      return socket
        .config()
        .deleteConfig([
          {
            type: "ontology",
            key: id,
          },
        ])
        .then((x) => {
          if (x["error"]) {
            console.log("Error:", x);
            throw x.error.message;
          }
          if (onSuccess) onSuccess();
        });
    },
    onError: (err) => {
      console.log("Error:", err);
      notify.error(err.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ontologies"] });
      notify.success("Ontology deleted");
    },
  });

  // Track loading states
  useActivity(ontologiesQuery.isLoading, "Loading ontologies");
  useActivity(updateOntologyMutation.isPending, "Updating ontology");
  useActivity(deleteOntologyMutation.isPending, "Deleting ontology");

  return {
    ontologies: ontologiesQuery.data || [],
    ontologiesLoading: ontologiesQuery.isLoading,
    ontologiesError: ontologiesQuery.error,

    updateOntology: updateOntologyMutation.mutate,
    isUpdatingOntology: updateOntologyMutation.isPending,

    createOntology: updateOntologyMutation.mutate, // Same as update
    isCreatingOntology: updateOntologyMutation.isPending,

    deleteOntology: deleteOntologyMutation.mutate,
    isDeletingOntology: deleteOntologyMutation.isPending,

    refetch: () => ontologiesQuery.refetch(),
  };
};
```

**AI Assistant APIs:**

The AI assistant functionality will use the existing LLM integration through the socket API. No new endpoints needed - the assistant will use the existing prompt/completion mechanisms.

### Table Component Implementation

Following the established pattern using Tanstack Table:

**Table Column Definition:**

```typescript
// src/model/ontologies-table.tsx
import { createColumnHelper } from "@tanstack/react-table";

export type OntologyTableRow = [string, {
  metadata: {
    name: string;
    description: string;
    version: string;
    modified: string;
    creator: string;
    namespace: string;
  };
  classes: Record<string, any>;
  objectProperties: Record<string, any>;
  datatypeProperties: Record<string, any>;
}];

const columnHelper = createColumnHelper<OntologyTableRow>();

export const ontologyColumns = [
  columnHelper.accessor((row) => row[0], {
    id: "id",
    header: "ID",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor((row) => row[1].metadata.name, {
    id: "name",
    header: "Name",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor((row) => row[1].metadata.description, {
    id: "description",
    header: "Description",
    cell: (info) => info.getValue() || "-",
  }),
  columnHelper.accessor((row) => Object.keys(row[1].classes || {}).length, {
    id: "classCount",
    header: "Classes",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor((row) =>
    Object.keys(row[1].objectProperties || {}).length +
    Object.keys(row[1].datatypeProperties || {}).length, {
    id: "propertyCount",
    header: "Properties",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor((row) => row[1].metadata.modified, {
    id: "modified",
    header: "Last Modified",
    cell: (info) => new Date(info.getValue()).toLocaleDateString(),
  }),
];
```

**Table Component:**

```typescript
// src/components/ontologies/OntologiesTable.tsx
import React from "react";
import { Box, Table, Text, Spinner, Center } from "@chakra-ui/react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from "@tanstack/react-table";
import { useOntologies } from "../../state/ontologies";
import { OntologyTableRow, ontologyColumns } from "../../model/ontologies-table";
import { EditOntologyDialog } from "./EditOntologyDialog";

export const OntologiesTable: React.FC = () => {
  const { ontologies, ontologiesLoading, ontologiesError } = useOntologies();
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedOntology, setSelectedOntology] =
    React.useState<OntologyTableRow | null>(null);

  const table = useReactTable({
    data: ontologies as OntologyTableRow[],
    columns: ontologyColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const handleRowClick = (row: OntologyTableRow) => {
    setSelectedOntology(row);
    setIsOpen(true);
  };

  if (ontologiesLoading) {
    return (
      <Center h="200px">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (ontologiesError) {
    return (
      <Box p={4} borderWidth="1px" borderColor="red.500" borderRadius="md" bg="red.50">
        <Text color="red.700">
          Error loading ontologies: {ontologiesError.toString()}
        </Text>
      </Box>
    );
  }

  if (ontologies.length === 0) {
    return (
      <Center h="200px">
        <Text color="gray.500">
          No ontologies found. Create one to get started.
        </Text>
      </Center>
    );
  }

  return (
    <>
      <Box overflowX="auto" borderWidth="1px" borderRadius="lg">
        <Table.Root interactive>
          <Table.Header>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Row key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <Table.ColumnHeader key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </Table.ColumnHeader>
                ))}
              </Table.Row>
            ))}
          </Table.Header>
          <Table.Body>
            {table.getRowModel().rows.map((row) => (
              <Table.Row
                key={row.id}
                onClick={() => handleRowClick(row.original)}
                style={{ cursor: "pointer" }}
              >
                {row.getVisibleCells().map((cell) => (
                  <Table.Cell key={cell.id}>
                    {flexRender(
                      cell.column.columnDef.cell,
                      cell.getContext(),
                    )}
                  </Table.Cell>
                ))}
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Box>

      {selectedOntology && (
        <EditOntologyDialog
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          mode="edit"
          ontologyId={selectedOntology[0]}
          initialOntology={selectedOntology[1]}
        />
      )}
    </>
  );
};
```

### Validation and Quality Assurance

#### OWL Compliance and Reasoning

**Structural Validation:**
- Verify proper ontology structure and namespace declarations
- Check for circular class inheritance
- Validate URI consistency and uniqueness
- Ensure required OWL/RDFS properties are present

**Type and Constraint Checking:**
- Validate domain and range specifications
- Check cardinality constraint consistency
- Verify datatype property ranges against XSD types
- Detect conflicting functional property declarations

**Logical Consistency:**
- Check for unsatisfiable classes
- Validate disjoint class declarations
- Ensure property inverse relationships are bidirectional
- Detect inconsistent equivalence relationships

**Reasoning and Inference:**
- Support for OWL reasoners (HermiT, Pellet)
- Automatic classification of inferred relationships
- Detection of implicit contradictions
- Validation of transitivity and symmetry

#### Real-time Validation

```javascript
const validator = {
  validateClass: (owlClass, ontology) => {
    return {
      isValid: boolean,
      errors: [{ field, message, severity }],
      warnings: [{ field, message, suggestion }],
      missingProperties: [propertyNames],
      completeness: percentage
    };
  },

  validateProperty: (property, ontology) => {
    return {
      isValid: boolean,
      domainIssues: [issues],
      rangeIssues: [issues],
      cardinalityConflicts: [conflicts]
    };
  },

  validateOntology: (ontology) => {
    return {
      isConsistent: boolean,
      unsatisfiableClasses: [classIds],
      logicalErrors: [{ type, message, elements }],
      inferredRelationships: [relationships],
      qualityScore: percentage
    };
  },

  runReasoner: async (ontology) => {
    // Integrate with OWL reasoner service
    return {
      inferences: [inferredFacts],
      inconsistencies: [conflicts],
      classification: hierarchyUpdates
    };
  }
};
```

### Import/Export Functionality

#### Supported Formats

**Turtle (.ttl)**
- Standard OWL/RDF representation
- Full property and constraint support
- Namespace management
- Human-readable format

**RDF/XML (.rdf, .owl)**
- W3C standard OWL serialization
- Complete OWL feature support
- Tool compatibility (Protégé, etc.)
- Verbose but comprehensive

**OWL/XML (.owx)**
- OWL-specific XML format
- Structured representation
- Easy parsing and validation
- Direct OWL construct mapping

**JSON-LD (.jsonld)**
- Web-friendly JSON format
- Linked data compatibility
- API integration ready
- Compact representation

#### Import Process

1. **File Upload**: Drag-and-drop or file picker
2. **Format Detection**: Automatic format recognition
3. **Parsing**: Extract classes, properties, and relationships
4. **Preview**: Show ontology structure before import
5. **Conflict Resolution**: Handle duplicate URIs and conflicting definitions
6. **Validation**: Check OWL consistency and run reasoner
7. **Import Execution**: Create configuration entries with full ontology

### Security Considerations

**Access Control:**
- Integrate with existing user authentication
- Role-based permissions for ontology editing
- Audit trail for all modifications
- Version control for ontology changes

**Data Validation:**
- Sanitize all user inputs
- Validate file uploads for malicious content
- Limit ontology size and complexity
- Rate limiting for AI assistant and reasoner requests

### Performance Considerations

**Frontend Optimization:**
- Virtual scrolling for large ontologies
- Lazy loading of class and property details
- Debounced search and filtering
- Optimistic UI updates with rollback
- Incremental reasoning for real-time validation

**Backend Efficiency:**
- Efficient configuration storage queries
- Caching for frequently accessed ontologies
- Batch operations for bulk modifications
- Async processing for large imports
- Background reasoning for complex ontologies

### Testing Strategy

**Unit Testing:**
- Component testing for UI elements
- OWL parser/serializer validation
- AI assistant response handling
- Import/export functionality
- Property constraint validation

**Integration Testing:**
- Configuration API integration
- Full ontology CRUD operations
- Import/export round-trip testing
- AI assistant service integration
- Reasoner integration testing

**User Acceptance Testing:**
- Data architect workflow validation
- Ontology creation scenarios
- Class and property definition workflows
- Constraint specification and validation
- Import/export with real OWL files

## UX Refactoring Plan

### Problem Statement

The current schema creation flow has significant duplication between the creation dialog and the main editor:
- The creation dialog allows entering concepts/fields which duplicates the editor functionality
- Users are forced to work in a constrained dialog when they could be using the full editor
- The transition from creation to editing is jarring and requires mental context switching

### Solution: Streamlined Creation Flow

#### 1. Minimal Creation Dialog

The "Create New Ontology" dialog should only capture the absolute minimum needed to create an ontology:

```
+---------------------------------------------+
| Create New Ontology                     [X] |
+---------------------------------------------+
| Ontology ID:     [___________________]      |
|                                              |
| Name:            [___________________]      |
|                                              |
| Description:     [___________________]      |
|                  [___________________]      |
|                                              |
| Namespace URI:   [http://example.org/____]  |
|                                              |
| ○ Start with blank ontology                 |
| ○ Use AI assistant to bootstrap             |
| ○ Import from file                          |
|                                              |
| [Cancel]              [Create & Open Editor] |
+---------------------------------------------+
```

**Key Features:**
- Only 4 required fields: ID, name, description, namespace
- Three clear starting options
- Single action: "Create & Open Editor"
- No concept/class creation in dialog

#### 2. Main Ontology Editor Workflow

After creation, immediately open the full ontology editor:

```
+----------------------------------------------------------+
| Ontology Editor: Domain Ontology                   [Save] |
+----------------------------------------------------------+
| [Classes] [Properties] [Imports] [Prefixes] [Settings]   |
+----------------------------------------------------------+
| Welcome Panel (shown for new ontologies):                |
| ┌────────────────────────────────────────────────────┐  |
| │ Getting Started with Your Ontology                  │  |
| │                                                      │  |
| │ Your ontology is ready! Here's what to do next:     │  |
| │                                                      │  |
| │ [+ Add First Class]  Start by defining object types │  |
| │ [⚡ Use AI Assistant] Let AI suggest initial classes │  |
| │ [📁 Import Classes]   Load from existing ontology   │  |
| │                                                      │  |
| │ [Dismiss]                        [Show me around 🎯] │  |
| └────────────────────────────────────────────────────┘  |
+----------------------------------------------------------+
```

**Key Benefits:**
- Full editor context immediately available
- Welcome panel provides guidance without constraining
- Can be dismissed to start working immediately
- All tools accessible from the start

#### 3. Editor-First Design Principles

**Immediate Context:**
- User lands in the full editor, not a dialog
- All ontology management happens in one place
- No artificial separation between creation and editing

**Progressive Disclosure:**
- Start simple with empty ontology
- Reveal complexity as user adds elements
- Contextual help and suggestions based on current state

**Persistent Workspace:**
- Auto-save drafts during editing
- Can leave and return without losing work
- Version history for rollback

### Implementation Phases

#### Phase 1: Simplify Creation Dialog
- Remove all field/concept creation from dialog
- Reduce to just core metadata fields
- Add starting mode selection (blank/AI/import)

#### Phase 2: Enhance Editor Landing
- Create welcome panel component
- Implement guided first steps
- Add contextual empty states

#### Phase 3: Improve Editor Navigation
- Tab-based navigation for different aspects
- Breadcrumb trail for deep navigation
- Quick access toolbar for common actions

#### Phase 4: AI Integration Points
- AI assistant panel (collapsible)
- Inline suggestions in editors
- Bulk generation workflows

### Detailed Component Changes

#### CreateOntologyDialog Component

```typescript
// Simplified creation dialog
interface CreateOntologyDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (ontologyId: string) => void; // Callback to open editor
}

// Only captures:
// - id: string (kebab-case, unique)
// - name: string (display name)
// - description: string (brief description)
// - namespace: string (base URI)
// - startMode: 'blank' | 'ai-assisted' | 'import'
```

#### OntologyEditor Component

```typescript
// Full-featured editor
interface OntologyEditorProps {
  ontologyId: string;
  showWelcome?: boolean; // Show welcome panel for new ontologies
}

// Features:
// - Multi-tab interface (Classes, Properties, etc.)
// - Split-pane layout (tree + details)
// - Integrated AI assistant (optional)
// - Real-time validation
// - Import/Export toolbar
```

### Benefits of This Approach

1. **Reduced Cognitive Load**: Users only think about metadata during creation
2. **Faster Time to Value**: Get into the editor immediately
3. **Consistent Context**: All ontology work happens in the editor
4. **Better Discoverability**: Full UI reveals all capabilities
5. **Natural Workflow**: Create → Edit → Refine (no back-and-forth)

### Migration from Current System

1. **Preserve Existing Schemas**: Convert to OWL format behind the scenes
2. **Dual Mode Support**: Keep old schema editor while building new ontology editor
3. **Gradual Transition**: Users can opt-in to new editor
4. **Data Migration Tools**: Automated conversion utilities

### Success Metrics

- Time from "Create" click to first class/property added
- Number of back-navigations during creation flow
- User feedback on creation experience
- Completion rate of ontology creation
- Feature discovery and usage

### Migration Plan

**Phase 1: Core UI**
- Basic ontology management interface
- Configuration API integration
- Class and property CRUD operations

**Phase 2: Advanced Features**
- Class hierarchy visualization
- Property domain/range specification
- Cardinality and constraint management
- Multi-language label support

**Phase 3: AI Assistant Wizard**
- Optional LLM integration
- "Getting started" wizard flow
- Property generation features
- Consistency checking tools
- Manual-only mode support

**Phase 4: Reasoning & Import/Export**
- OWL reasoner integration
- File format support (Turtle, RDF/XML, OWL/XML)
- Import/export workflows
- Inference visualization

### Open Questions

- Do we need integration with external ontology repositories (e.g., BioPortal, schema.org)? Not needed currently.
- Should the system support ontology versioning and branching? No.
- How should we handle very large ontologies (1000+ classes)? No explicit support needed at the moment.
- Do we need offline editing capabilities? No.
- Which OWL profiles should we support (OWL Lite, DL, Full)? Start with OWL DL for decidable reasoning.

### References

- [OWL 2 Web Ontology Language Reference](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [RDF/XML Syntax Specification](https://www.w3.org/TR/rdf-syntax-grammar/)
- [OWL 2 XML Serialization](https://www.w3.org/TR/owl2-xml-serialization/)
- [JSON-LD 1.1 Specification](https://www.w3.org/TR/json-ld11/)
- [Turtle RDF Syntax](https://www.w3.org/TR/turtle/)
- [Dublin Core Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)

