import React from "react";
import { Plus } from "lucide-react";
import { Button, Box } from "@chakra-ui/react";
import { generateFlowClassId } from "@trustgraph/react-state";

interface FlowClassControlsProps {
  onNew?: (id: string) => void;
}

const FlowClassControls: React.FC<FlowClassControlsProps> = ({ onNew }) => {
  const handleCreate = () => {
    const newId = generateFlowClassId("flow-class");
    onNew?.(newId);
  };

  return (
    <Box>
      <Button
        mt={5}
        ml={5}
        mb={5}
        variant="solid"
        colorPalette="primary"
        onClick={handleCreate}
      >
        <Plus /> Create Flow Class
      </Button>
    </Box>
  );
};

export default FlowClassControls;
