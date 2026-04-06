import React from "react";

import { Box, Spinner } from "@chakra-ui/react";

import { useProgressStateStore } from "@trustgraph/react-state";

const CenterSpinner: React.FC = () => {
  const activity = useProgressStateStore((state) => state.activity);

  if (activity.size < 1) {
    return null;
  }

  return (
    <Box
      position="absolute"
      top="calc(50% - 3rem)"
      left="calc(50% - 3rem)"
      zIndex="999"
      margin="0"
      padding="0"
    >
      <Spinner size="xl" />
    </Box>
  );
};

export default CenterSpinner;
