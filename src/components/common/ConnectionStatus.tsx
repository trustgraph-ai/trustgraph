import React from "react";
import { Box, HStack, Text, Tooltip } from "@chakra-ui/react";
import { Info, Clock, Wifi, WifiOff, Shield, ShieldOff } from "lucide-react";
import { useConnectionState } from "@trustgraph/react-provider";
import type { ConnectionState } from "@trustgraph/client";

interface ConnectionStatusProps {
  showDetails?: boolean;
  size?: "sm" | "md" | "lg";
}

const getStatusDisplay = (state: ConnectionState) => {
  switch (state.status) {
    case "connecting":
      return {
        icon: Clock,
        color: "yellow.500",
        text: "Connecting...",
        tooltip: "Establishing connection to server",
      };

    case "connected":
      return {
        icon: Wifi,
        color: "green.500",
        text: "Connected",
        tooltip: "Connected to server",
      };

    case "authenticated":
      return {
        icon: Shield,
        color: "green.500",
        text: "Authenticated",
        tooltip: "Connected with API key authentication",
      };

    case "unauthenticated":
      return {
        icon: ShieldOff,
        color: "blue.500",
        text: "Unauthenticated",
        tooltip: "Connected but no API key provided (limited functionality)",
      };

    case "reconnecting":
      return {
        icon: Clock,
        color: "orange.500",
        text: `Reconnecting... (${state.reconnectAttempt}/${state.maxAttempts})`,
        tooltip: `Attempting to reconnect. Try ${state.reconnectAttempt} of ${state.maxAttempts}`,
      };

    case "failed":
      return {
        icon: WifiOff,
        color: "red.500",
        text: "Connection Failed",
        tooltip:
          state.lastError || "Connection failed after maximum retry attempts",
      };

    default:
      return {
        icon: Info,
        color: "gray.500",
        text: "Unknown",
        tooltip: "Unknown connection state",
      };
  }
};

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  showDetails = false,
  size = "md",
}) => {
  const connectionState = useConnectionState();

  if (!connectionState) {
    return null;
  }

  const {
    icon: StatusIcon,
    color,
    text,
    tooltip,
  } = getStatusDisplay(connectionState);

  const iconSize = size === "sm" ? 16 : size === "lg" ? 24 : 20;
  const fontSize = size === "sm" ? "xs" : size === "lg" ? "md" : "sm";

  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <HStack spacing={2}>
          <Box color={color}>
            <StatusIcon size={iconSize} />
          </Box>
          <Text fontSize={fontSize} color="fg.default">
            {showDetails ? text : connectionState.status}
          </Text>
          {showDetails && connectionState.hasApiKey && (
            <Text fontSize="xs" color="fg.muted">
              (API Key)
            </Text>
          )}
        </HStack>
      </Tooltip.Trigger>
      <Tooltip.Positioner>
        <Tooltip.Content>{tooltip}</Tooltip.Content>
      </Tooltip.Positioner>
    </Tooltip.Root>
  );
};

export default ConnectionStatus;
