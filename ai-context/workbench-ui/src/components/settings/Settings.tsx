import React from "react";
import { VStack, HStack, Button } from "@chakra-ui/react";
import { RotateCcw, Download, Upload } from "lucide-react";
import { useSettings } from "@trustgraph/react-state";
import { useNotification } from "@trustgraph/react-state";
import UserSection from "./UserSection";
import AuthenticationSection from "./AuthenticationSection";
import GraphRagSection from "./GraphRagSection";
import FeatureSwitchesSection from "./FeatureSwitchesSection";

const Settings: React.FC = () => {
  const {
    settings,
    updateSetting,
    resetSettings,
    exportSettings,
    importSettings,
    isSaving,
  } = useSettings();

  const notify = useNotification();

  const handleReset = async () => {
    try {
      resetSettings();
      notify.success("Settings reset to defaults successfully");
    } catch {
      notify.error("Failed to reset settings");
    }
  };

  const handleExport = () => {
    try {
      const settingsJson = exportSettings();
      const blob = new Blob([settingsJson], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "trustgraph-settings.json";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      notify.success("Settings exported successfully");
    } catch {
      notify.error("Failed to export settings");
    }
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const content = e.target?.result as string;
            importSettings(content);
            notify.success("Settings imported successfully");
          } catch {
            notify.error("Failed to import settings - invalid format");
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  // Loading state is handled by useActivity in the settings hook
  // CenterSpinner component automatically shows when activities are active

  return (
    <VStack gap={6} align="stretch" p={6} maxW="4xl" mx="auto">
      <HStack justify="flex-end" gap={2}>
        <Button variant="outline" onClick={handleImport} leftIcon={<Upload />}>
          Import
        </Button>
        <Button
          variant="outline"
          onClick={handleExport}
          leftIcon={<Download />}
        >
          Export
        </Button>
        <Button
          variant="outline"
          colorPalette="red"
          onClick={handleReset}
          leftIcon={<RotateCcw />}
        >
          Reset to Defaults
        </Button>
      </HStack>

      <UserSection
        user={settings.user}
        onUserChange={(value) => updateSetting("user", value)}
        isSaving={isSaving}
      />

      <AuthenticationSection
        apiKey={settings.authentication.apiKey}
        onApiKeyChange={(value) =>
          updateSetting("authentication.apiKey", value)
        }
        isSaving={isSaving}
      />

      <GraphRagSection
        entityLimit={settings.graphrag.entityLimit}
        tripleLimit={settings.graphrag.tripleLimit}
        maxSubgraphSize={settings.graphrag.maxSubgraphSize}
        pathLength={settings.graphrag.pathLength}
        onEntityLimitChange={(value) =>
          updateSetting("graphrag.entityLimit", value)
        }
        onTripleLimitChange={(value) =>
          updateSetting("graphrag.tripleLimit", value)
        }
        onMaxSubgraphSizeChange={(value) =>
          updateSetting("graphrag.maxSubgraphSize", value)
        }
        onPathLengthChange={(value) =>
          updateSetting("graphrag.pathLength", value)
        }
      />

      <FeatureSwitchesSection
        ontologyEditor={settings.featureSwitches.ontologyEditor}
        submissions={settings.featureSwitches.submissions}
        agentTools={settings.featureSwitches.agentTools}
        mcpTools={settings.featureSwitches.mcpTools}
        schemas={settings.featureSwitches.schemas}
        tokenCost={settings.featureSwitches.tokenCost}
        flowClasses={settings.featureSwitches.flowClasses}
        structuredQuery={settings.featureSwitches.structuredQuery}
        llmModels={settings.featureSwitches.llmModels}
        onOntologyEditorChange={(value) =>
          updateSetting("featureSwitches.ontologyEditor", value)
        }
        onSubmissionsChange={(value) =>
          updateSetting("featureSwitches.submissions", value)
        }
        onAgentToolsChange={(value) =>
          updateSetting("featureSwitches.agentTools", value)
        }
        onMcpToolsChange={(value) =>
          updateSetting("featureSwitches.mcpTools", value)
        }
        onSchemasChange={(value) =>
          updateSetting("featureSwitches.schemas", value)
        }
        onTokenCostChange={(value) =>
          updateSetting("featureSwitches.tokenCost", value)
        }
        onFlowClassesChange={(value) =>
          updateSetting("featureSwitches.flowClasses", value)
        }
        onStructuredQueryChange={(value) =>
          updateSetting("featureSwitches.structuredQuery", value)
        }
        onLlmModelsChange={(value) =>
          updateSetting("featureSwitches.llmModels", value)
        }
      />
    </VStack>
  );
};

export default Settings;
