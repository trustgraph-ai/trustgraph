import React from "react";
import { Box, VStack } from "@chakra-ui/react";
import { SchemaControls } from "./SchemaControls";
import { SchemasTable } from "./SchemasTable";

export const Schemas: React.FC = () => {
  return (
    <Box>
      <VStack gap={6} align="stretch">
        <SchemaControls />
        <SchemasTable />
      </VStack>
    </Box>
  );
};
