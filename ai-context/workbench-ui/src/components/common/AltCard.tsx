import React from "react";
import { Box, Flex, Heading, Text } from "@chakra-ui/react";

interface AltCardProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

const AltCard: React.FC<AltCardProps> = ({
  title,
  description,
  icon,
  children,
}) => {
  return (
    <Box borderRadius="lg" boxShadow="sm" p={5} border="1px" height="100%">
      <Flex alignItems="center" mb={description ? 2 : 4}>
        {icon && (
          <Box mr={3} color="accent.solid">
            {icon}
          </Box>
        )}
        <Heading as="h3" size="md" fontWeight="semibold">
          {title}
        </Heading>
      </Flex>
      {description && (
        <Text mb={4} fontSize="sm">
          {description}
        </Text>
      )}
      {children}
    </Box>
  );
};

export default AltCard;
