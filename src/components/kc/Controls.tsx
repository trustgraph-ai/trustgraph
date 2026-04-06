import React, { useState } from "react";

import { Upload } from "lucide-react";

import { Button, Box } from "@chakra-ui/react";

import UploadDialog from "./UploadDialog";

const Controls = () => {
  const [uploadOpen, setUploadOpen] = useState(false);

  return (
    <Box>
      <Button
        mt={5}
        ml={5}
        mb={5}
        variant="solid"
        colorPalette="primary"
        onClick={() => setUploadOpen(true)}
      >
        <Upload /> Upload
      </Button>
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </Box>
  );
};

export default Controls;
