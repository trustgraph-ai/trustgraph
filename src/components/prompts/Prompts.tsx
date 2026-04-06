import React, { useState } from "react";

import { Tabs } from "@chakra-ui/react";

import { usePrompts } from "@trustgraph/react-state";

import EditDialog from "./EditDialog";
import PromptControls from "./PromptControls";
import EditSystemPrompt from "./EditSystemPrompt";
import PromptsTable from "./PromptsTable";
import SystemPrompt from "./SystemPrompt";

const Prompts = () => {
  const promptsState = usePrompts();

  const [selected, setSelected] = useState("");
  const [systemEdit, setSystemEdit] = useState(false);

  const onSelect = (row) => {
    setSelected(row[0]);
  };

  const onComplete = () => {
    setSelected("");
    setSystemEdit(false);
  };

  const onSystemEdit = () => {
    setSystemEdit(true);
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
      <EditSystemPrompt
        open={systemEdit}
        onOpenChange={() => setSystemEdit(false)}
        onComplete={() => onComplete()}
      />
      <Tabs.Root defaultValue="prompts">
        <Tabs.List>
          <Tabs.Trigger value="prompts">Prompt templates</Tabs.Trigger>
          <Tabs.Trigger value="system">System prompt</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="prompts">
          <PromptsTable
            prompts={promptsState.prompts}
            onSelect={(row) => onSelect(row)}
          />
          <PromptControls />
        </Tabs.Content>
        <Tabs.Content value="system">
          <SystemPrompt
            prompt={promptsState.systemPrompt || ""}
            onEdit={onSystemEdit}
          />
        </Tabs.Content>
      </Tabs.Root>
    </>
  );
};

export default Prompts;
