import { Plus } from "lucide-react";

import { Button, Box } from "@chakra-ui/react";

/**
 * CollectionControls component - Control buttons for collection operations
 * @param {Function} onCreate - Callback for creating a new collection
 */
const CollectionControls = ({ onCreate }) => {
  return (
    <Box>
      <Button
        mt={5}
        ml={5}
        mb={5}
        variant="solid"
        colorPalette="primary"
        onClick={() => onCreate()}
      >
        <Plus /> Create Collection
      </Button>
    </Box>
  );
};

export default CollectionControls;
