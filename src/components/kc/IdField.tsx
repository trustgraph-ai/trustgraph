import React from "react";

import { Box } from "@chakra-ui/react";

import TextField from "../common/TextField";

interface IdProps {
  value;
  setValue;
}

const IdField: React.FC<IdProps> = ({ value, setValue }) => {
  return (
    <>
      <Box sx={{ m: 2 }}>
        <TextField
          label="Knowledge core ID"
          helperText="Use a unique ID for the core"
          value={value}
          onValueChange={(e) => setValue(e)}
        />
      </Box>
    </>
  );
};

export default IdField;
