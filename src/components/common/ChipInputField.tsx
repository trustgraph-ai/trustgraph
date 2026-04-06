import React, { useState } from "react";

import { Input, Tag, Wrap, Field } from "@chakra-ui/react";

// Represents a label added to the list. Highlighted with a close button for
// removal.
const Chip = ({ label, onCloseClick }) => (
  <Tag.Root
    key={label}
    borderRadius="full"
    variant="solid"
    colorScheme="green"
  >
    <Tag.Label>{label}</Tag.Label>
    <Tag.EndElement>
      <Tag.CloseTrigger
        onClick={() => {
          onCloseClick(label);
        }}
      />
    </Tag.EndElement>
  </Tag.Root>
);

// A horizontal stack of chips. Like a Pringles can on its side.
const ChipList = ({ items = [], onCloseClick }) => (
  <Wrap spacing={1} mb={3}>
    {items.map((item) => (
      <Chip label={item} key={item} onCloseClick={onCloseClick} />
    ))}
  </Wrap>
);

// Form field wrapper.
const ChipInput = ({ ...rest }) => <Input {...rest} />;

// Field wrapping chip list and input
const ChipInputField: React.FC<{
  values: string[];
  onValuesChange: (v: string[]) => void;
  label: string;
}> = ({ values, onValuesChange, label }) => {
  const [inputValue, setInputValue] = useState("");

  // Checks whether we've added this item already.
  const itemChipExists = (item) => values.includes(item);

  // Add an item to the list, if it's valid and isn't already there.
  const addItems = (itemsToAdd) => {
    const validatedItems = itemsToAdd
      .map((e) => e.trim())
      .filter((item) => !itemChipExists(item));

    const newItems = [...values, ...validatedItems];

    onValuesChange(newItems);
    setInputValue("");
  };

  // Remove an item from the list.
  const removeItem = (item) => {
    const index = values.findIndex((e) => e === item);
    if (index !== -1) {
      const newItems = [...values];
      newItems.splice(index, 1);
      onValuesChange(newItems);
    }
  };

  // Save input field contents in state when changed.
  const handleChange = (e) => {
    setInputValue(e.target.value);
  };

  // Validate and add the item if we press tab, enter or comma.
  const handleKeyDown = (e) => {
    if (["Enter", "Tab", ","].includes(e.key)) {
      e.preventDefault();
      addItems([inputValue]);
    }
  };

  // Split and add items when pasting.
  const handlePaste = (e) => {
    e.preventDefault();

    const pastedData = e.clipboardData.getData("text");
    const pastedItems = pastedData.split(",");
    addItems(pastedItems);
  };

  const handleCloseClick = (item) => {
    removeItem(item);
  };

  const required = false;

  return (
    <Field.Root mb={4} required={required}>
      <Field.Label>
        {label} {required && <Field.RequiredIndicator />}
      </Field.Label>

      <ChipList items={values} onCloseClick={handleCloseClick} />

      <ChipInput
        placeholder="enter items"
        onPaste={handlePaste}
        onKeyDown={handleKeyDown}
        onChange={handleChange}
        value={inputValue}
        variant="subtle"
      />
    </Field.Root>
  );
};

export default ChipInputField;
