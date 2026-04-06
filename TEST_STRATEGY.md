# Test Strategy for TrustGraph UI

## Overview

This document outlines the comprehensive testing strategy for the TrustGraph UI application, a React-based knowledge graph visualization and chat interface built with TypeScript, Vite, and Chakra UI.

## Technology Stack

- **Frontend**: React 18, TypeScript, Vite
- **UI Framework**: Chakra UI v3
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router v7
- **Visualization**: React Force Graph (3D), Three.js
- **WebSocket**: Custom socket implementation for real-time communication
- **Build Tools**: Vite, ESLint, Prettier

## Testing Approach

### 1. Unit Testing

#### Framework Recommendation
- **Jest** + **React Testing Library** for component testing
- **Vitest** (recommended for Vite projects) as Jest alternative
- **@testing-library/jest-dom** for DOM assertions

#### What to Test
- **State Management (Zustand stores)**:
  - `src/state/chat.ts` - Chat state management
  - `src/state/session.ts` - Session state
  - `src/state/workbench.ts` - Workbench state
  - `src/state/graph-query.ts` - Graph query state
  - All other state modules in `src/state/`

- **Utility Functions**:
  - `src/utils/knowledge-graph.ts` - Graph manipulation utilities
  - `src/utils/document-encoding.ts` - Document encoding/decoding
  - `src/utils/vector-search.ts` - Vector search utilities
  - `src/utils/time-string.ts` - Time formatting utilities

- **API Layer**:
  - `src/api/trustgraph/socket.ts` - WebSocket connection
  - `src/api/trustgraph/service-call.ts` - Service call utilities
  - `src/api/trustgraph/messages.ts` - Message handling

#### Test Structure
```
tests/
├── unit/
│   ├── components/
│   ├── state/
│   ├── utils/
│   ├── api/
│   └── model/
├── integration/
├── e2e/
└── fixtures/
```

### 2. Component Testing

#### Core Components to Test
- **Chat Components**:
  - `src/components/chat/ChatConversation.tsx`
  - `src/components/chat/ChatMessage.tsx`
  - `src/components/chat/InputArea.tsx`
  - `src/components/chat/ChatModeSelector.tsx`

- **Graph Components**:
  - `src/components/graph/Graph.tsx`
  - `src/components/entity/EntityDetail.tsx`
  - `src/components/entity/EntityNode.tsx`

- **Common Components**:
  - `src/components/common/BasicTable.tsx`
  - `src/components/common/SelectableTable.tsx`
  - `src/components/common/TextField.tsx`
  - `src/components/common/Card.tsx`

- **Layout Components**:
  - `src/components/Layout.tsx`
  - `src/components/Sidebar.tsx`

#### Testing Strategies
- **Snapshot Testing** for UI consistency
- **User Interaction Testing** (click, input, navigation)
- **Props Testing** and component behavior
- **Error Boundary Testing**
- **Accessibility Testing** (screen reader, keyboard navigation)

### 3. Integration Testing

#### Areas to Test
- **WebSocket Integration**: Test real-time communication with backend
- **State Persistence**: Test Zustand store persistence
- **Route Navigation**: Test React Router integration
- **API Integration**: Test service calls and data flow
- **Component Interaction**: Test parent-child component communication

#### Mock Strategy
- Mock WebSocket connections for consistent testing
- Mock external APIs and services
- Mock file upload/download operations
- Mock 3D graph rendering for performance

### 4. End-to-End Testing

#### Framework Recommendation
- **Playwright** or **Cypress** for cross-browser testing

#### Test Scenarios
1. **User Authentication Flow**
2. **Chat Interface**:
   - Send messages in different modes (graph-rag, agent, basic-llm)
   - Receive and display responses
   - Chat history persistence

3. **Knowledge Graph Visualization**:
   - Load and display graph data
   - Node interaction and navigation
   - Graph filtering and search

4. **Document Management**:
   - Upload documents
   - Process and index documents
   - Search through document library

5. **Flow Management**:
   - Create and edit processing flows
   - Execute flows with different parameters

6. **Agent Tools**:
   - Configure MCP tools
   - Test agent interactions
   - Tool execution and results

### 5. Performance Testing

#### Areas to Monitor
- **Bundle Size**: Monitor JavaScript bundle size
- **3D Graph Rendering**: Test performance with large graphs
- **Memory Usage**: Monitor memory leaks in long-running sessions
- **WebSocket Performance**: Test real-time communication under load

#### Tools
- **Lighthouse** for web performance metrics
- **Bundle Analyzer** for bundle size optimization
- **React DevTools Profiler** for component performance

### 6. Accessibility Testing

#### Requirements
- **WCAG 2.1 AA** compliance
- **Screen Reader** compatibility
- **Keyboard Navigation** support
- **Color Contrast** validation

#### Tools
- **axe-core** for automated accessibility testing
- **React Testing Library** accessibility queries
- **Manual testing** with screen readers

## Testing Infrastructure

### Setup Requirements
```bash
# Install testing dependencies
npm install --save-dev \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jsdom \
  @vitest/ui \
  playwright
```

### Configuration Files
- `vitest.config.ts` - Vitest configuration
- `playwright.config.ts` - E2E test configuration
- `test-setup.ts` - Global test setup

### CI/CD Integration
- **GitHub Actions** workflow for automated testing
- **Pre-commit hooks** for running tests before commits
- **Coverage reporting** with minimum thresholds
- **Visual regression testing** for UI components

## Test Data Management

### Mock Data Strategy
- **Fixtures**: Static test data for consistent testing
- **Factory Functions**: Generate test data programmatically
- **MSW (Mock Service Worker)**: Mock API responses
- **WebSocket Mocking**: Mock real-time communication

### Data Categories
- **Graph Data**: Nodes, edges, and relationships
- **Chat Messages**: Various message types and formats
- **User Sessions**: Authentication and session data
- **Document Metadata**: File information and processing status

## Coverage Goals

### Minimum Coverage Targets
- **Unit Tests**: 80% line coverage
- **Integration Tests**: Cover all major user flows
- **E2E Tests**: Cover critical business paths
- **Component Tests**: 90% of UI components

### Exclusions
- Third-party library code
- Generated type definitions
- Development-only code

## Testing Best Practices

### General Guidelines
1. **Test behavior, not implementation**
2. **Use descriptive test names**
3. **Keep tests independent and isolated**
4. **Test error conditions and edge cases**
5. **Maintain test data consistency**

### React-Specific Guidelines
1. **Test user interactions, not internal state**
2. **Use React Testing Library queries effectively**
3. **Test accessibility features**
4. **Mock external dependencies**
5. **Test component composition**

## Monitoring and Maintenance

### Test Health
- **Flaky Test Detection**: Monitor and fix unstable tests
- **Test Performance**: Keep test execution time reasonable
- **Coverage Trends**: Monitor coverage over time
- **Test Maintenance**: Regular review and cleanup

### Quality Gates
- **All tests must pass** before merging
- **Coverage thresholds** must be maintained
- **Performance budgets** must not be exceeded
- **Accessibility standards** must be met

## Domain-Specific Testing Strategy

### Agents Module (`src/components/agents/`)

#### Components to Test:
- **EditDialog.tsx**: Agent configuration dialog
  - Form validation for agent settings
  - Tool selection and configuration
  - Modal open/close behavior
- **ToolsTable.tsx**: Display agent tools
  - Table rendering with tool data
  - Tool selection/filtering
  - Action buttons (edit, delete, enable/disable)

#### Testing Approach:
```tsx
// Example test structure
describe('Agent EditDialog', () => {
  it('validates required fields', () => {
    // Test form validation
  });
  
  it('handles tool selection', () => {
    // Test multi-select tool interface
  });
  
  it('saves agent configuration', () => {
    // Test API calls and state updates
  });
});
```

#### Mock Requirements:
- Agent configuration API calls
- Available tools data
- Agent execution results

---

### Graph Module (`src/components/graph/`)

#### Components to Test:
- **Graph.tsx**: 3D force graph visualization
  - Graph rendering with mock data
  - Node selection and highlighting
  - Performance with large datasets (>1000 nodes)
- **NodeDetailsDrawer.tsx**: Entity detail panel
  - Property display formatting
  - Relationship navigation
  - Edit mode functionality

#### Testing Challenges:
- **3D Rendering**: Mock Three.js and react-force-graph
- **Performance**: Test with large graph datasets
- **Interactions**: Node selection, drag, zoom behaviors

#### Testing Approach:
```tsx
describe('Graph Component', () => {
  beforeEach(() => {
    // Mock 3D rendering libraries
    vi.mock('react-force-graph-3d');
  });
  
  it('renders nodes and links', () => {
    // Test graph data rendering
  });
  
  it('handles node selection', () => {
    // Test node click events
  });
  
  it('performs well with large datasets', () => {
    // Performance testing with 1000+ nodes
  });
});
```

---

### MCP Tools Module (`src/components/mcp-tools/`)

#### Components to Test:
- **EditDialog.tsx**: MCP tool configuration
  - Tool parameter validation
  - API endpoint configuration
  - Authentication settings
- **McpToolsTable.tsx**: Tools management interface
  - Tool status indicators
  - Bulk operations (enable/disable multiple tools)
  - Tool execution history

#### Test Data Requirements:
```tsx
// Mock MCP tool configurations
const mockMcpTool = {
  id: 'test-tool-1',
  name: 'File System Tool',
  endpoint: 'http://localhost:3001',
  enabled: true,
  parameters: {
    path: '/tmp',
    permissions: 'read-write'
  }
};
```

---

### Prompts Module (`src/components/prompts/`)

#### Components to Test:
- **EditDialog.tsx**: Prompt template editor
  - Template syntax validation
  - Variable substitution preview
  - JSON schema validation for structured outputs
- **PromptsTable.tsx**: Prompt management
  - Template versioning
  - Usage statistics
  - Import/export functionality

#### Key Test Scenarios:
- Template variable validation: `{{variable}}` syntax
- JSON schema validation for structured prompts
- Prompt execution with different input types

---

### Schemas Module (`src/components/schemas/`) - Recently Modularized

#### Components to Test (New Modular Structure):
- **SchemaFieldEditor.tsx**: Individual field configuration
  - Field type selection and validation
  - Enum value management
  - Required/optional field toggles
- **useSchemaForm.ts**: Form state management hook
  - Field addition/removal
  - Form validation logic
  - Form reset functionality
- **EnumValueManager.tsx**: Enum value editing
  - Add/remove enum values
  - Duplicate value prevention
  - Input validation

#### Testing Approach for Modular Components:
```tsx
describe('Schema Field Editor', () => {
  it('handles field type changes', () => {
    // Test type dropdown and dependent field updates
  });
  
  it('manages enum values correctly', () => {
    // Test enum value addition/removal
  });
  
  it('validates field configurations', () => {
    // Test field validation rules
  });
});

describe('useSchemaForm hook', () => {
  it('manages form state correctly', () => {
    // Test hook state management
  });
  
  it('handles field operations', () => {
    // Test add/remove/update field operations
  });
});
```

---

### Taxonomies Module (`src/components/taxonomies/`) - Extensive Functionality

#### Priority Components to Test:
- **TaxonomyManager.tsx**: Main taxonomy editor
  - SKOS concept hierarchy management
  - Concept relationships (broader/narrower/related)
  - Bulk concept operations
- **ConceptEditor.tsx**: Individual concept editing
  - Concept metadata validation
  - Relationship consistency checking
  - Auto-save functionality
- **TaxonomyValidationTab.tsx**: SKOS validation
  - Validation rule execution
  - Error reporting and suggestions
  - Auto-fix functionality
- **SKOSDialog.tsx**: Import/export functionality
  - SKOS RDF/XML parsing
  - Format conversion (RDF ↔ Turtle ↔ JSON)
  - File upload/download

#### Complex Test Scenarios:
```tsx
describe('Taxonomy Validation', () => {
  it('detects circular references', () => {
    const invalidTaxonomy = {
      concepts: {
        'A': { broader: 'B' },
        'B': { broader: 'A' }  // Circular reference
      }
    };
    // Test validation catches this error
  });
  
  it('suggests auto-fixes', () => {
    // Test quality improvement suggestions
  });
});

describe('SKOS Import/Export', () => {
  it('parses valid SKOS RDF/XML', () => {
    // Test XML parsing and conversion
  });
  
  it('handles parsing errors gracefully', () => {
    // Test error handling for invalid SKOS
  });
});
```

#### Mock Requirements:
- SKOS validation rules
- File upload/download operations
- Large taxonomy datasets (100+ concepts)

---

## Implementation Roadmap (Updated)

### Phase 1: Foundation & Utilities (Weeks 1-2)
- **Complete**: Set up testing framework (Vitest already configured)
- **Complete**: Utility function tests (SKOS, time-string, encoding)
- **Complete**: Basic common component tests
- **New**: Test modularized schema components

### Phase 2: Domain-Specific Components (Weeks 3-4)
- **Agents Module**: Test agent configuration and tools management
- **Prompts Module**: Test prompt editing and template validation  
- **MCP Tools Module**: Test tool configuration and execution
- **Graph Module**: Test visualization components (with mocked 3D)

### Phase 3: Complex Domain Logic (Weeks 5-6)
- **Taxonomies Module**: Test SKOS validation, concept editing, import/export
- **Schemas Module**: Test advanced schema validation and form logic
- **Integration Tests**: Test cross-module interactions

### Phase 4: Advanced Testing (Weeks 7-8)
- **Performance Testing**: Large dataset handling (1000+ graph nodes, 100+ taxonomy concepts)
- **E2E Workflows**: Complete user journeys across modules
- **Accessibility**: WCAG compliance for all form components
- **Visual Regression**: Ensure UI consistency across refactoring

---

## Testing Priority Matrix

### High Priority (Week 3-4)
1. **Taxonomies**: Complex SKOS logic, validation, import/export
2. **Schemas**: Recently modularized, needs comprehensive coverage
3. **Graph**: Core visualization functionality
4. **Agents**: Critical for AI functionality

### Medium Priority (Week 5-6)  
1. **Prompts**: Template management and validation
2. **MCP Tools**: Tool configuration and execution
3. **Integration**: Cross-module data flow

### Lower Priority (Week 7-8)
1. **Performance**: Large dataset handling
2. **Accessibility**: WCAG compliance  
3. **Visual**: UI consistency and regression testing

---

## Mock Data Strategy (Updated)

### Taxonomy Test Data:
```tsx
const mockTaxonomy = {
  concepts: {
    'animals': {
      prefLabel: 'Animals',
      narrower: ['mammals', 'birds'],
      topConcept: true
    },
    'mammals': {
      prefLabel: 'Mammals', 
      broader: 'animals',
      narrower: ['cats', 'dogs']
    }
  },
  scheme: {
    uri: 'http://example.org/taxonomy',
    hasTopConcept: ['animals']
  }
};
```

### Schema Test Data:
```tsx
const mockSchema = {
  name: 'Customer Record',
  fields: [
    {
      name: 'customer_id',
      type: 'string',
      required: true,
      primary_key: true
    },
    {
      name: 'status',
      type: 'enum',
      enum: ['active', 'inactive', 'pending']
    }
  ]
};
```

### Agent Test Data:
```tsx
const mockAgent = {
  id: 'research-agent',
  name: 'Research Assistant',
  description: 'Helps with research tasks',
  tools: ['web-search', 'document-reader'],
  model: 'gpt-4',
  temperature: 0.7
};
```

## Success Metrics

- **Test Coverage**: Achieve and maintain 80%+ coverage
- **Test Reliability**: < 1% flaky test rate
- **Test Performance**: Test suite completes in < 5 minutes
- **Bug Detection**: Catch 90%+ of bugs before production
- **Developer Experience**: Tests provide clear feedback and are easy to maintain

## Conclusion

This testing strategy provides comprehensive coverage for the TrustGraph UI application, ensuring reliability, performance, and maintainability. The phased implementation approach allows for gradual adoption while maintaining development velocity.

Regular review and updates of this strategy will ensure it remains effective as the application evolves and new features are added.