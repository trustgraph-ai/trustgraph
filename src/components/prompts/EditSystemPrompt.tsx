import React, { useEffect, useState } from "react";

import { SendHorizontal } from "lucide-react";

import { Portal, Button, Dialog, CloseButton } from "@chakra-ui/react";

import { usePrompts } from "@trustgraph/react-state";
import TextAreaField from "../common/TextAreaField";

const EditDialog = ({ open, onOpenChange, onComplete }) => {
  const { systemPrompt, updateSystemPrompt } = usePrompts();
  const [prompt, setPrompt] = useState("");

  useEffect(() => {
    if (systemPrompt) {
      setPrompt(systemPrompt);
    }
  }, [systemPrompt]);

  const onEdit = () => {
    updateSystemPrompt({ prompt, onSuccess: onComplete });
  };

  return (
    <Dialog.Root
      placement="center"
      size="xl"
      open={open}
      onOpenChange={(x) => {
        onOpenChange(x.open);
      }}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>Edit system prompt</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <TextAreaField
                label="System prompt"
                placeholder="Enter AI prompt"
                value={prompt}
                onValueChange={(v) => setPrompt(v)}
                required={true}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={() => onEdit()} colorPalette="primary">
                <SendHorizontal /> Submit
              </Button>
            </Dialog.Footer>
            <Dialog.CloseTrigger asChild>
              <CloseButton size="sm" />
            </Dialog.CloseTrigger>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default EditDialog;
