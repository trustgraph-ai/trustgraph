import React from "react";
import { Check, Trash, Eye } from "lucide-react";
import { ActionBar, Portal, Button } from "@chakra-ui/react";

interface FlowClassActionsProps {
  selectedCount: number;
  onEdit?: () => void;
  onDelete?: () => void;
}

const FlowClassActions: React.FC<FlowClassActionsProps> = ({
  selectedCount,
  onEdit,
  onDelete,
}) => {
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

            {selectedCount === 1 && onEdit && (
              <Button
                variant="outline"
                colorPalette="blue"
                size="sm"
                onClick={onEdit}
              >
                <Eye /> View
              </Button>
            )}

            {/* Temporarily disabled this because it doesn't work
            {selectedCount === 1 && onDuplicate && (
              <Button
                variant="outline"
                colorPalette="green"
                size="sm"
                onClick={onDuplicate}
              >
                <Copy /> Duplicate
              </Button>
            )}
            */}

            {onDelete && (
              <Button
                variant="outline"
                colorPalette="red"
                size="sm"
                onClick={onDelete}
              >
                <Trash /> Delete
              </Button>
            )}
          </ActionBar.Content>
        </ActionBar.Positioner>
      </Portal>
    </ActionBar.Root>
  );
};

export default FlowClassActions;
