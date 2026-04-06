import React, { useEffect, useState } from "react";

import { Trash, SendHorizontal } from "lucide-react";

import { Portal, Button, Dialog, CloseButton } from "@chakra-ui/react";

import { useTokenCosts } from "@trustgraph/react-state";
import TextField from "../common/TextField";

const EditDialog = ({ open, onOpenChange, model, create }) => {
  const state = useTokenCosts();

  const [newModel, setNewModel] = useState("");
  const [input, setInput] = useState(0);
  const [output, setOutput] = useState(0);

  useEffect(() => {
    if (!model) return;

    const models = state.tokenCosts.filter((row) => row.model == model);

    if (models.length < 1) return;

    setNewModel(model);
    setInput(models[0].input_price * 1000000);
    setOutput(models[0].output_price * 1000000);
  }, [state.tokenCosts, model, create]);

  const onEdit = () => {
    // Create is different from edit existing
    if (create) {
      // When creating, the order is...
      // 1) write the prompt template,
      // 2) get the template index
      // 3) add this prompt ID to the index if not already there

      state.updateTokenCost({
        model: newModel,
        input_price: input,
        output_price: output,
        onSuccess: () => onOpenChange(false),
      });
    } else {
      state.updateTokenCost({
        model: model,
        input_price: input,
        output_price: output,
        onSuccess: () => onOpenChange(false),
      });
    }
  };

  const onDelete = () => {
    // Shouldn't happen, but can't delete a prompt that hasn't been created
    // yet
    if (create) return;

    state.deleteTokenCosts({
      model: model,
      onSuccess: () => onOpenChange(false),
    });
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
              {create && <Dialog.Title>Create model cost</Dialog.Title>}

              {!create && (
                <Dialog.Title>
                  Edit model cost: <code>{model}</code>
                </Dialog.Title>
              )}
            </Dialog.Header>
            <Dialog.Body>
              {create && (
                <TextField
                  label="Model ID"
                  placeholder="Enter a unique model ID"
                  value={newModel}
                  onValueChange={(v) => setNewModel(v)}
                  required={true}
                />
              )}

              <TextField
                label="Input token cost ( $ / 1Mt )"
                placeholder="Input token cost"
                value={input}
                onValueChange={(v) => setInput(v)}
                required={true}
              />

              <TextField
                label="Output token cost ( $ / 1Mt )"
                placeholder="Output token cost ($/token)"
                value={output}
                onValueChange={(v) => setOutput(v)}
                required={true}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              {
                // If a 'create' operation, there's nothing to delete, only
                // present if an existing prompt exists
              }
              {!create && (
                <Button
                  variant="solid"
                  onClick={() => onDelete()}
                  colorPalette="red"
                >
                  <Trash /> Delete
                </Button>
              )}
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
