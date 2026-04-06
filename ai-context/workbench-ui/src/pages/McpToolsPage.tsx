import React from "react";
import { Plug } from "lucide-react";

import PageHeader from "../components/common/PageHeader";
import McpTools from "../components/mcp-tools/McpTools";

const McpToolsPage = () => {
  return (
    <>
      <PageHeader
        icon={<Plug />}
        title="MCP Tools Configuration"
        description="Makes MCP tools available for agent integration"
      />
      <McpTools />
    </>
  );
};

export default McpToolsPage;
