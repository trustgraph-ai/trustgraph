import React from "react";

import { Box } from "@chakra-ui/react";

import { useLoadStateStore } from "@trustgraph/react-state";

import TextAreaField from "../common/TextAreaField";

const Comments = () => {
  const value = useLoadStateStore((state) => state.comments);
  const setValue = useLoadStateStore((state) => state.setComments);

  return (
    <>
      <Box sx={{ m: 2 }}>
        <TextAreaField
          label="Comments (optional)"
          helperText="Notes / description..."
          value={value}
          onValueChange={(e) => setValue(e)}
        />
      </Box>
    </>
  );
};

export default Comments;
