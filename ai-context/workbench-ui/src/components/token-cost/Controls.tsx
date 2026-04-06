import React, { useState } from "react";

import { Plus } from "lucide-react";

import { Button, Box } from "@chakra-ui/react";

import EditDialog from "./EditDialog";

const Controls = ({ onUpdate }) => {
  const [createOpen, setCreateOpen] = useState(false);

  const onComplete = () => {
    onUpdate();
    setCreateOpen(false);
  };

  return (
    <Box>
      <Button
        mt={5}
        ml={5}
        mb={5}
        variant="solid"
        colorPalette="primary"
        onClick={() => setCreateOpen(true)}
      >
        <Plus /> Create Model Cost
      </Button>
      <EditDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        create={true}
        onComplete={() => onComplete()}
      />
    </Box>
  );
};

export default Controls;
