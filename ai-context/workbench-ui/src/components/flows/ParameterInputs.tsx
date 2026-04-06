import React, { useState, useEffect } from "react";
import {
  Box,
  Text,
  Field,
  Checkbox,
  Button,
  Collapsible,
  HStack,
} from "@chakra-ui/react";
import { ChevronDown, ChevronRight, Link2 } from "lucide-react";
import TextField from "../common/TextField";
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";

// Rich enum option structure
interface EnumOption {
  id: string; // The actual value
  description: string; // Display text
}

interface ParameterSchema {
  type: "string" | "number" | "integer" | "boolean";
  description?: string;
  default?: unknown;
  enum?: EnumOption[] | string[]; // Can be rich objects or simple strings
  minimum?: number;
  maximum?: number;
  pattern?: string;
  required?: boolean;
  helper?: string; // Custom helper text
  placeholder?: string; // Custom placeholder text
}

// Flow parameter metadata (stored in flow class)
interface FlowParameterMetadata {
  description: string;
  order: number;
  type: string; // Reference to parameter definition name
  advanced?: boolean; // If true, parameter is shown in collapsible advanced section
  "controlled-by"?: string; // Name of parameter that controls this parameter's value
}

interface ParameterInputsProps {
  parameterDefinitions: { [key: string]: ParameterSchema }; // The actual definitions
  parameterMapping: { [key: string]: string }; // Maps flow param names to definition names
  parameterMetadata: { [key: string]: FlowParameterMetadata }; // Flow-specific metadata
  parameterValues: { [key: string]: unknown };
  onParameterChange: (values: { [key: string]: unknown }) => void;
  validationErrors: { [key: string]: string };
  contentRef?: React.RefObject<HTMLDivElement>;
}

const ParameterInputs: React.FC<ParameterInputsProps> = ({
  parameterDefinitions,
  parameterMapping,
  parameterMetadata,
  parameterValues,
  onParameterChange,
  validationErrors,
  contentRef,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [explicitlySetParams, setExplicitlySetParams] = useState<Set<string>>(
    new Set(),
  );

  // Initialize controlled parameter values when component mounts or dependencies change
  useEffect(() => {
    if (
      !parameterMetadata ||
      !parameterDefinitions ||
      Object.keys(parameterMapping).length === 0
    ) {
      return;
    }

    const needsUpdate = Object.entries(parameterMetadata).some(
      ([paramName, metadata]) => {
        if (metadata["controlled-by"]) {
          const hasExplicitValue =
            parameterValues[paramName] !== undefined &&
            parameterValues[paramName] !== "";
          if (!hasExplicitValue) {
            const resolvedValue = resolveParameterValue(
              paramName,
              parameterValues,
            );
            return resolvedValue !== parameterValues[paramName];
          }
        }
        return false;
      },
    );

    if (needsUpdate) {
      const updatedValues = { ...parameterValues };
      Object.entries(parameterMetadata).forEach(([paramName, metadata]) => {
        if (metadata["controlled-by"]) {
          const hasExplicitValue =
            parameterValues[paramName] !== undefined &&
            parameterValues[paramName] !== "";
          if (!hasExplicitValue) {
            const resolvedValue = resolveParameterValue(
              paramName,
              parameterValues,
            );
            if (resolvedValue !== parameterValues[paramName]) {
              updatedValues[paramName] = resolvedValue;
            }
          }
        }
      });
      onParameterChange(updatedValues);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parameterMetadata, parameterDefinitions, parameterMapping]);

  // Early return after all hooks to avoid hook order violation
  if (!parameterMapping || Object.keys(parameterMapping).length === 0) {
    return null;
  }

  // Debug logging
  console.log("[ParameterInputs] Parameter metadata:", parameterMetadata);
  console.log("[ParameterInputs] Parameter mapping:", parameterMapping);
  console.log("[ParameterInputs] Parameter values:", parameterValues);

  // Detect circular dependencies in controlled-by relationships
  const detectCircularDependencies = (
    paramName: string,
    visited: Set<string> = new Set(),
    path: string[] = [],
  ): string[] | null => {
    if (visited.has(paramName)) {
      const cycleStart = path.indexOf(paramName);
      return path.slice(cycleStart).concat(paramName);
    }

    const metadata = parameterMetadata[paramName];
    if (!metadata || !metadata["controlled-by"]) {
      return null;
    }

    visited.add(paramName);
    path.push(paramName);

    return detectCircularDependencies(
      metadata["controlled-by"],
      visited,
      path,
    );
  };

  // Resolve parameter value considering controlled-by relationships
  const resolveParameterValue = (
    paramName: string,
    currentValues: { [key: string]: unknown },
  ): unknown => {
    // Check for circular dependencies first
    const cycle = detectCircularDependencies(paramName);
    if (cycle) {
      console.warn(
        `Circular dependency detected in controlled-by chain: ${cycle.join(" -> ")}`,
      );
      return (
        currentValues[paramName] ??
        parameterDefinitions[parameterMapping[paramName]]?.default ??
        ""
      );
    }

    const metadata = parameterMetadata[paramName];
    const schema = parameterDefinitions[parameterMapping[paramName]];

    // If parameter has explicit value, use it
    if (
      currentValues[paramName] !== undefined &&
      currentValues[paramName] !== ""
    ) {
      return currentValues[paramName];
    }

    // If parameter is controlled by another parameter, inherit its value
    if (metadata && metadata["controlled-by"]) {
      const controllerName = metadata["controlled-by"];
      const controllerValue = resolveParameterValue(
        controllerName,
        currentValues,
      );
      if (controllerValue !== undefined && controllerValue !== "") {
        return controllerValue;
      }
    }

    // Fall back to default value from schema
    return schema?.default ?? "";
  };

  // Get all parameters that are controlled by a given parameter
  const getControlledParameters = (controllerName: string): string[] => {
    return Object.entries(parameterMetadata)
      .filter(([_, metadata]) => metadata["controlled-by"] === controllerName)
      .map(([paramName]) => paramName);
  };

  const handleParameterChange = (paramName: string, value: unknown) => {
    console.log(
      `[ParameterInputs] Changing parameter ${paramName} to:`,
      value,
    );

    // Mark this parameter as explicitly set by user
    const newExplicitParams = new Set(explicitlySetParams);
    newExplicitParams.add(paramName);
    setExplicitlySetParams(newExplicitParams);

    const newValues = { ...parameterValues, [paramName]: value };

    // Update controlled parameters
    const controlledParams = getControlledParameters(paramName);
    console.log(
      `[ParameterInputs] Found ${controlledParams.length} controlled parameters:`,
      controlledParams,
    );

    for (const controlledParam of controlledParams) {
      const currentValue = parameterValues[controlledParam];
      const isExplicitlySet = explicitlySetParams.has(controlledParam);

      console.log(
        `[ParameterInputs] Controlled param ${controlledParam}: current="${currentValue}", isExplicit=${isExplicitlySet}`,
      );

      // Only update if the controlled parameter hasn't been explicitly set by user
      if (!isExplicitlySet) {
        console.log(
          `[ParameterInputs] Setting ${controlledParam} = ${value} (inherited from ${paramName})`,
        );
        newValues[controlledParam] = value;
      } else {
        console.log(
          `[ParameterInputs] Skipping ${controlledParam} - user has explicitly set it`,
        );
      }
    }

    console.log(`[ParameterInputs] Final parameter values:`, newValues);
    onParameterChange(newValues);
  };

  const renderParameterInput = (
    flowParamName: string,
    definitionName: string,
  ) => {
    const schema = parameterDefinitions[definitionName];
    const metadata = parameterMetadata[flowParamName];
    if (!schema) {
      return null;
    }
    const defaultValue = schema.default;
    const resolvedValue = resolveParameterValue(
      flowParamName,
      parameterValues,
    );
    const value = resolvedValue ?? defaultValue ?? "";
    const error = validationErrors[flowParamName];

    // Check if this parameter is inheriting its value
    const isInheriting =
      metadata &&
      metadata["controlled-by"] &&
      !explicitlySetParams.has(flowParamName);
    const controllerName = metadata?.["controlled-by"];

    // Use metadata description if available, fallback to schema description, then parameter name
    const description = metadata?.description || schema.description;
    const label = description || flowParamName;

    // Helper text priority: inheritance info -> schema.helper -> type-based fallback
    const getHelperText = () => {
      let baseHelperText = schema.helper;

      if (!baseHelperText) {
        switch (schema.type) {
          case "integer":
            baseHelperText = "Enter a whole number";
            break;
          case "number":
            baseHelperText = "Enter a number (decimals allowed)";
            break;
          case "boolean":
            baseHelperText = "Select true or false";
            break;
          case "string":
            baseHelperText = schema.enum ? undefined : "Enter text";
            break;
          default:
            baseHelperText = undefined;
        }
      }

      // Add inheritance info if applicable
      if (isInheriting && controllerName) {
        const inheritanceText = `Inherits from "${controllerName}"`;
        return baseHelperText
          ? `${baseHelperText}. ${inheritanceText}`
          : inheritanceText;
      }

      return baseHelperText;
    };

    const helperText = getHelperText();
    const placeholder = schema.placeholder || "";

    // Helper component to show inheritance indicator
    const renderInheritanceIndicator = () => {
      if (!isInheriting || !controllerName) return null;

      return (
        <HStack gap={1} mt={1}>
          <Link2 size={12} style={{ color: "var(--colors-fg-muted)" }} />
          <Text fontSize="xs" color="fg.muted">
            Inherits from {controllerName}
          </Text>
        </HStack>
      );
    };

    // Enum parameters - handle both rich {id, description} and simple string arrays
    if (schema.enum && schema.enum.length > 0) {
      const options = schema.enum.map((option) => {
        // Handle both rich {id, description} and simple string enums
        const optionId = typeof option === "object" ? option.id : option;
        const optionDesc =
          typeof option === "object" ? option.description : option;

        return {
          value: optionId,
          label: optionDesc,
          description: (
            <SelectOptionText title={optionDesc}>
              {optionDesc}
            </SelectOptionText>
          ),
        };
      });

      return (
        <Box key={flowParamName} mt={5}>
          <SelectField
            label={schema.required ? `${label} *` : label}
            items={options}
            value={value ? [value.toString()] : []}
            onValueChange={(values) => {
              const selectedValue = values.length > 0 ? values[0] : "";
              handleParameterChange(flowParamName, selectedValue);
            }}
            contentRef={contentRef}
          />
          {error && (
            <Text color="red.500" fontSize="sm" mt={1}>
              {error}
            </Text>
          )}
          {helperText && (
            <Text fontSize="sm" color="fg.muted" mt={1}>
              {helperText}
            </Text>
          )}
          {renderInheritanceIndicator()}
        </Box>
      );
    }

    // Boolean parameters - use Checkbox
    if (schema.type === "boolean") {
      return (
        <Box key={flowParamName} mt={5}>
          <Field.Root>
            <Checkbox
              checked={value}
              onChange={(e) =>
                handleParameterChange(flowParamName, e.target.checked)
              }
            >
              {schema.required ? `${label} *` : label}
            </Checkbox>
            {helperText && <Field.HelperText>{helperText}</Field.HelperText>}
            {error && (
              <Text color="red.500" fontSize="sm" mt={1}>
                {error}
              </Text>
            )}
          </Field.Root>
          {renderInheritanceIndicator()}
        </Box>
      );
    }

    // Number/Integer parameters - use TextField with type="number"
    if (schema.type === "number" || schema.type === "integer") {
      let enhancedHelperText = helperText;
      if (schema.minimum !== undefined || schema.maximum !== undefined) {
        const rangeText = [];
        if (schema.minimum !== undefined)
          rangeText.push(`min: ${schema.minimum}`);
        if (schema.maximum !== undefined)
          rangeText.push(`max: ${schema.maximum}`);
        const rangeInfo = rangeText.join(", ");
        enhancedHelperText = enhancedHelperText
          ? `${enhancedHelperText} (${rangeInfo})`
          : rangeInfo;
      }

      return (
        <Box key={flowParamName} mt={5}>
          <TextField
            label={label}
            helperText={enhancedHelperText}
            placeholder={placeholder}
            value={value.toString()}
            onValueChange={(val) => {
              // Store as string since backend expects string-encoded values
              handleParameterChange(flowParamName, val);
            }}
            type="number"
            required={schema.required}
          />
          {error && (
            <Text color="red.500" fontSize="sm" mt={1}>
              {error}
            </Text>
          )}
          {renderInheritanceIndicator()}
        </Box>
      );
    }

    // String parameters - use TextField
    return (
      <Box key={flowParamName} mt={5}>
        <TextField
          label={label}
          helperText={helperText}
          placeholder={placeholder}
          value={value.toString()}
          onValueChange={(val) => handleParameterChange(flowParamName, val)}
          required={schema.required}
        />
        {error && (
          <Text color="red.500" fontSize="sm" mt={1}>
            {error}
          </Text>
        )}
        {renderInheritanceIndicator()}
      </Box>
    );
  };

  // Sort parameters by order field from metadata and separate basic vs advanced
  const sortedParameters = Object.entries(parameterMapping).sort(
    ([paramNameA], [paramNameB]) => {
      const orderA = parameterMetadata[paramNameA]?.order || 999;
      const orderB = parameterMetadata[paramNameB]?.order || 999;
      return orderA - orderB;
    },
  );

  // Separate basic and advanced parameters
  const basicParameters = sortedParameters.filter(
    ([paramName]) => !parameterMetadata[paramName]?.advanced,
  );

  const advancedParameters = sortedParameters.filter(
    ([paramName]) => parameterMetadata[paramName]?.advanced === true,
  );

  return (
    <Box>
      <Box mt={5} mb={3} fontWeight="bold">
        Parameters:
      </Box>

      {/* Basic Parameters */}
      {basicParameters.map(([flowParamName, definitionName]) =>
        renderParameterInput(flowParamName, definitionName),
      )}

      {/* Advanced Parameters Section */}
      {advancedParameters.length > 0 && (
        <Box mt={6}>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            p={0}
            h="auto"
            minH="auto"
            fontWeight="normal"
            color="fg.muted"
            _hover={{ color: "fg" }}
          >
            <HStack gap={1}>
              {showAdvanced ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
              <Text fontSize="sm">Advanced Settings</Text>
            </HStack>
          </Button>

          <Collapsible.Root open={showAdvanced}>
            <Collapsible.Content>
              <Box
                mt={3}
                pl={6}
                borderLeft="2px solid"
                borderColor="border.muted"
              >
                {advancedParameters.map(([flowParamName, definitionName]) =>
                  renderParameterInput(flowParamName, definitionName),
                )}
              </Box>
            </Collapsible.Content>
          </Collapsible.Root>
        </Box>
      )}
    </Box>
  );
};

export default ParameterInputs;
