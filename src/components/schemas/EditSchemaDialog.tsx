import React, { useRef } from "react";
import {
  Dialog,
  Portal,
  CloseButton,
  Button,
  VStack,
  HStack,
  Separator,
} from "@chakra-ui/react";
import { useSchemas } from "@trustgraph/react-state";
import { Schema } from "../../model/schemas-table";
import { validateSchema } from "../../utils/schema-validation";
import { useSchemaForm } from "./useSchemaForm";
import { SchemaValidationErrors } from "./SchemaValidationErrors";
import { SchemaBasicInfo } from "./SchemaBasicInfo";
import { SchemaFieldsList } from "./SchemaFieldsList";
import { SchemaIndexesSection } from "./SchemaIndexesSection";
import { ConfirmDialog } from "../common/ConfirmDialog";

interface EditSchemaDialogProps {
  isOpen: boolean;
  onClose: () => void;
  mode: "create" | "edit";
  schemaId?: string;
  initialSchema?: Schema;
}

export const EditSchemaDialog: React.FC<EditSchemaDialogProps> = ({
  isOpen,
  onClose,
  mode,
  schemaId,
  initialSchema,
}) => {
  const { createSchema, updateSchema, deleteSchema, schemas } = useSchemas();
  const contentRef = useRef<HTMLDivElement>(null);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const {
    id,
    setId,
    name,
    setName,
    description,
    setDescription,
    fields,
    indexes,
    newIndex,
    setNewIndex,
    errors,
    setErrors,
    handleAddField,
    handleRemoveField,
    handleFieldChange,
    handleAddEnumValue,
    handleRemoveEnumValue,
    handleAddIndex,
    handleRemoveIndex,
    resetForm,
    getSchema,
  } = useSchemaForm({
    isOpen,
    mode,
    schemaId,
    initialSchema,
  });

  const handleSave = async () => {
    const schema = getSchema();

    // Validate schema
    const validationErrors = validateSchema(
      schema,
      schemas,
      mode === "create" ? id : undefined,
    );
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    try {
      if (mode === "create") {
        createSchema({
          id,
          schema,
          onSuccess: () => {
            onClose();
            resetForm();
          },
        });
      } else {
        updateSchema({
          id: schemaId!,
          schema,
          onSuccess: () => {
            onClose();
            setErrors([]);
          },
        });
      }
    } catch (error) {
      console.error("Error saving schema:", error);
    }
  };

  const handleDelete = () => {
    setConfirmDelete(true);
  };

  const handleConfirmDelete = () => {
    deleteSchema({
      id: schemaId!,
      onSuccess: () => {
        onClose();
      },
    });
    setConfirmDelete(false);
  };

  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(details) => {
        if (!details.open) onClose();
      }}
      size="xl"
      placement="center"
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content ref={contentRef}>
            <Dialog.Header>
              <Dialog.Title>
                {mode === "create" ? "Create New Schema" : "Edit Schema"}
              </Dialog.Title>
            </Dialog.Header>

            <Dialog.Body overflowY="auto">
              <VStack gap={6} align="stretch">
                <SchemaValidationErrors errors={errors} />

                <SchemaBasicInfo
                  mode={mode}
                  id={id}
                  name={name}
                  description={description}
                  onIdChange={setId}
                  onNameChange={setName}
                  onDescriptionChange={setDescription}
                />

                <Separator />

                <SchemaFieldsList
                  fields={fields}
                  onFieldChange={handleFieldChange}
                  onAddField={handleAddField}
                  onRemoveField={handleRemoveField}
                  onAddEnumValue={handleAddEnumValue}
                  onRemoveEnumValue={handleRemoveEnumValue}
                  contentRef={contentRef}
                />

                <Separator />

                <SchemaIndexesSection
                  indexes={indexes}
                  fields={fields}
                  newIndex={newIndex}
                  onNewIndexChange={setNewIndex}
                  onAddIndex={handleAddIndex}
                  onRemoveIndex={handleRemoveIndex}
                  contentRef={contentRef}
                />
              </VStack>
            </Dialog.Body>

            <Dialog.Footer>
              <HStack gap={3}>
                {mode === "edit" && (
                  <Button
                    colorPalette="red"
                    variant="ghost"
                    onClick={handleDelete}
                  >
                    Delete Schema
                  </Button>
                )}
                <Button variant="ghost" onClick={onClose}>
                  Cancel
                </Button>
                <Button colorPalette="primary" onClick={handleSave}>
                  {mode === "create" ? "Create" : "Save"}
                </Button>
              </HStack>
            </Dialog.Footer>

            <Dialog.CloseTrigger asChild>
              <CloseButton size="sm" />
            </Dialog.CloseTrigger>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>

      <ConfirmDialog
        isOpen={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Schema"
        message={`Are you sure you want to delete the schema "${name}"?\n\nThis action cannot be undone and will permanently remove the schema and all its configuration.`}
        variant="danger"
        confirmText="Delete"
      />
    </Dialog.Root>
  );
};
