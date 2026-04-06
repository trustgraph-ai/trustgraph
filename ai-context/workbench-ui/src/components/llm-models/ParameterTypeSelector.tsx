import React from "react";
import { VStack, Text, Select, createListCollection } from "@chakra-ui/react";
import { LLMModelParameter } from "@trustgraph/react-state";

interface ParameterTypeSelectorProps {
  parameterTypes: LLMModelParameter[];
  selectedType: string;
  onSelectType: (type: string) => void;
}

const ParameterTypeSelector: React.FC<ParameterTypeSelectorProps> = ({
  parameterTypes,
  selectedType,
  onSelectType,
}) => {
  const collection = createListCollection({
    items: parameterTypes.map((pt) => ({
      label: pt.name,
      value: pt.name,
    })),
  });

  return (
    <VStack gap={2} align="stretch">
      <Text fontSize="sm" fontWeight="medium">
        Parameter Type
      </Text>
      <Select.Root
        collection={collection}
        value={[selectedType]}
        onValueChange={(e) => onSelectType(e.value[0])}
        size="sm"
        width="300px"
      >
        <Select.HiddenSelect />
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="Select a parameter type" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
          </Select.IndicatorGroup>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {parameterTypes.map((pt) => (
              <Select.Item key={pt.name} item={pt.name}>
                {pt.name}
                <Select.ItemIndicator />
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>
    </VStack>
  );
};

export default ParameterTypeSelector;
