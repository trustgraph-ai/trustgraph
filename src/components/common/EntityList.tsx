import { useNavigate } from "react-router";

import { HStack, Tag } from "@chakra-ui/react";

import { Entity } from "@trustgraph/react-state";
import { useWorkbenchStateStore } from "@trustgraph/react-state";

const EntityList = () => {
  const entities = useWorkbenchStateStore((state) => state.entities);
  const setSelected = useWorkbenchStateStore((state) => state.setSelected);

  const navigate = useNavigate();

  const onSelect = (x: Entity) => {
    setSelected(x);
    navigate("/entity");
  };

  return (
    <HStack mt={8}>
      {entities.slice(0, 8).map((entity, ix) => (
        <Tag.Root
          asChild
          size="sm"
          key={ix}
          color="primary.solid"
          bgColor="bg"
          variant="surface"
        >
          <button onClick={() => onSelect(entity)}>
            <Tag.Label>{entity.label}</Tag.Label>
          </button>
        </Tag.Root>
      ))}
    </HStack>
  );
};

export default EntityList;
