import React from "react";
import { VStack, HStack, Text, Switch, Tag } from "@chakra-ui/react";
import { ToggleLeft } from "lucide-react";
import Card from "../common/Card";

interface FeatureSwitchesSectionProps {
  ontologyEditor: boolean;
  submissions: boolean;
  agentTools: boolean;
  mcpTools: boolean;
  schemas: boolean;
  tokenCost: boolean;
  flowClasses: boolean;
  structuredQuery: boolean;
  llmModels: boolean;
  onOntologyEditorChange: (enabled: boolean) => void;
  onSubmissionsChange: (enabled: boolean) => void;
  onAgentToolsChange: (enabled: boolean) => void;
  onMcpToolsChange: (enabled: boolean) => void;
  onSchemasChange: (enabled: boolean) => void;
  onTokenCostChange: (enabled: boolean) => void;
  onFlowClassesChange: (enabled: boolean) => void;
  onStructuredQueryChange: (enabled: boolean) => void;
  onLlmModelsChange: (enabled: boolean) => void;
}

const FeatureSwitchesSection: React.FC<FeatureSwitchesSectionProps> = ({
  ontologyEditor,
  submissions,
  agentTools,
  mcpTools,
  schemas,
  tokenCost,
  flowClasses,
  structuredQuery,
  llmModels,
  onOntologyEditorChange,
  onSubmissionsChange,
  onAgentToolsChange,
  onMcpToolsChange,
  onSchemasChange,
  onTokenCostChange,
  onFlowClassesChange,
  onStructuredQueryChange,
  onLlmModelsChange,
}) => {
  return (
    <Card
      title="Feature Switches"
      description="Enable or disable advanced and experimental features"
      icon={<ToggleLeft />}
    >
      <VStack gap={4} align="stretch">
        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Ontology Editor</Text>
            <HStack gap={2} align="center">
              <Text fontSize="sm" color="fg.muted">
                Enable the ontology management interface for SKOS concepts
              </Text>
              <Tag.Root colorPalette="accent" size="sm">
                <Tag.Label>preview</Tag.Label>
              </Tag.Root>
            </HStack>
          </VStack>
          <Switch.Root
            checked={ontologyEditor}
            onCheckedChange={(details) =>
              onOntologyEditorChange(details.checked)
            }
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Submissions</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the submissions page
            </Text>
          </VStack>
          <Switch.Root
            checked={submissions}
            onCheckedChange={(details) => onSubmissionsChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Agent Tools</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the agent tools configuration interface
            </Text>
          </VStack>
          <Switch.Root
            checked={agentTools}
            onCheckedChange={(details) => onAgentToolsChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">MCP Tools</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the MCP (Model Context Protocol) tools interface
            </Text>
          </VStack>
          <Switch.Root
            checked={mcpTools}
            onCheckedChange={(details) => onMcpToolsChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Schemas</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the schemas management interface for structured data
            </Text>
          </VStack>
          <Switch.Root
            checked={schemas}
            onCheckedChange={(details) => onSchemasChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Token Cost</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the token cost tracking and analysis interface
            </Text>
          </VStack>
          <Switch.Root
            checked={tokenCost}
            onCheckedChange={(details) => onTokenCostChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Flow Classes</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the flow classes management interface for dataflow
              definitions
            </Text>
          </VStack>
          <Switch.Root
            checked={flowClasses}
            onCheckedChange={(details) => onFlowClassesChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">Structured Query</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the structured query interface for building and executing
              complex queries
            </Text>
          </VStack>
          <Switch.Root
            checked={structuredQuery}
            onCheckedChange={(details) =>
              onStructuredQueryChange(details.checked)
            }
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>

        <HStack justify="space-between" align="center">
          <VStack gap={1} align="start">
            <Text fontWeight="medium">LLM Models</Text>
            <Text fontSize="sm" color="fg.muted">
              Enable the LLM models editor for managing available model options
            </Text>
          </VStack>
          <Switch.Root
            checked={llmModels}
            onCheckedChange={(details) => onLlmModelsChange(details.checked)}
          >
            <Switch.HiddenInput />
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
          </Switch.Root>
        </HStack>
      </VStack>
    </Card>
  );
};

export default FeatureSwitchesSection;
