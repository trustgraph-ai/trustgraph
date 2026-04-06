import React from "react";

import { Box } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";

import TextField from "../common/TextField";

const Title = () => {
  const value = useLoadStateStore((state) => state.title);
  const setValue = useLoadStateStore((state) => state.setTitle);

  return (
    <>
      <Box sx={{ m: 2 }}>
        <TextField
          label="Title (optional)"
          helperText="File title (not available for loading multiple files at once)"
          value={value}
          onValueChange={(e) => setValue(e)}
        />
      </Box>
    </>
  );
};

export default Title;
