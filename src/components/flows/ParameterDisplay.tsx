import React, { useMemo } from "react";
import { Text, Badge, Flex } from "@chakra-ui/react";
import { useFlows } from "@trustgraph/react-state";
import { useFlowParameters } from "@trustgraph/react-state";

interface ParameterDisplayProps {
  flowClassName: string;
  parameters: { [key: string]: unknown } | undefined;
}

/**
 * Component for displaying flow parameters with descriptive names and values
 * Looks up parameter metadata from flow class to show descriptions instead of identifiers
 * Also maps enum values to their descriptions when available
 */
const ParameterDisplay: React.FC<ParameterDisplayProps> = ({
  flowClassName,
  parameters,
}) => {
  const { flowClasses } = useFlows();

  // Fetch parameter definitions to get enum mappings
  const { parameterDefinitions, parameterMapping } =
    useFlowParameters(flowClassName);

  // Find the flow class metadata
  const flowClass = Array.isArray(flowClasses)
    ? flowClasses.find(
        (fc) => Array.isArray(fc) && fc[0] === flowClassName,
      )?.[1]
    : undefined;
  const parameterMetadata = useMemo(
    () => flowClass?.parameters || {},
    [flowClass],
  );

  // Create a mapping of parameter values to display values
  const displayValues = useMemo(() => {
    const result: { [key: string]: string } = {};

    if (!parameters) return result;

    Object.entries(parameters).forEach(([paramName, paramValue]) => {
      // Get the parameter definition name from mapping
      const definitionName = parameterMapping[paramName];
      const definition = definitionName
        ? parameterDefinitions[definitionName]
        : null;

      // If parameter has enum options, try to find the description
      if (definition?.enum && Array.isArray(definition.enum)) {
        const enumOption = definition.enum.find((option) => {
          // Handle both rich {id, description} and simple string enums
          const optionId = typeof option === "object" ? option.id : option;
          return optionId === paramValue;
        });

        if (enumOption) {
          // Use description if available, otherwise use the value itself
          result[paramName] =
            typeof enumOption === "object"
              ? enumOption.description
              : enumOption;
        } else {
          result[paramName] = String(paramValue);
        }
      } else {
        result[paramName] = String(paramValue);
      }
    });

    return result;
  }, [parameters, parameterDefinitions, parameterMapping]);

  // Sort parameters by order field from metadata
  const sortedParameterEntries = useMemo(() => {
    return Object.entries(parameters).sort(([keyA], [keyB]) => {
      const orderA = parameterMetadata[keyA]?.order || 999;
      const orderB = parameterMetadata[keyB]?.order || 999;
      return orderA - orderB;
    });
  }, [parameters, parameterMetadata]);

  // Array of color palettes to cycle through for visual distinction
  const colorPalettes = [
    "blue",
    "teal",
    "purple",
    "green",
    "orange",
    "pink",
    "cyan",
  ];

  // Display parameters as compact badges that can wrap
  return (
    <Flex wrap="wrap" gap={1.5} maxWidth="400px">
      {sortedParameterEntries.map(([key, value], index) => {
        // Use parameter description if available, otherwise fall back to key
        const displayName = parameterMetadata[key]?.description || key;
        const displayValue = displayValues[key] || String(value);
        // Cycle through color palettes for visual distinction
        const colorPalette = colorPalettes[index % colorPalettes.length];

        return (
          <Badge
            key={key}
            colorPalette={colorPalette}
            variant="subtle"
            size="sm"
            px={2}
            py={0.5}
            borderRadius="md"
          >
            <Text fontSize="xs">
              <Text as="span" fontWeight="semibold">
                {displayName}:
              </Text>{" "}
              <Text as="span">{displayValue}</Text>
            </Text>
          </Badge>
        );
      })}
    </Flex>
  );
};

export default ParameterDisplay;
