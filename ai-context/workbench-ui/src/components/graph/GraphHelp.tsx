import React from "react";

import { Popover, Text, IconButton, Portal } from "@chakra-ui/react";
import { CircleHelp } from "lucide-react";

const Help = () => {
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
              <Popover.Title fontWeight="medium">Visualize</Popover.Title>
              <Text m={2}>
                The Visualize page projects the knowledge graph into 3
                dimensions. The initial view is centered on a node that you
                select.
              </Text>
              <Text>
                You can use the mouse to zoom, pan and rotate the space to
                explore different parts of the graph. Clicking on a graph node
                adds more properties and relationships to the graph centered on
                that node.
              </Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default Help;
