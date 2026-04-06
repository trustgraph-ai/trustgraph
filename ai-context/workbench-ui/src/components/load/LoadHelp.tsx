import React from "react";

import { Popover, Text, IconButton, Portal, List } from "@chakra-ui/react";
import { CircleHelp } from "lucide-react";

const LoadHelp = () => {
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
              <Popover.Title fontWeight="medium">Load</Popover.Title>
              <Text m={2}>
                The Load page lets you ingest new data into TrustGraph
                processing. There are 3 operations:
              </Text>
              <List.Root m={2} ps={8}>
                <List.Item>Upload PDF - for PDF documents</List.Item>
                <List.Item>
                  Upload text - for text and markdown documents
                </List.Item>
                <List.Item>
                  Paste text - for copy/pasting or typing a snippet of text.
                </List.Item>
              </List.Root>
              <Text m={2}>
                Note that Upload simply initiates the processing; it may take
                many minutes / hours or even days to complete processing large
                documents. You would see some elements of documents begin
                appearing in the workbench within a couple of minutes of
                document upload.
              </Text>
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
};

export default LoadHelp;
