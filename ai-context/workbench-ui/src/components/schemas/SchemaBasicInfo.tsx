import React from "react";
import { Field, Input } from "@chakra-ui/react";
import TextField from "../common/TextField";
import TextAreaField from "../common/TextAreaField";

interface SchemaBasicInfoProps {
  mode: "create" | "edit";
  id: string;
  name: string;
  description: string;
  onIdChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
}

export const SchemaBasicInfo: React.FC<SchemaBasicInfoProps> = ({
  mode,
  id,
  name,
  description,
  onIdChange,
  onNameChange,
  onDescriptionChange,
}) => {
  return (
    <>
      {mode === "create" && (
        <Field.Root required>
          <Field.Label>
            Schema ID <Field.RequiredIndicator />
          </Field.Label>
          <Input
            value={id}
            onChange={(e) => onIdChange(e.target.value)}
            placeholder="e.g., customer_records"
          />
        </Field.Root>
      )}

      <TextField
        label="Name"
        value={name}
        onValueChange={onNameChange}
        placeholder="e.g., Customer Records"
        required
      />

      <TextAreaField
        label="Description"
        value={description}
        onValueChange={onDescriptionChange}
        placeholder="Describe the purpose of this schema"
        required
      />
    </>
  );
};
