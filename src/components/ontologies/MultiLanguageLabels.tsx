import React, { useState } from "react";
import {
  VStack,
  HStack,
  Box,
  Text,
  Input,
  Button,
  IconButton,
  Field,
  Select,
} from "@chakra-ui/react";
import { Plus, Trash2 } from "lucide-react";

interface LanguageLabel {
  value: string;
  lang?: string;
}

interface MultiLanguageLabelsProps {
  label: string;
  labels: LanguageLabel[];
  onLabelsChange: (labels: LanguageLabel[]) => void;
}

const COMMON_LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
  { value: "ru", label: "Russian" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "zh", label: "Chinese" },
  { value: "ar", label: "Arabic" },
  { value: "hi", label: "Hindi" },
];

export const MultiLanguageLabels: React.FC<MultiLanguageLabelsProps> = ({
  label,
  labels,
  onLabelsChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(labels.length > 1);

  const handleAddLabel = () => {
    const newLabels = [...labels, { value: "", lang: "en" }];
    onLabelsChange(newLabels);
    setIsExpanded(true);
  };

  const handleUpdateLabel = (
    index: number,
    field: "value" | "lang",
    value: string,
  ) => {
    const newLabels = [...labels];
    if (field === "value") {
      newLabels[index].value = value;
    } else {
      newLabels[index].lang = value;
    }
    onLabelsChange(newLabels);
  };

  const handleRemoveLabel = (index: number) => {
    const newLabels = labels.filter((_, i) => i !== index);
    onLabelsChange(newLabels);
    if (newLabels.length <= 1) {
      setIsExpanded(false);
    }
  };

  const primaryLabel = labels[0] || { value: "", lang: "en" };

  return (
    <VStack align="stretch" spacing={3}>
      <Field.Root required>
        <Field.Label>
          {label}
          <Field.RequiredIndicator />
        </Field.Label>
        <HStack>
          <Input
            flex="1"
            value={primaryLabel.value}
            onChange={(e) => handleUpdateLabel(0, "value", e.target.value)}
            placeholder={`${label} (primary)`}
          />
          {!isExpanded && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsExpanded(true)}
              colorPalette="blue"
            >
              <Plus size={14} style={{ marginRight: "4px" }} />
              Add Language
            </Button>
          )}
        </HStack>
        <Text fontSize="xs" color="gray.500" mt={1}>
          Primary label ({primaryLabel.lang || "en"})
        </Text>
      </Field.Root>

      {isExpanded && (
        <VStack align="stretch" spacing={2}>
          <HStack justify="space-between">
            <Text fontSize="sm" fontWeight="medium" color="gray.700">
              Additional Languages
            </Text>
            <Button
              size="xs"
              variant="ghost"
              onClick={handleAddLabel}
              colorPalette="blue"
            >
              <Plus size={12} style={{ marginRight: "4px" }} />
              Add
            </Button>
          </HStack>

          {labels.slice(1).map((labelItem, index) => (
            <HStack key={index + 1} spacing={2}>
              <Select.Root
                size="sm"
                value={labelItem.lang || "en"}
                onValueChange={(e) =>
                  handleUpdateLabel(index + 1, "lang", e.value[0])
                }
              >
                <Select.Trigger minW="120px">
                  <Select.ValueText />
                </Select.Trigger>
                <Select.Content>
                  {COMMON_LANGUAGES.map((lang) => (
                    <Select.Item key={lang.value} item={lang.value}>
                      <Select.ItemText>{lang.label}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.Content>
              </Select.Root>

              <Input
                flex="1"
                size="sm"
                value={labelItem.value}
                onChange={(e) =>
                  handleUpdateLabel(index + 1, "value", e.target.value)
                }
                placeholder={`${label} in ${COMMON_LANGUAGES.find((l) => l.value === labelItem.lang)?.label || labelItem.lang}`}
              />

              <IconButton
                size="sm"
                variant="ghost"
                colorPalette="red"
                onClick={() => handleRemoveLabel(index + 1)}
                aria-label={`Remove ${labelItem.lang} label`}
              >
                <Trash2 size={12} />
              </IconButton>
            </HStack>
          ))}

          {labels.length <= 1 && (
            <Box p={2} bg="gray.50" borderRadius="md">
              <Text fontSize="xs" color="gray.600" textAlign="center">
                Click "Add" to provide labels in additional languages
              </Text>
            </Box>
          )}

          <Button
            size="xs"
            variant="ghost"
            onClick={() => setIsExpanded(false)}
            alignSelf="flex-end"
          >
            Collapse
          </Button>
        </VStack>
      )}
    </VStack>
  );
};
