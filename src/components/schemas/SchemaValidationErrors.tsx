import React from "react";
import { Box, Text } from "@chakra-ui/react";

interface SchemaValidationErrorsProps {
  errors: string[];
}

export const SchemaValidationErrors: React.FC<SchemaValidationErrorsProps> = ({
  errors,
}) => {
  if (errors.length === 0) return null;

  return (
    <Box
      p={4}
      borderWidth="1px"
      borderColor="red.500"
      borderRadius="md"
      bg="red.50"
    >
      <Text color="red.700" fontWeight="bold" mb={2}>
        Please fix the following errors:
      </Text>
      {errors.map((error, i) => (
        <Text key={i} color="red.600" fontSize="sm">
          • {error}
        </Text>
      ))}
    </Box>
  );
};
