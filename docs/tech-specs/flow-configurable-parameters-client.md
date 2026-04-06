# Flow Configurable Parameters - Client-Side Technical Specification

## Overview

This specification describes the client-side implementation of configurable parameters for flow classes in TrustGraph UI. This complements the server-side implementation by providing dynamic form generation, parameter validation, and user-friendly parameter input interfaces for flow creation.

The client-side implementation enables users to:
- View available parameters when selecting a flow class
- Input parameter values through dynamically generated forms
- Validate parameters according to their schema definitions
- Launch flows with custom parameter configurations
- Save and reuse parameter presets for common configurations

## Goals

- **Dynamic Form Generation**: Automatically create parameter input forms based on flow class parameter schemas
- **Type-Safe Validation**: Validate parameter inputs according to schema definitions (string, number, boolean, enum)
- **Intuitive User Experience**: Provide clear parameter descriptions, validation feedback, and sensible defaults
- **Integration with Existing UI**: Seamlessly integrate with the current CreateDialog and flow management system
- **Parameter Presets**: Allow users to save and reuse common parameter configurations
- **Real-time Feedback**: Show validation errors and hints as users input parameters
- **Accessibility**: Ensure parameter forms are accessible and follow project UI patterns

## Architecture

### Component Structure

```
src/components/flows/
├── CreateDialog.tsx              # Enhanced with parameter support
├── ParameterInputs.tsx           # Dynamic parameter form component
├── ParameterPresets.tsx          # Parameter preset management
├── ParameterValidation.tsx       # Validation logic and error display
└── __tests__/
    ├── ParameterInputs.test.tsx
    └── ParameterPresets.test.tsx

src/state/
├── flows.ts                      # Enhanced with parameter support
└── flow-parameters.ts            # Parameter definition fetching and caching

src/model/
└── flow-parameters.ts            # Parameter type definitions and utilities
```

### Data Flow

1. **Parameter Schema Fetching**:
   ```
   User selects flow class → Fetch parameter definitions → Parse schema → Generate form
   ```

2. **Parameter Input**:
   ```
   User inputs values → Validate against schema → Update form state → Enable/disable submit
   ```

3. **Flow Creation**:
   ```
   User submits → Validate all parameters → Send to API → Create flow with parameters
   ```

## Technical Design

### Core Types

```typescript
// Parameter schema definition (from server)
interface ParameterSchema {
  type: 'string' | 'number' | 'integer' | 'boolean';
  description?: string;
  default?: any;
  enum?: EnumOption[] | string[]; // Can be rich objects or simple strings
  minimum?: number;
  maximum?: number;
  pattern?: string;
  required?: boolean;
  helper?: string; // Custom helper text
  placeholder?: string; // Custom placeholder text
}

// Rich enum option structure
interface EnumOption {
  id: string; // The actual value
  description: string; // Display text
}

// Flow class structure (from getFlowClass API)
interface FlowClass {
  class: { [processorName: string]: any }; // Processor definitions
  description: string;
  flow: { [stepName: string]: any }; // Flow step definitions
  interfaces: { [interfaceName: string]: any }; // Interface definitions
  parameters?: { [flowParamName: string]: FlowParameterMetadata }; // Maps flow param names to parameter metadata
  tags?: string[];
}

// Flow parameter metadata structure
interface FlowParameterMetadata {
  type: string; // Reference to parameter-type definition name
  description: string; // Human-readable description for UI display
  order: number; // Display order for parameter forms (lower numbers appear first)
}

// Parameter definitions fetched from config
interface ParameterDefinitions {
  [definitionName: string]: ParameterSchema;
}

// User parameter values
interface ParameterValues {
  [flowParamName: string]: any;
}

// Parameter validation result
interface ValidationResult {
  isValid: boolean;
  errors: { [paramName: string]: string };
}
```

### Component Implementation

#### 1. Enhanced CreateDialog

```typescript
// Key enhancements to existing CreateDialog
const CreateDialog = ({ open, onOpenChange }) => {
  const [flowClass, setFlowClass] = useState<string>();
  const [id, setId] = useState("");
  const [description, setDescription] = useState("");
  const [parameterValues, setParameterValues] = useState<ParameterValues>({});

  // Fetch parameter definitions when flow class is selected
  const {
    parameterDefinitions,
    isLoadingParameters
  } = useFlowParameters(flowClass);

  // Validate form including parameters
  const { isValid, errors } = useParameterValidation(
    flowClass,
    parameterDefinitions,
    parameterValues
  );

  const onSubmit = () => {
    if (!isValid) return;

    flowState.startFlow({
      id,
      flowClass,
      description,
      parameters: parameterValues, // Include parameters
      onSuccess: () => {
        setParameterValues({}); // Clear parameters on success
        // ... rest of success logic
      },
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {/* Existing dialog structure */}

      {/* Enhanced with parameter inputs */}
      <ParameterInputs
        flowClass={flowClass}
        parameterDefinitions={parameterDefinitions}
        parameterValues={parameterValues}
        onParameterChange={setParameterValues}
        validationErrors={errors}
      />

      {/* Parameter presets */}
      <ParameterPresets
        flowClass={flowClass}
        onPresetLoad={setParameterValues}
        currentValues={parameterValues}
      />
    </Dialog.Root>
  );
};
```

#### 2. ParameterInputs Component

**Following Project Patterns**:
- Uses common components (TextField, SelectField) instead of raw Chakra
- Implements Chakra v3 patterns (Field.Root, etc.)
- Provides proper SelectField descriptions with SelectOptionText

```typescript
interface ParameterInputsProps {
  flowClass?: string;
  parameterDefinitions: ParameterDefinitions;
  parameterValues: ParameterValues;
  onParameterChange: (values: ParameterValues) => void;
  validationErrors: { [key: string]: string };
}

const ParameterInputs: React.FC<ParameterInputsProps> = ({
  parameterDefinitions,
  parameterValues,
  onParameterChange,
  validationErrors,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);

  const handleParameterChange = (paramName: string, value: any) => {
    onParameterChange({
      ...parameterValues,
      [paramName]: value,
    });
  };

  const renderParameterInput = (paramName: string, schema: ParameterSchema) => {
    const defaultValue = schema.default;
    const value = parameterValues[paramName] ?? defaultValue ?? "";
    const error = validationErrors[paramName];
    const label = (schema.description || paramName) + (schema.required ? " *" : "");

    // Helper text priority: schema.helper -> type-based fallback
    const getHelperText = () => {
      if (schema.helper) return schema.helper;

      switch (schema.type) {
        case 'integer': return 'Enter a whole number';
        case 'number': return 'Enter a number (decimals allowed)';
        case 'boolean': return 'Select true or false';
        case 'string': return schema.enum ? undefined : 'Enter text';
        default: return undefined;
      }
    };

    const helperText = getHelperText();
    const placeholder = schema.placeholder || "";

    // Enum parameters - handle both rich {id, description} and simple string arrays
    if (schema.enum && schema.enum.length > 0) {
      const options = schema.enum.map(option => {
        // Handle both rich {id, description} and simple string enums
        const optionId = typeof option === 'object' ? option.id : option;
        const optionDesc = typeof option === 'object' ? option.description : option;

        return {
          value: optionId,
          label: optionDesc,
          description: (
            <SelectOptionText title={optionDesc}>
              {optionId}
            </SelectOptionText>
          ),
        };
      });

      return (
        <Box key={paramName} mt={5}>
          <SelectField
            label={label}
            items={options}
            value={value ? [value.toString()] : []}
            onValueChange={(values) => {
              const selectedValue = values.length > 0 ? values[0] : "";
              handleParameterChange(paramName, selectedValue);
            }}
            contentRef={contentRef}
          />
          {error && <Text color="red.500" fontSize="sm" mt={1}>{error}</Text>}
          {helperText && (
            <Text fontSize="sm" color="fg.muted" mt={1}>
              {helperText}
            </Text>
          )}
        </Box>
      );
    }

    // Boolean parameters - use Checkbox
    if (schema.type === 'boolean') {
      return (
        <Box key={paramName} mt={5}>
          <Field.Root>
            <Checkbox
              checked={value}
              onChange={(e) => handleParameterChange(paramName, e.target.checked)}
            >
              {label}
            </Checkbox>
            {helperText && <Field.HelperText>{helperText}</Field.HelperText>}
            {error && <Text color="red.500" fontSize="sm" mt={1}>{error}</Text>}
          </Field.Root>
        </Box>
      );
    }

    // Number/Integer parameters - use TextField with type="number"
    if (schema.type === 'number' || schema.type === 'integer') {
      let enhancedHelperText = helperText;
      if (schema.minimum !== undefined || schema.maximum !== undefined) {
        const rangeText = [];
        if (schema.minimum !== undefined) rangeText.push(`min: ${schema.minimum}`);
        if (schema.maximum !== undefined) rangeText.push(`max: ${schema.maximum}`);
        const rangeInfo = rangeText.join(", ");
        enhancedHelperText = enhancedHelperText
          ? `${enhancedHelperText} (${rangeInfo})`
          : rangeInfo;
      }

      return (
        <Box key={paramName} mt={5}>
          <TextField
            label={label}
            helperText={enhancedHelperText}
            placeholder={placeholder}
            value={value.toString()}
            onValueChange={(val) => {
              const numValue = schema.type === 'integer'
                ? parseInt(val, 10)
                : parseFloat(val);
              if (!isNaN(numValue)) {
                handleParameterChange(paramName, numValue);
              } else if (val === "") {
                handleParameterChange(paramName, "");
              }
            }}
            type="number"
            required={schema.required}
          />
          {error && <Text color="red.500" fontSize="sm" mt={1}>{error}</Text>}
        </Box>
      );
    }

    // String parameters - use TextField
    return (
      <Box key={paramName} mt={5}>
        <TextField
          label={label}
          helperText={helperText}
          placeholder={placeholder}
          value={value.toString()}
          onValueChange={(val) => handleParameterChange(paramName, val)}
          required={schema.required}
        />
        {error && <Text color="red.500" fontSize="sm" mt={1}>{error}</Text>}
      </Box>
    );
  };

  return (
    <Box>
      {Object.entries(parameterDefinitions).map(([paramName, schema]) =>
        renderParameterInput(paramName, schema)
      )}
    </Box>
  );
};
```

#### 3. State Management

**Following Project Patterns**:
- Uses TanStack Query for API calls and caching
- Uses useActivity hook for loading states
- Uses useNotification hook for error/success messages

```typescript
// Enhanced flows.ts state
export const useFlows = () => {
  // ... existing code

  /**
   * Enhanced mutation for starting flows with parameters
   */
  const startFlowMutation = useMutation({
    mutationFn: ({ id, flowClass, description, parameters, onSuccess }) => {
      return socket
        .flows()
        .startFlow(id, flowClass, description, parameters)
        .then(() => {
          if (onSuccess) onSuccess();
        });
    },
    onError: (err) => {
      notify.error(err.message);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flows"] });
      notify.success("Flow started successfully");
    },
  });

  // ... rest of existing code
};

// New flow-parameters.ts state
export const useFlowParameters = (flowClassName?: string) => {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const notify = useNotification();

  const isSocketReady =
    connectionState?.status === "authenticated" ||
    connectionState?.status === "unauthenticated";

  /**
   * Query for fetching parameter definitions for a flow class
   */
  const parametersQuery = useQuery({
    queryKey: ["flow-parameters", flowClassName],
    enabled: isSocketReady && !!flowClassName,
    queryFn: async () => {
      if (!flowClassName) return null;

      // Get flow class definition first
      const flowClass = await socket.flows().getFlowClass(flowClassName);

      // Extract parameter metadata
      const parameterMetadata = flowClass.parameters || {};
      if (Object.keys(parameterMetadata).length === 0) {
        return { parameterDefinitions: {}, parameterMapping: {}, parameterMetadata: {} };
      }

      // Extract unique parameter types for fetching definitions
      const parameterTypes = [...new Set(Object.values(parameterMetadata).map(meta => meta.type))];
      const configKeys = parameterTypes.map(type => ({ type: "parameter-types", key: type }));

      const configResponse = await socket.config().getConfig(configKeys);
      const parameterDefinitions = {};

      // Parse config response to get parameter definitions
      configResponse.values?.forEach(item => {
        if (item.type === "parameter-types") {
          parameterDefinitions[item.key] = JSON.parse(item.value);
        }
      });

      // Create mapping for backwards compatibility
      const parameterMapping = {};
      Object.entries(parameterMetadata).forEach(([paramName, meta]) => {
        parameterMapping[paramName] = meta.type;
      });

      return {
        parameterDefinitions,
        parameterMapping, // Maps flow param names to definition names (backwards compatibility)
        parameterMetadata, // Full metadata with description, order, and type
      };
    },
  });

  useActivity(parametersQuery.isLoading, "Loading flow parameters");

  return {
    parameterDefinitions: parametersQuery.data?.parameterDefinitions || {},
    parameterMapping: parametersQuery.data?.parameterMapping || {},
    parameterMetadata: parametersQuery.data?.parameterMetadata || {},
    isLoading: parametersQuery.isLoading,
    isError: parametersQuery.isError,
    error: parametersQuery.error,
  };
};
```

#### 4. Parameter Validation

```typescript
// Custom hook for parameter validation
export const useParameterValidation = (
  flowClass: string,
  parameterDefinitions: ParameterDefinitions,
  parameterValues: ParameterValues
) => {
  return useMemo(() => {
    const errors: { [key: string]: string } = {};
    let isValid = true;

    Object.entries(parameterDefinitions).forEach(([paramName, schema]) => {
      const value = parameterValues[paramName];

      // Check required fields
      if (schema.required && (value === undefined || value === "")) {
        errors[paramName] = `${paramName} is required`;
        isValid = false;
        return;
      }

      // Skip validation for empty optional fields
      if (value === undefined || value === "") {
        return;
      }

      // Type validation
      if (schema.type === 'number' || schema.type === 'integer') {
        const numValue = typeof value === 'string' ? parseFloat(value) : value;
        if (isNaN(numValue)) {
          errors[paramName] = `${paramName} must be a valid number`;
          isValid = false;
          return;
        }

        if (schema.type === 'integer' && !Number.isInteger(numValue)) {
          errors[paramName] = `${paramName} must be an integer`;
          isValid = false;
          return;
        }

        // Range validation
        if (schema.minimum !== undefined && numValue < schema.minimum) {
          errors[paramName] = `${paramName} must be at least ${schema.minimum}`;
          isValid = false;
        }
        if (schema.maximum !== undefined && numValue > schema.maximum) {
          errors[paramName] = `${paramName} must be at most ${schema.maximum}`;
          isValid = false;
        }
      }

      // Enum validation
      if (schema.enum && schema.enum.length > 0) {
        if (!schema.enum.includes(value)) {
          errors[paramName] = `${paramName} must be one of: ${schema.enum.join(', ')}`;
          isValid = false;
        }
      }

      // Pattern validation for strings
      if (schema.pattern && schema.type === 'string') {
        const regex = new RegExp(schema.pattern);
        if (!regex.test(value.toString())) {
          errors[paramName] = `${paramName} format is invalid`;
          isValid = false;
        }
      }
    });

    return { isValid, errors };
  }, [parameterDefinitions, parameterValues]);
};
```

### API Integration

#### Enhanced Socket API

The socket API has been enhanced to support parameters (already implemented):

```typescript
// In trustgraph-socket.ts - already updated
startFlow(id: string, class_name: string, description: string, parameters?: { [key: string]: any }) {
  return this.api.makeRequest<FlowRequest, FlowResponse>(
    "flow",
    {
      operation: "start-flow",
      "flow-id": id,
      "class-name": class_name,
      description: description,
      parameters: parameters,
    },
    30000,
  ).then((response) => {
    if (response.error) {
      const errorMessage = typeof response.error === 'object' && response.error.message
        ? response.error.message
        : typeof response.error === 'string'
        ? response.error
        : "Flow start failed";
      throw new Error(errorMessage);
    }
    return response;
  });
}
```

#### Config API Integration

```typescript
// Fetching parameter definitions from config system
const fetchParameterDefinitions = async (definitionNames: string[]) => {
  const configKeys = definitionNames.map(name => ({
    type: "parameter-types",
    key: name
  }));

  const response = await socket.config().getConfig(configKeys);
  const definitions = {};

  response.values?.forEach(item => {
    if (item.type === "parameter-types") {
      definitions[item.key] = JSON.parse(item.value);
    }
  });

  return definitions;
};
```

## Real-World Examples

### Flow Class Example
```json
{
  "class": {
    "text-completion:{id}": {
      "model": "{llm-model}",
      "request": "non-persistent://tg/request/text-completion:{id}",
      "response": "non-persistent://tg/response/text-completion:{id}"
    }
  },
  "description": "GraphRAG, DocumentRAG, structured data + knowledge cores",
  "flow": {
    "text-completion:{id}": {
      "model": "{llm-model}",
      "temperature": "{llm-temperature}",
      "request": "non-persistent://tg/request/text-completion:{id}",
      "response": "non-persistent://tg/response/text-completion:{id}"
    }
  },
  "interfaces": { /* ... */ },
  "parameters": {
    "llm-model": {
      "description": "LLM model",
      "order": 1,
      "type": "llm-model"
    },
    "llm-rag-model": {
      "description": "LLM model for RAG",
      "order": 2,
      "type": "llm-model"
    },
    "llm-rag-temperature": {
      "description": "LLM temperature",
      "order": 3,
      "type": "llm-temperature"
    },
    "llm-temperature": {
      "description": "LLM temperature",
      "order": 3,
      "type": "llm-temperature"
    }
  },
  "tags": ["document-rag", "graph-rag"]
}
```

### Parameter Definition Examples

#### Rich Enum Parameter (LLM Model)
```json
{
  "default": "gemini-2.5-flash-lite",
  "description": "LLM model to use",
  "enum": [
    {
      "description": "Gemini 2.5 Pro",
      "id": "gemini-2.5-pro"
    },
    {
      "description": "Claude 3.5 Sonnet (via VertexAI)",
      "id": "claude-3-5-sonnet@20241022"
    }
  ],
  "required": true,
  "type": "string"
}
```

#### String Parameter (Free-form)
```json
{
  "default": "gemini-2.5-flash-lite",
  "description": "LLM model to use",
  "required": true,
  "type": "string",
  "helper": "Enter the model identifier",
  "placeholder": "e.g. gpt-4, claude-3"
}
```

#### Number Parameter Example
```json
{
  "default": 0.7,
  "description": "Temperature for model generation",
  "type": "number",
  "minimum": 0.0,
  "maximum": 2.0,
  "required": false,
  "helper": "Controls randomness of model output"
}
```

#### Boolean Parameter Example
```json
{
  "default": false,
  "description": "Enable streaming responses",
  "type": "boolean",
  "required": false,
  "helper": "Stream responses as they are generated"
}
```

### Config API Response Example
```json
{
  "values": [
    {
      "type": "parameter-types",
      "key": "llm-model",
      "value": "{\"default\": \"gemini-2.5-flash-lite\", \"description\": \"LLM model to use\", \"enum\": [{\"description\": \"Gemini 2.5 Pro\", \"id\": \"gemini-2.5-pro\"}], \"required\": true, \"type\": \"string\"}"
    }
  ]
}
```

## User Experience Design

### Form Behavior

1. **Initial State**: When CreateDialog opens, no parameters are shown
2. **Flow Class Selection**: When user selects a flow class:
   - Show loading indicator while fetching parameters
   - Display parameter form sections if parameters exist
   - Show "No additional parameters required" if none exist
3. **Parameter Input**:
   - Show validation errors in real-time
   - Disable submit button until all required parameters are valid
   - Provide clear descriptions and hints for each parameter
4. **Form Submission**:
   - Validate all parameters before submission
   - Show progress indicator during submission
   - Clear form on successful submission
   - Retain values on error for correction

### Parameter Input Types

1. **Enum Parameters (with rich options)**:
   - SelectField dropdown with `{id, description}` structure
   - Display user-friendly descriptions, store technical IDs
   - Example: "Gemini 2.5 Pro" displays, "gemini-2.5-pro" is the value
   - Supports both rich objects and simple string arrays

2. **String Parameters (no enum)**:
   - TextField for free-form text input
   - Uses `description` field as label
   - Uses `helper` field or falls back to "Enter text"
   - Uses `placeholder` field if provided

3. **Integer Parameters**:
   - TextField with `type="number"`
   - Helper text: "Enter a whole number"
   - Validates and converts to integer

4. **Number/Float Parameters**:
   - TextField with `type="number"`
   - Helper text: "Enter a number (decimals allowed)"
   - Validates and converts to float

5. **Boolean Parameters**:
   - Checkbox component
   - Helper text: "Select true or false"
   - Direct true/false values

6. **Required Parameters**:
   - Marked with asterisk (*) in label
   - Red error styling for validation failures
   - Cannot submit form without valid values

7. **Default Values**:
   - Pre-populated when form loads
   - Shows current value or default from schema

### Parameter Presets (Future Enhancement)

```typescript
// Parameter preset management component
const ParameterPresets: React.FC<{
  flowClass: string;
  onPresetLoad: (values: ParameterValues) => void;
  currentValues: ParameterValues;
}> = ({ flowClass, onPresetLoad, currentValues }) => {
  const [presets, setPresets] = useState<ParameterPreset[]>([]);
  const [presetName, setPresetName] = useState("");

  const savePreset = () => {
    const preset: ParameterPreset = {
      id: generateId(),
      name: presetName,
      flowClass,
      values: currentValues,
      createdAt: new Date(),
    };
    // Save to local storage or backend
    saveParameterPreset(preset);
    setPresets([...presets, preset]);
  };

  return (
    <Box mt={5}>
      <Text fontWeight="bold" mb={2}>Parameter Presets</Text>

      {/* Preset selection */}
      {presets.length > 0 && (
        <SelectField
          label="Load Preset"
          items={presets.map(preset => ({
            value: preset.id,
            label: preset.name,
            description: (
              <SelectOptionText title={preset.name}>
                {preset.name} - {formatDate(preset.createdAt)}
              </SelectOptionText>
            ),
          }))}
          value={[]}
          onValueChange={(values) => {
            const presetId = values[0];
            const preset = presets.find(p => p.id === presetId);
            if (preset) {
              onPresetLoad(preset.values);
            }
          }}
        />
      )}

      {/* Save current values as preset */}
      <HStack mt={3}>
        <TextField
          label="Preset Name"
          value={presetName}
          onValueChange={setPresetName}
          placeholder="Enter preset name..."
        />
        <Button
          onClick={savePreset}
          disabled={!presetName.trim() || Object.keys(currentValues).length === 0}
        >
          Save Preset
        </Button>
      </HStack>
    </Box>
  );
};
```

## Testing Strategy

### Unit Tests

1. **ParameterInputs Component Tests**:
```typescript
describe('ParameterInputs', () => {
  it('renders string parameters with TextField', () => {
    const schema = { type: 'string', description: 'Test string param' };
    render(<ParameterInputs parameterDefinitions={{ param1: schema }} ... />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('renders enum parameters with SelectField', () => {
    const schema = { type: 'string', enum: ['option1', 'option2'] };
    render(<ParameterInputs parameterDefinitions={{ param1: schema }} ... />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('validates required parameters', () => {
    const schema = { type: 'string', required: true };
    const validationErrors = { param1: 'param1 is required' };
    render(<ParameterInputs validationErrors={validationErrors} ... />);
    expect(screen.getByText('param1 is required')).toBeInTheDocument();
  });

  it('calls onParameterChange when value changes', () => {
    const mockOnChange = jest.fn();
    const schema = { type: 'string' };
    render(<ParameterInputs onParameterChange={mockOnChange} ... />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test value' } });

    expect(mockOnChange).toHaveBeenCalledWith({ param1: 'test value' });
  });
});
```

2. **Parameter Validation Tests**:
```typescript
describe('useParameterValidation', () => {
  it('validates required parameters', () => {
    const { result } = renderHook(() => useParameterValidation(
      'test-flow',
      { param1: { type: 'string', required: true } },
      {}
    ));

    expect(result.current.isValid).toBe(false);
    expect(result.current.errors.param1).toBe('param1 is required');
  });

  it('validates number ranges', () => {
    const { result } = renderHook(() => useParameterValidation(
      'test-flow',
      { param1: { type: 'number', minimum: 5, maximum: 10 } },
      { param1: 15 }
    ));

    expect(result.current.isValid).toBe(false);
    expect(result.current.errors.param1).toContain('must be at most 10');
  });

  it('validates enum values', () => {
    const { result } = renderHook(() => useParameterValidation(
      'test-flow',
      { param1: { type: 'string', enum: ['opt1', 'opt2'] } },
      { param1: 'invalid' }
    ));

    expect(result.current.isValid).toBe(false);
    expect(result.current.errors.param1).toContain('must be one of: opt1, opt2');
  });
});
```

### Integration Tests

1. **CreateDialog with Parameters**:
```typescript
describe('CreateDialog with Parameters', () => {
  it('fetches and displays parameters when flow class is selected', async () => {
    const mockFlowClass = {
      parameters: { 'model': 'llm-model', 'temp': 'temperature' }
    };
    const mockParameterDefs = {
      'llm-model': { type: 'string', enum: ['gpt-4', 'claude-3'] },
      'temperature': { type: 'number', minimum: 0, maximum: 2 }
    };

    mockSocket.flows().getFlowClass.mockResolvedValue(mockFlowClass);
    mockSocket.config().getConfig.mockResolvedValue({
      values: [
        { type: 'parameters', key: 'llm-model', value: JSON.stringify(mockParameterDefs['llm-model']) },
        { type: 'parameters', key: 'temperature', value: JSON.stringify(mockParameterDefs.temperature) }
      ]
    });

    render(<CreateDialog open={true} />);

    // Select flow class
    const flowClassSelect = screen.getByLabelText('Flow class');
    fireEvent.change(flowClassSelect, { target: { value: 'test-flow' } });

    // Wait for parameters to load and display
    await waitFor(() => {
      expect(screen.getByLabelText('model')).toBeInTheDocument();
      expect(screen.getByLabelText('temp')).toBeInTheDocument();
    });
  });

  it('submits flow with parameter values', async () => {
    // Set up mocks and render
    // Fill in form including parameters
    // Submit form
    // Verify startFlow called with correct parameters
  });

  it('prevents submission with invalid parameters', () => {
    // Set up form with required parameters
    // Leave parameters empty
    // Verify submit button is disabled
    // Verify validation errors are shown
  });
});
```

### End-to-End Tests

1. **Complete Flow Creation with Parameters**:
   - Navigate to Flows page
   - Click Create button
   - Select flow class with parameters
   - Fill in all required fields and parameters
   - Submit form
   - Verify flow appears in list
   - Verify flow has correct parameter values

2. **Parameter Validation Scenarios**:
   - Test all parameter types (string, number, boolean, enum)
   - Test required field validation
   - Test range validation for numbers
   - Test enum value validation
   - Test form reset after successful submission

## Migration Plan

### Phase 1: Core Parameter Support
1. ✅ Update FlowRequest/FlowResponse types (completed)
2. ✅ Update startFlow API method (completed)
3. ✅ Create ParameterInputs component (completed)
4. Integrate ParameterInputs into CreateDialog
5. Implement parameter fetching from config API
6. Add parameter validation logic

### Phase 2: Enhanced User Experience
1. Add loading states during parameter fetching
2. Improve validation error display
3. Add parameter descriptions and help text
4. Implement form reset on successful submission

### Phase 3: Advanced Features (Future)
1. Parameter presets and templates
2. Parameter value suggestions based on history
3. Bulk parameter import/export
4. Parameter dependency validation
5. Real-time parameter preview

## Security Considerations

1. **Parameter Validation**: All parameter validation occurs on both client and server
2. **Type Safety**: TypeScript ensures type safety for parameter values
3. **Sanitization**: Parameter values are properly sanitized before API calls
4. **Schema Validation**: Parameter schemas are validated against expected formats
5. **Error Handling**: Sensitive information is not exposed in validation errors

## Performance Considerations

1. **Lazy Loading**: Parameter definitions are only fetched when needed
2. **Caching**: Parameter definitions are cached using TanStack Query
3. **Validation Debouncing**: Real-time validation is debounced to avoid excessive computation
4. **Component Optimization**: ParameterInputs uses React.memo for performance
5. **Bundle Size**: Components are tree-shakeable and imported dynamically where possible

## Backwards Compatibility

1. **Flow Classes Without Parameters**: Existing flow classes continue to work without changes
2. **API Compatibility**: Parameter field is optional in API calls
3. **UI Graceful Degradation**: UI gracefully handles flows with no parameters
4. **Existing Flows**: Existing flows without parameters continue to function normally

## Future Enhancements

1. **Parameter Templates**: Pre-defined parameter sets for common use cases
2. **Conditional Parameters**: Parameters that appear based on other parameter values
3. **Parameter Groups**: Organize related parameters into collapsible sections
4. **Import/Export**: Bulk parameter configuration via JSON/YAML files
5. **Parameter History**: Track and suggest parameter values based on usage patterns
6. **Advanced Validation**: Custom validation rules and cross-parameter validation
7. **Parameter Documentation**: Rich documentation with examples and best practices