import React from "react";

import { Popover, Text, IconButton, Portal } from "@chakra-ui/react";
import { CircleHelp } from "lucide-react";

const EntityHelp = () => {
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
              <Popover.Title fontWeight="medium">Explore</Popover.Title>
              <Text m={2}>
                The Explore page shows properties and relationships of entities
                in the knowledge graph. On this page, you can navigate by
                selecting other knowledge graph entities and seeing the
                properties and relationships related to those entities.
              </Text>
              <Text>
                Selecting the Graph View button shows you the same information,
                but presented in a 3D graphical form.
              </Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default EntityHelp;
