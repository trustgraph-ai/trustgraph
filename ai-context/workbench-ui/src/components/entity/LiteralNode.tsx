import React from "react";

import { Text } from "@chakra-ui/react";

import { Value } from "@trustgraph/react-state";

const LiteralNode: React.FC<{ value: Value }> = ({ value }) => {
  return <Text>{value.label}</Text>;
};

export default LiteralNode;
