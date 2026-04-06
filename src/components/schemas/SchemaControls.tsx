import React from "react";
import { HStack, Button } from "@chakra-ui/react";
import { Plus } from "lucide-react";
import { EditSchemaDialog } from "./EditSchemaDialog";

export const SchemaControls: React.FC = () => {
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);

  return (
    <>
      <HStack justify="flex-end">
        <Button colorPalette="primary" onClick={() => setIsCreateOpen(true)}>
          <Plus size={20} />
          Create Schema
        </Button>
      </HStack>

      <EditSchemaDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        mode="create"
      />
    </>
  );
};
