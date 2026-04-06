import { Check } from "lucide-react";

import { Trash } from "lucide-react";

import { ActionBar, Portal, Button } from "@chakra-ui/react";

const Actions = ({ selectedCount, onDelete }) => {
  return (
    <ActionBar.Root open={selectedCount > 0} colorPalette="blue">
      <Portal>
        <ActionBar.Positioner>
          <ActionBar.Content
            background="{colors.bg.muted}"
            color="fg"
            colorPalette="primary"
          >
            <ActionBar.SelectionTrigger>
              <Check /> {selectedCount} selected
            </ActionBar.SelectionTrigger>
            <ActionBar.Separator />
            <Button
              variant="outline"
              colorPalette="red"
              size="sm"
              onClick={onDelete}
            >
              <Trash /> Delete
            </Button>
          </ActionBar.Content>
        </ActionBar.Positioner>
      </Portal>
    </ActionBar.Root>
  );
};

export default Actions;
