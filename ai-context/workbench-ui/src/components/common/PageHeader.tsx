import React from "react";

import { Flex, Text, Box, HStack, VStack, Heading } from "@chakra-ui/react";

import ColorModeToggle from "../color-mode-toggle";
import FlowSelector from "./FlowSelector";
import ConnectionStatus from "./ConnectionStatus";
import UserDisplay from "./UserDisplay";

interface PageHeaderProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  icon,
}) => {
  return (
    <Flex
      mb={8}
      alignItems="center"
      justifyContent="space-between"
      width="100%"
      px={1}
      py={1}
    >
      <Flex alignItems="center">
        {icon && (
          <Box mr={4} color="{colors.primary.fg}" fontSize="xl">
            {icon}
          </Box>
        )}
        <Box>
          <Heading
            as="h1"
            size="xl"
            color="{colors.primary.fg}"
            fontWeight="bold"
          >
            {title}
          </Heading>
          <Text mt={1} fontSize="md" color="{colors.primary.emphasized}">
            {description}
          </Text>
        </Box>
      </Flex>
      <Box>
        <HStack gap={6} align="center">
          <VStack gap={1} align="end">
            <ConnectionStatus showDetails={true} size="sm" />
            <UserDisplay />
          </VStack>
          <FlowSelector />
          <ColorModeToggle />
        </HStack>
      </Box>
    </Flex>
  );
};

export default PageHeader;
