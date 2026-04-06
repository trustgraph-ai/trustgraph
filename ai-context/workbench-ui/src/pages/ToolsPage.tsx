import React from "react";
import { Hammer } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import Tools from "../components/agents/Tools";

const ToolsPage = () => {
  return (
    <>
      <PageHeader
        icon={<Hammer />}
        title="Agent Tools Configuration"
        description="Agent tools equip the agent framework to work with your data"
      />
      <Tools />
    </>
  );
};

export default ToolsPage;
