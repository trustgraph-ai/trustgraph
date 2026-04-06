import React from "react";

import { Popover, Text, IconButton, Portal } from "@chakra-ui/react";
import { CircleHelp } from "lucide-react";

const ChatHelp = () => {
  return (
    <Popover.Root size="md" variant="outline">
      <Popover.Trigger asChild>
        <IconButton size="lg" ml={10}>
          <CircleHelp />
        </IconButton>
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content w="25rem">
            <Popover.Arrow />
            <Popover.Body p={5}>
              <Popover.Title fontWeight="medium">Chat assistant</Popover.Title>
              <Text m={2}>
                The Chat assistant lets you converse with the assistant in
                natural language. The assistant has access to all of the
                information in the knowledge graph and will use the knowledge
                graph to provide information to you.
              </Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default ChatHelp;
