# LLM Models Editor Technical Specification

## Overview

This specification describes the LLM Models Editor in the TrustGraph UI. This feature allows administrators to manage the `llm-model` parameter type - the list of available LLM models that appear in dropdown menus when launching flows.

The LLM model list is stored as a parameter type definition in the configuration system with type `"parameter-types"` and key `"llm-model"`. The editor provides a simple table interface for managing model options (ID, Description, Default).

## Background

The `llm-model` parameter controls which models are available when configuring flows. It's stored as a parameter type definition with an `enum` field containing model options.

### Current State

- The llm-model parameter can be modified through direct config API calls or CLI commands
- The parameter type with its `enum` array renders as a dropdown in flow dialogs
- The default value determines which model is pre-selected

### Feature Switch

This feature is controlled by a feature switch in Settings:
- **Setting Name**: `llmModels`
- **Display Label**: "LLM Models"
- **Default**: `false` (off by default)
- **Location**: Settings page → Feature Switches section

## Goals

- **Simple Table Editor**: Editable table with ID, Description, and Default columns
- **Direct Editing**: Edit model options directly in table cells
- **Add/Delete Rows**: Add new models or delete existing ones
- **Default Selection**: Radio button to mark one model as default
- **Save Changes**: Manual save with "Save Changes" button
- **Auto-defaults**: First model automatically selected as default when adding to empty table

## Technical Design

### Architecture

Following CODEBOT-INSTRUCTIONS.md patterns:

**Component Structure:**
```
src/
├── pages/
│   └── LLMModelsPage.tsx                    # Main page with PageHeader
├── components/
│   └── llm-models/                          # Domain-specific directory
│       ├── LLMModels.tsx                    # Container component
│       ├── ParameterTypeSelector.tsx        # (unused - kept for future)
│       └── ModelsTable.tsx                  # Editable table with save
├── state/
│   └── llm-models.ts                        # API hooks
└── model/
    └── llm-models.ts                        # TypeScript types
```

### Data Models

#### EnumOption (Model Option)

```typescript
interface EnumOption {
  id: string;           // Model ID (e.g., "gemini-2.5-flash")
  description: string;  // Display text (e.g., "Gemini 2.5 Flash")
}
```

#### LLMModelParameter

```typescript
interface LLMModelParameter {
  name: string;                // Parameter type key (always "llm-model")
  type: string;                // Always "string"
  description: string;         // Read-only (e.g., "LLM model to use")
  default: string;             // Default model ID
  enum: EnumOption[];          // List of models
  required: boolean;           // Read-only
}
```

### Implementation Details

**Key Behavior:**
1. Page only handles the single `llm-model` parameter type
2. Table edits are local until "Save Changes" is clicked
3. Radio buttons use native HTML inputs (Chakra RadioGroup had issues in tables)
4. When adding first model to empty table, it's auto-selected as default
5. When editing ID of default model, default value updates to track changes
6. When deleting default model, first remaining model becomes default
7. Empty ID fields are allowed but disabled for default selection

**State Management:**
- Uses `getConfig([{type: "parameter-types", key: "llm-model"}])` to fetch single param
- Uses `putConfig()` to save changes, preserving read-only fields
- React Query handles caching and invalidation

### Routing and Navigation

#### Route (`src/App.tsx`)
```typescript
<Route path="/llm-models" element={<LLMModelsPage />} />
```

#### Sidebar Navigation (`src/components/Sidebar.tsx`)
```typescript
{settings.featureSwitches.llmModels && (
  <NavItem to="/llm-models" icon={Bot} label="LLM Models" />
)}
```

### Feature Switch Integration

#### Settings Types (`src/model/settings-types.ts`)
```typescript
featureSwitches: {
  llmModels: boolean;  // Default: false
}
```

#### Feature Switches Section (`src/components/settings/FeatureSwitchesSection.tsx`)
Adds toggle UI with prop `llmModels` and handler `onLlmModelsChange`

## User Workflows

### Editing Model Options

1. Enable feature in Settings → Feature Switches → LLM Models
2. Navigate to LLM Models page from sidebar
3. View current models in table
4. Edit ID or Description fields directly
5. Click "Save Changes" to persist
6. Notification confirms success

### Setting Default Model

1. View models table
2. Click radio button in "Default" column for desired model
3. Click "Save Changes" to persist

### Adding New Model

1. Click "Add Model" button
2. New empty row appears
3. Enter Model ID and Description
4. If it's the only model, radio button is auto-selected
5. Click "Save Changes" to persist

### Deleting Model

1. Click trash icon next to model
2. Row is removed from local state
3. If deleted model was default, first remaining model becomes default
4. Click "Save Changes" to persist

## Implementation Checklist

- [x] Update `src/model/settings-types.ts` - Add `llmModels` feature switch
- [x] Update `src/components/settings/FeatureSwitchesSection.tsx` - Add LLM Models toggle
- [x] Update `src/components/settings/Settings.tsx` - Wire up llmModels prop
- [x] Create `src/model/llm-models.ts` - Type definitions
- [x] Create `src/state/llm-models.ts` - useLLMModels hook
- [x] Create `src/components/llm-models/LLMModels.tsx` - Container
- [x] Create `src/components/llm-models/ParameterTypeSelector.tsx` - (Created but unused)
- [x] Create `src/components/llm-models/ModelsTable.tsx` - Editable table with save
- [x] Create `src/pages/LLMModelsPage.tsx` - Main page with PageHeader
- [x] Update `src/App.tsx` - Add route
- [x] Update `src/components/Sidebar.tsx` - Add navigation item with Bot icon
- [x] Test CRUD operations
- [x] Test feature switch toggle

## Future Enhancements

1. **Multiple Parameter Types**: Support editing other parameter types with enum arrays (llm-rag-model, etc.)
2. **Import/Export**: Bulk import/export model lists from JSON
3. **Templates**: Pre-configured model lists for common providers
4. **Model Metadata**: Additional fields like context length, cost per token
5. **Reordering**: Drag-and-drop or up/down arrows to reorder models

## References

- Flow Configurable Parameters: `docs/tech-specs/flow-configurable-parameters.md`
- Parameter Inputs Component: `src/components/flows/ParameterInputs.tsx`
- Settings Feature Switches: `src/components/settings/FeatureSwitchesSection.tsx`
- CODEBOT Instructions: `CODEBOT-INSTRUCTIONS.md`
