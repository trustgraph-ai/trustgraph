import React from "react";
import { Select, Portal, createListCollection } from "@chakra-ui/react";
import { useConversation, ChatMode } from "@trustgraph/react-state";

const ChatModeSelector = () => {
  const chatMode = useConversation((state) => state.chatMode);
  const setChatMode = useConversation((state) => state.setChatMode);

  const chatModes = [
    { value: "graph-rag", label: "Graph RAG" },
    { value: "agent", label: "Agent" },
    { value: "basic-llm", label: "Basic LLM" },
  ];

  const collection = createListCollection({ items: chatModes });

  return (
    <Select.Root
      collection={collection}
      value={[chatMode]}
      onValueChange={(e) => setChatMode(e.value[0] as ChatMode)}
      size="sm"
      width="150px"
    >
      <Select.HiddenSelect />
      <Select.Control>
        <Select.Trigger>
          <Select.ValueText />
        </Select.Trigger>
        <Select.IndicatorGroup>
          <Select.Indicator />
        </Select.IndicatorGroup>
      </Select.Control>
      <Portal>
        <Select.Positioner>
          <Select.Content>
            {chatModes.map((mode) => (
              <Select.Item item={mode} key={mode.value}>
                <Select.ItemText>{mode.label}</Select.ItemText>
                <Select.ItemIndicator />
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Portal>
    </Select.Root>
  );
};

export default ChatModeSelector;
