import React from "react";
import { Box, Spinner, Text } from "@chakra-ui/react";

/**
 * Loading screen displayed while establishing WebSocket connection
 */
export const ConnectionLoadingScreen: React.FC = () => {
  return (
    <Box
      width="100%"
      height="100vh"
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      gap={4}
    >
      <Spinner size="xl" />
      <Text color="fg.muted">Connecting to server...</Text>
    </Box>
  );
};
