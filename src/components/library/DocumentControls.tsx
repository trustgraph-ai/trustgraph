import { Plus } from "lucide-react";

import { Button, Box } from "@chakra-ui/react";

const Controls = ({ onUpload }) => {
  return (
    <Box>
      <Button
        mt={5}
        ml={5}
        mb={5}
        variant="solid"
        colorPalette="primary"
        onClick={() => onUpload()}
      >
        <Plus /> Upload Documents
      </Button>
    </Box>
  );
};

export default Controls;
