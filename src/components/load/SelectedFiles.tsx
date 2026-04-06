import React from "react";

import { Trash } from "lucide-react";

import { Box, Table, IconButton } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";

const SelectedFiles = () => {
  const files = useLoadStateStore((state) => state.files);
  const removeFile = useLoadStateStore((state) => state.removeFile);

  return (
    <>
      <Box>
        <Table.Root width="30rem">
          <Table.Body>
            {Array.from(files).map((file, ix) => (
              <Table.Row key={ix}>
                <Table.Cell>{file.name}</Table.Cell>
                <Table.Cell>
                  <IconButton
                    size="xs"
                    onClick={() => removeFile(file)}
                    colorPalette="red"
                  >
                    <Trash />
                  </IconButton>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Box>
    </>
  );
};

export default SelectedFiles;
