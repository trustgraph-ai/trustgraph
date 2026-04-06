import React from "react";

import { Field, Input } from "@chakra-ui/react";

interface TextFieldProps {
  label: string;
  placeholder?: string;
  value: string;
  onValueChange: (x: string) => void;
  required?: boolean;
  helperText?: string;
  disabled?: boolean;
  type?: string;
}

const TextField: React.FC<TextFieldProps> = ({
  label,
  placeholder,
  value,
  onValueChange,
  required,
  helperText,
  disabled,
  type = "text",
}) => {
  return (
    <Field.Root mb={4} required={required}>
      <Field.Label>
        {label} {required && <Field.RequiredIndicator />}
      </Field.Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        placeholder={placeholder}
        variant="subtle"
        disabled={disabled}
      />
      {helperText && <Field.HelperText>{helperText}</Field.HelperText>}
    </Field.Root>
  );
};

export default TextField;
