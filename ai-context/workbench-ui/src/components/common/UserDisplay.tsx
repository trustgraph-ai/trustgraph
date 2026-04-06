import React from "react";
import { HStack, Text } from "@chakra-ui/react";
import { User } from "lucide-react";
import { useSettings } from "@trustgraph/react-state";

const UserDisplay: React.FC = () => {
  const { settings } = useSettings();

  return (
    <HStack gap={2} align="center">
      <User size={14} color="currentColor" />
      <Text fontSize="xs" fontWeight="medium" color="fg.muted">
        {settings.user}
      </Text>
    </HStack>
  );
};

export default UserDisplay;
