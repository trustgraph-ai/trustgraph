import React from "react";

import { Button } from "@chakra-ui/react";

import { useWorkbenchStateStore } from "@trustgraph/react-state";
import { Value } from "@trustgraph/react-state";

const EntityNode: React.FC<{ value: Value }> = ({ value }) => {
  const setSelected = useWorkbenchStateStore((state) => state.setSelected);

  return (
    <Button
      size="xs"
      variant="subtle"
      colorPalette="blue"
      onClick={() =>
        setSelected({
          uri: value.v,
          label: value.label ? value.label : value.v,
        })
      }
    >
      {value.label}
    </Button>
  );
};

export default EntityNode;
