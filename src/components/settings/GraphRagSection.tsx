import React from "react";
import { VStack, SimpleGrid, Text, HStack, Button } from "@chakra-ui/react";
import { Network, Circle, Minimize2, Maximize2 } from "lucide-react";
import Card from "../common/Card";
import NumberField from "../common/NumberField";

interface GraphRagSectionProps {
  entityLimit: number;
  tripleLimit: number;
  maxSubgraphSize: number;
  pathLength: number;
  onEntityLimitChange: (value: number) => void;
  onTripleLimitChange: (value: number) => void;
  onMaxSubgraphSizeChange: (value: number) => void;
  onPathLengthChange: (value: number) => void;
}

const GraphRagSection: React.FC<GraphRagSectionProps> = ({
  entityLimit,
  tripleLimit,
  maxSubgraphSize,
  pathLength,
  onEntityLimitChange,
  onTripleLimitChange,
  onMaxSubgraphSizeChange,
  onPathLengthChange,
}) => {
  // Preset configurations
  const presets = {
    small: {
      entityLimit: 10,
      tripleLimit: 10,
      maxSubgraphSize: 100,
      pathLength: 1,
    },
    medium: {
      entityLimit: 20,
      tripleLimit: 20,
      maxSubgraphSize: 400,
      pathLength: 2,
    },
    large: {
      entityLimit: 50,
      tripleLimit: 30,
      maxSubgraphSize: 1000,
      pathLength: 2,
    },
  };

  const applyPreset = (preset: keyof typeof presets) => {
    const config = presets[preset];
    onEntityLimitChange(config.entityLimit);
    onTripleLimitChange(config.tripleLimit);
    onMaxSubgraphSizeChange(config.maxSubgraphSize);
    onPathLengthChange(config.pathLength);
  };
  return (
    <Card
      title="GraphRAG Configuration"
      description="Configure entity limits, triple limits, and graph traversal settings"
      icon={<Network />}
    >
      <VStack gap={4} align="stretch">
        <VStack gap={3} align="stretch">
          <Text fontSize="sm" fontWeight="medium" color="fg.muted">
            Quick Presets
          </Text>
          <HStack gap={2} justify="center">
            <Button
              size="sm"
              variant="solid"
              colorPalette="accent"
              onClick={() => applyPreset("small")}
            >
              <Minimize2 />
              Small
            </Button>
            <Button
              size="sm"
              variant="solid"
              colorPalette="accent"
              onClick={() => applyPreset("medium")}
            >
              <Circle />
              Medium
            </Button>
            <Button
              size="sm"
              variant="solid"
              colorPalette="accent"
              onClick={() => applyPreset("large")}
            >
              <Maximize2 />
              Large
            </Button>
          </HStack>
        </VStack>

        <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
          <VStack gap={2} align="stretch">
            <NumberField
              label="Entity Limit"
              value={entityLimit}
              onValueChange={onEntityLimitChange}
              minValue={1}
              maxValue={1000}
            />
            <Text fontSize="sm" color="fg.muted">
              Maximum number of entities to include in graph queries
            </Text>
          </VStack>

          <VStack gap={2} align="stretch">
            <NumberField
              label="Triple Limit"
              value={tripleLimit}
              onValueChange={onTripleLimitChange}
              minValue={1}
              maxValue={500}
            />
            <Text fontSize="sm" color="fg.muted">
              Maximum number of triples to retrieve per query
            </Text>
          </VStack>

          <VStack gap={2} align="stretch">
            <NumberField
              label="Max Subgraph Size"
              value={maxSubgraphSize}
              onValueChange={onMaxSubgraphSizeChange}
              minValue={100}
              maxValue={10000}
            />
            <Text fontSize="sm" color="fg.muted">
              Maximum size of subgraphs for processing
            </Text>
          </VStack>

          <VStack gap={2} align="stretch">
            <NumberField
              label="Path Length"
              value={pathLength}
              onValueChange={onPathLengthChange}
              minValue={1}
              maxValue={10}
            />
            <Text fontSize="sm" color="fg.muted">
              Maximum path length for graph traversal
            </Text>
          </VStack>
        </SimpleGrid>
      </VStack>
    </Card>
  );
};

export default GraphRagSection;
