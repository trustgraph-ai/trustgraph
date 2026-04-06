import React from "react";

import { Tag } from "@chakra-ui/react";

import { Value } from "@trustgraph/react-state";

const SelectedNode: React.FC<{ value: Value }> = ({ value }) => {
  return (
    <Tag.Root variant="surface" color="gray.50" backgroundColor="gray.600">
      <Tag.Label>{value.label}</Tag.Label>
    </Tag.Root>
  );
};

export default SelectedNode;
