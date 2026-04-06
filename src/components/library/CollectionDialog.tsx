import React, { useState, useEffect } from "react";
import { Dialog, Button } from "@chakra-ui/react";
import { Portal } from "@chakra-ui/react";

import TextField from "../common/TextField";
import TextAreaField from "../common/TextAreaField";
import ChipInputField from "../common/ChipInputField";
import ProgressSubmitButton from "../common/ProgressSubmitButton";

/**
 * CollectionDialog component - Dialog for creating or editing collections
 * @param {boolean} open - Whether the dialog is open
 * @param {Function} onOpenChange - Callback to control dialog open state
 * @param {Function} onSave - Callback when saving collection
 * @param {Object} editingCollection - Collection being edited (null for create mode)
 */
const CollectionDialog = ({
  open,
  onOpenChange,
  onSave,
  editingCollection,
}) => {
  const [collection, setCollection] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);

  // Reset form when dialog opens or editing collection changes
  useEffect(() => {
    if (editingCollection) {
      setCollection(editingCollection.collection);
      setName(editingCollection.name);
      setDescription(editingCollection.description);
      setTags(editingCollection.tags || []);
    } else {
      setCollection("");
      setName("");
      setDescription("");
      setTags([]);
    }
  }, [editingCollection, open]);

  /**
   * Handle form submission
   */
  const handleSubmit = () => {
    onSave(collection, name, description, tags);
  };

  // Validation: collection ID and name are required
  const isValid = collection.trim() !== "" && name.trim() !== "";

  return (
    <Dialog.Root open={open} onOpenChange={(e) => onOpenChange(e.open)}>
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>
                {editingCollection ? "Edit Collection" : "Create Collection"}
              </Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <TextField
                label="Collection ID"
                value={collection}
                onValueChange={setCollection}
                disabled={!!editingCollection}
                required
                helperText={
                  editingCollection
                    ? "ID cannot be changed"
                    : "Unique identifier for the collection"
                }
              />
              <TextField
                label="Name"
                value={name}
                onValueChange={setName}
                required
                helperText="Display name for the collection"
              />
              <TextAreaField
                label="Description"
                value={description}
                onValueChange={setDescription}
                helperText="Brief description of the collection"
              />
              <ChipInputField
                label="Tags"
                values={tags}
                onValuesChange={setTags}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <ProgressSubmitButton onClick={handleSubmit} disabled={!isValid}>
                {editingCollection ? "Update" : "Create"}
              </ProgressSubmitButton>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default CollectionDialog;
