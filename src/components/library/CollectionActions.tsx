import { Check, Pencil, Trash } from "lucide-react";

import { ActionBar, Portal, Button } from "@chakra-ui/react";

/**
 * CollectionActions component - Action bar for bulk operations on selected collections
 * Displays when one or more collections are selected
 * @param {number} selectedCount - Number of selected collections
 * @param {Function} onEdit - Callback for edit action
 * @param {Function} onDelete - Callback for delete action
 */
const CollectionActions = ({ selectedCount, onEdit, onDelete }) => {
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
            {selectedCount === 1 && (
              <Button variant="outline" size="sm" onClick={onEdit}>
                <Pencil /> Edit
              </Button>
            )}
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

export default CollectionActions;
