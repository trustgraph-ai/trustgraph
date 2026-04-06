import React from "react";

import { Box, Alert } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";

const ProcessedFiles = () => {
  const uploaded = useLoadStateStore((state) => state.uploaded);

  return (
    <>
      <Box>
        {uploaded.map((file, ix) => (
          <Alert.Root key={ix} status="info" mt={5}>
            <Alert.Indicator />
            <Alert.Title>{file} uploaded</Alert.Title>
          </Alert.Root>
        ))}
      </Box>
    </>
  );
};

export default ProcessedFiles;
