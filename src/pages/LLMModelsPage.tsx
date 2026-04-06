import React from "react";
import { Bot } from "lucide-react";
import PageHeader from "../components/common/PageHeader";
import LLMModels from "../components/llm-models/LLMModels";

const LLMModelsPage: React.FC = () => {
  return (
    <>
      <PageHeader
        icon={<Bot />}
        title="LLM Models"
        description="Manage available LLM model options and set the default model"
      />
      <LLMModels />
    </>
  );
};

export default LLMModelsPage;
