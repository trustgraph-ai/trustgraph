import React from "react";

import { Box } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";
import TextAreaField from "../common/TextAreaField";

const TextBuffer = () => {
  const value = useLoadStateStore((state) => state.text);
  const setValue = useLoadStateStore((state) => state.setText);

  return (
    <>
      <Box mt={5}>
        <TextAreaField
          value={value}
          onValueChange={(e) => setValue(e)}
          label="Text content"
          rows={15}
        />
      </Box>
    </>
  );
};

export default TextBuffer;
