import React, { useState } from "react";
import { Table, Input, Button, HStack, IconButton } from "@chakra-ui/react";
import { Trash2, Plus, Check } from "lucide-react";
import { EnumOption } from "@trustgraph/react-state";

interface ModelsTableProps {
  models: EnumOption[];
  defaultValue: string;
  onUpdate: (models: EnumOption[], defaultValue: string) => void;
  isUpdating: boolean;
}

const ModelsTable: React.FC<ModelsTableProps> = ({
  models,
  defaultValue,
  onUpdate,
  isUpdating,
}) => {
  const [editingModels, setEditingModels] = useState<EnumOption[]>(models);
  const [editingDefault, setEditingDefault] = useState<string>(defaultValue);
  const [hasChanges, setHasChanges] = useState(false);

  React.useEffect(() => {
    setEditingModels(models);
    setEditingDefault(defaultValue);
    setHasChanges(false);
  }, [models, defaultValue]);

  const handleModelChange = (
    index: number,
    field: keyof EnumOption,
    value: string,
  ) => {
    const updated = [...editingModels];
    const oldId = updated[index].id;
    updated[index] = { ...updated[index], [field]: value };
    setEditingModels(updated);
    setHasChanges(true);

    // If this is the ID field, update the default accordingly
    if (field === "id") {
      if (!editingDefault && value) {
        // No default set and we're adding an ID - make it the default
        setEditingDefault(value);
      } else if (editingDefault === oldId) {
        // We're changing the ID of the current default - update the default to the new ID
        setEditingDefault(value);
      }
    }
  };

  const handleAddModel = () => {
    const newModel = { id: "", description: "" };
    const updated = [...editingModels, newModel];
    setEditingModels(updated);
    setHasChanges(true);

    // If this is the first model (table was empty), make it the default
    if (editingModels.length === 0) {
      setEditingDefault("");
    }
  };

  const handleDeleteModel = (index: number) => {
    const updated = editingModels.filter((_, i) => i !== index);
    setEditingModels(updated);
    setHasChanges(true);

    // If we deleted the default, set the first remaining model as default
    if (editingModels[index].id === editingDefault) {
      if (updated.length > 0) {
        setEditingDefault(updated[0].id);
      } else {
        setEditingDefault("");
      }
    }
  };

  const handleDefaultChange = (value: string) => {
    setEditingDefault(value);
    setHasChanges(true);
  };

  const handleSave = () => {
    onUpdate(editingModels, editingDefault);
  };

  return (
    <>
      <Table.Root size="sm" variant="outline">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader width="40px">Default</Table.ColumnHeader>
            <Table.ColumnHeader>ID</Table.ColumnHeader>
            <Table.ColumnHeader>Description</Table.ColumnHeader>
            <Table.ColumnHeader width="60px">Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {editingModels.map((model, index) => (
            <Table.Row key={index}>
              <Table.Cell textAlign="center">
                <input
                  type="radio"
                  name="default-model"
                  checked={editingDefault === model.id}
                  onChange={() => handleDefaultChange(model.id)}
                  style={{ cursor: "pointer" }}
                />
              </Table.Cell>
              <Table.Cell>
                <Input
                  value={model.id}
                  onChange={(e) =>
                    handleModelChange(index, "id", e.target.value)
                  }
                  placeholder="Model ID"
                  size="sm"
                />
              </Table.Cell>
              <Table.Cell>
                <Input
                  value={model.description}
                  onChange={(e) =>
                    handleModelChange(index, "description", e.target.value)
                  }
                  placeholder="Description"
                  size="sm"
                />
              </Table.Cell>
              <Table.Cell>
                <IconButton
                  aria-label="Delete model"
                  size="sm"
                  variant="ghost"
                  onClick={() => handleDeleteModel(index)}
                >
                  <Trash2 />
                </IconButton>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>

      <HStack justify="space-between" mt={4}>
        <Button
          onClick={handleAddModel}
          size="sm"
          variant="outline"
          colorPalette="accent"
        >
          <Plus />
          Add Model
        </Button>

        <Button
          onClick={handleSave}
          size="sm"
          colorPalette="accent"
          disabled={!hasChanges || isUpdating}
          loading={isUpdating}
        >
          <Check />
          Save Changes
        </Button>
      </HStack>
    </>
  );
};

export default ModelsTable;
