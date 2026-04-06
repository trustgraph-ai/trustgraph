import React from "react";
import { Box, Text } from "@chakra-ui/react";
import { useLLMModels } from "@trustgraph/react-state";
import ModelsTable from "./ModelsTable";
import { EnumOption } from "@trustgraph/react-state";

const LLMModels: React.FC = () => {
  const { parameterTypes, updateParameter, isUpdating } = useLLMModels();

  const llmModelParam = parameterTypes[0]; // We only fetch llm-model

  const handleUpdate = (models: EnumOption[], defaultValue: string) => {
    updateParameter({
      name: "llm-model",
      enum: models,
      default: defaultValue,
    });
  };

  if (!llmModelParam) {
    return (
      <Box>
        <Text color="fg.muted">
          LLM model parameter type not found. Please configure the llm-model
          parameter type in your system.
        </Text>
      </Box>
    );
  }

  return (
    <Box>
      <ModelsTable
        models={llmModelParam.enum}
        defaultValue={llmModelParam.default}
        onUpdate={handleUpdate}
        isUpdating={isUpdating}
      />
    </Box>
  );
};

export default LLMModels;
