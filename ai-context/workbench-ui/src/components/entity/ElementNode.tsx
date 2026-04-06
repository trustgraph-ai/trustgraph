import React from "react";

import { Value } from "@trustgraph/react-state";
import { Entity } from "@trustgraph/react-state";
import LiteralNode from "./LiteralNode";
import EntityNode from "./EntityNode";
import SelectedNode from "./SelectedNode";

const ElementNode: React.FC<{ value: Value; selected: Entity }> = ({
  value,
  selected,
}) => {
  if (value.e)
    if (selected && value.v == selected.uri)
      return <SelectedNode value={value} />;
    else return <EntityNode value={value} />;
  else return <LiteralNode value={value} />;
};

export default ElementNode;
