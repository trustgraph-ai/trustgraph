import React, { useState, useRef } from "react";
import {
  Box,
  HStack,
  Input,
  Button,
  Badge,
  Flex,
  CloseButton,
  Text,
} from "@chakra-ui/react";

interface EnumValueManagerProps {
  values: string[];
  onAddValue: (value: string) => void;
  onRemoveValue: (value: string) => void;
}

export const EnumValueManager: React.FC<EnumValueManagerProps> = ({
  values = [],
  onAddValue,
  onRemoveValue,
}) => {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleAdd = () => {
    if (inputValue.trim() && !values.includes(inputValue.trim())) {
      onAddValue(inputValue.trim());
      setInputValue("");
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <Box>
      <Text mb={2}>Enum Values</Text>
      <HStack mb={2}>
        <Input
          ref={inputRef}
          placeholder="Add enum value"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <Button
          size="sm"
          onClick={handleAdd}
          colorPalette="primary"
          disabled={!inputValue.trim() || values.includes(inputValue.trim())}
        >
          Add
        </Button>
      </HStack>
      {values.length > 0 ? (
        <Flex wrap="wrap" gap={2}>
          {values.map((value) => (
            <Badge
              key={value}
              colorPalette="accent"
              borderRadius="full"
              px={3}
              py={1}
              display="flex"
              alignItems="center"
              gap={2}
            >
              {value}
              <CloseButton
                size="sm"
                onClick={() => onRemoveValue(value)}
                aria-label={`Remove ${value}`}
              />
            </Badge>
          ))}
        </Flex>
      ) : (
        <Text fontSize="sm" color="fg.muted">
          No values added yet
        </Text>
      )}
    </Box>
  );
};
