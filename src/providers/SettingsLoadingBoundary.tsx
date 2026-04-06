import React from "react";
import { Box, Spinner, Text } from "@chakra-ui/react";
import { useSettings } from "@trustgraph/react-state";

interface SettingsLoadingBoundaryProps {
  children: React.ReactNode;
}

/**
 * Loading boundary that waits for settings to load before rendering children
 *
 * Shows a loading spinner and message while settings are being loaded.
 * Once settings are ready, renders children.
 */
export const SettingsLoadingBoundary: React.FC<
  SettingsLoadingBoundaryProps
> = ({ children }) => {
  const { isLoaded } = useSettings();

  // Show loading state while settings load
  if (!isLoaded) {
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
        <Text color="fg.muted">Loading settings...</Text>
      </Box>
    );
  }

  return <>{children}</>;
};
