import { MessageCircleCode } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import Prompts from "../components/prompts/Prompts";

const PromptsPage = () => {
  return (
    <>
      <PageHeader
        icon={<MessageCircleCode />}
        title="Prompt Management"
        description="Define prompts which control AI interactions"
      />
      <Prompts />
    </>
  );
};

export default PromptsPage;
