import React from "react";

import { Box } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";
import TextField from "../common/TextField";

const Url = () => {
  const value = useLoadStateStore((state) => state.url);
  const setValue = useLoadStateStore((state) => state.setUrl);

  return (
    <>
      <Box sx={{ m: 2 }}>
        <TextField
          sx={{
            width: "50rem",
          }}
          label="URL (optional)"
          helperText="Source URL (not available for loading multiple files at once)"
          value={value}
          onValueChange={(e) => setValue(e)}
        />
      </Box>
    </>
  );
};

export default Url;
