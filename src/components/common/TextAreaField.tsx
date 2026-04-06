import React from "react";

import { Field, Textarea } from "@chakra-ui/react";

interface TextFieldProps {
  label: string;
  placeholder?: string;
  value: string;
  onValueChange: (x: string) => void;
  required?: boolean;
  disabled?: boolean;
}

const TextAreaField: React.FC<TextFieldProps> = ({
  label,
  placeholder,
  value,
  onValueChange,
  required,
  disabled,
}) => {
  return (
    <Field.Root mb={4} required={required}>
      <Field.Label>
        {label} {required && <Field.RequiredIndicator />}
      </Field.Label>
      <Textarea
        placeholder={placeholder}
        variant="subtle"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        maxH="30lh"
        h="10lh"
        disabled={disabled}
      />
    </Field.Root>
  );
};

export default TextAreaField;
