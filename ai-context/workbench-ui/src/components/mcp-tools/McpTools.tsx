import React, { useState } from "react";

import { useMcpTools } from "@trustgraph/react-state";
import EditDialog from "./EditDialog";
import Controls from "./Controls";
import McpToolsTable from "./McpToolsTable";

const McpTools = () => {
  const toolsState = useMcpTools();
  const [selected, setSelected] = useState("");

  const onComplete = () => {
    setSelected("");
  };

  return (
    <>
      <EditDialog
        open={selected != ""}
        onOpenChange={() => setSelected("")}
        onComplete={() => onComplete()}
        create={false}
        id={selected}
      />
      <McpToolsTable
        selected={selected}
        setSelected={setSelected}
        tools={toolsState.tools}
      />
      <Controls />
    </>
  );
};

export default McpTools;
