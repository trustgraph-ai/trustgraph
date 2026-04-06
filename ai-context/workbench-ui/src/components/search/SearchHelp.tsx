import React from "react";

// Chakra UI components for popover help interface
import { Popover, Text, IconButton, Portal } from "@chakra-ui/react";

// Help icon from Lucide React icon library
import { CircleHelp } from "lucide-react";

/**
 * SearchHelp component provides contextual help information for the search feature
 * Displays a help popover when the help icon button is clicked
 * Explains how semantic search works with the knowledge graph
 */
const SearchHelp = () => {
  return (
    <Popover.Root size="md" variant="outline">
      {/* Help icon button that triggers the popover */}
      <Popover.Trigger asChild>
        <IconButton size="lg" ml={10}>
          <CircleHelp />
        </IconButton>
      </Popover.Trigger>

      {/* Portal ensures popover renders at document root level */}
      <Portal>
        <Popover.Positioner>
          <Popover.Content w="25rem">
            <Popover.Arrow />
            <Popover.Body p={5}>
              <Popover.Title fontWeight="medium">Search</Popover.Title>
              <Text m={2}>
                {/* Explanation of semantic search functionality */}
                The Search assistant lets you enter terms for semantic matching
                against known entities in the knowledge graph. Just enter a
                natural language term, and the search assistant will find
                things that closely match what you enter.
              </Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default SearchHelp;
