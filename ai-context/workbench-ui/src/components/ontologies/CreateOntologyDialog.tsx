import React, { useState } from "react";
import {
  Dialog,
  Portal,
  CloseButton,
  Button,
  VStack,
  HStack,
  Input,
  Textarea,
  Field,
  RadioCard,
} from "@chakra-ui/react";
import { useOntologies, Ontology } from "@trustgraph/react-state";

interface CreateOntologyDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: (ontologyId: string) => void;
}

type StartMode = "blank" | "ai-assisted" | "import";

export const CreateOntologyDialog: React.FC<CreateOntologyDialogProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const { createOntology } = useOntologies();

  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [namespace, setNamespace] = useState("http://example.org/");
  const [startMode, setStartMode] = useState<StartMode>("blank");
  const [errors, setErrors] = useState<string[]>([]);

  const handleSubmit = () => {
    const validationErrors: string[] = [];

    if (!id.trim()) validationErrors.push("ID is required");
    if (!name.trim()) validationErrors.push("Name is required");
    if (!description.trim()) validationErrors.push("Description is required");
    if (!namespace.trim()) validationErrors.push("Namespace URI is required");

    // Basic kebab-case validation for ID
    if (id && !/^[a-z0-9-]+$/.test(id)) {
      validationErrors.push(
        "ID must be kebab-case (lowercase letters, numbers, and hyphens only)",
      );
    }

    // Basic URI validation for namespace
    if (namespace && !namespace.startsWith("http")) {
      validationErrors.push(
        "Namespace must be a valid URI starting with http",
      );
    }

    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    // Create minimal ontology structure
    const ontology: Ontology = {
      metadata: {
        name: name.trim(),
        description: description.trim(),
        version: "1.0.0",
        created: new Date().toISOString(),
        modified: new Date().toISOString(),
        creator: "current-user", // TODO: Get from auth context
        namespace: namespace.trim(),
        imports: ["http://www.w3.org/2002/07/owl#"],
      },
      classes: {},
      objectProperties: {},
      datatypeProperties: {},
    };

    createOntology({
      id: id.trim(),
      ontology,
      onSuccess: () => {
        resetForm();
        onClose();
        if (onCreated) {
          onCreated(id.trim());
        }
      },
    });
  };

  const resetForm = () => {
    setId("");
    setName("");
    setDescription("");
    setNamespace("http://example.org/");
    setStartMode("blank");
    setErrors([]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  return (
    <Dialog.Root
      open={isOpen}
      onOpenChange={(details) => {
        if (!details.open) handleClose();
      }}
      size="lg"
      placement="center"
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>Create New Ontology</Dialog.Title>
            </Dialog.Header>

            <Dialog.Body>
              <VStack gap={4} align="stretch">
                {errors.length > 0 && (
                  <VStack
                    gap={2}
                    p={3}
                    borderWidth="1px"
                    borderColor="red.500"
                    borderRadius="md"
                    bg="red.50"
                  >
                    {errors.map((error, index) => (
                      <div
                        key={index}
                        style={{ color: "red", fontSize: "14px" }}
                      >
                        {error}
                      </div>
                    ))}
                  </VStack>
                )}

                <Field.Root required>
                  <Field.Label>
                    Ontology ID
                    <Field.RequiredIndicator />
                  </Field.Label>
                  <Input
                    value={id}
                    onChange={(e) =>
                      setId(
                        e.target.value
                          .toLowerCase()
                          .replace(/[^a-z0-9-]/g, ""),
                      )
                    }
                    placeholder="domain-model"
                  />
                </Field.Root>

                <Field.Root required>
                  <Field.Label>
                    Name
                    <Field.RequiredIndicator />
                  </Field.Label>
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Domain Model Ontology"
                  />
                </Field.Root>

                <Field.Root required>
                  <Field.Label>
                    Description
                    <Field.RequiredIndicator />
                  </Field.Label>
                  <Textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="A comprehensive ontology for modeling domain concepts..."
                    rows={3}
                  />
                </Field.Root>

                <Field.Root required>
                  <Field.Label>
                    Namespace URI
                    <Field.RequiredIndicator />
                  </Field.Label>
                  <Input
                    value={namespace}
                    onChange={(e) => setNamespace(e.target.value)}
                    placeholder="http://example.org/domain/"
                  />
                </Field.Root>

                <Field.Root>
                  <Field.Label>How would you like to start?</Field.Label>
                  <RadioCard.Root
                    value={startMode}
                    onValueChange={(details) =>
                      setStartMode(details.value as StartMode)
                    }
                  >
                    <VStack gap={2} align="stretch">
                      <RadioCard.Item value="blank">
                        <RadioCard.ItemHiddenInput />
                        <RadioCard.ItemControl>
                          <RadioCard.ItemContent>
                            <RadioCard.ItemText>
                              Start with blank ontology
                            </RadioCard.ItemText>
                            <RadioCard.ItemDescription>
                              Create classes and properties manually
                            </RadioCard.ItemDescription>
                          </RadioCard.ItemContent>
                          <RadioCard.ItemIndicator />
                        </RadioCard.ItemControl>
                      </RadioCard.Item>

                      <RadioCard.Item value="ai-assisted" disabled>
                        <RadioCard.ItemHiddenInput />
                        <RadioCard.ItemControl>
                          <RadioCard.ItemContent>
                            <RadioCard.ItemText>
                              Use AI assistant to bootstrap
                            </RadioCard.ItemText>
                            <RadioCard.ItemDescription>
                              Coming in Phase 7 - Let AI suggest initial
                              structure
                            </RadioCard.ItemDescription>
                          </RadioCard.ItemContent>
                          <RadioCard.ItemIndicator />
                        </RadioCard.ItemControl>
                      </RadioCard.Item>

                      <RadioCard.Item value="import" disabled>
                        <RadioCard.ItemHiddenInput />
                        <RadioCard.ItemControl>
                          <RadioCard.ItemContent>
                            <RadioCard.ItemText>
                              Import from file
                            </RadioCard.ItemText>
                            <RadioCard.ItemDescription>
                              Coming in Phase 6 - Load existing OWL/RDF
                              ontology
                            </RadioCard.ItemDescription>
                          </RadioCard.ItemContent>
                          <RadioCard.ItemIndicator />
                        </RadioCard.ItemControl>
                      </RadioCard.Item>
                    </VStack>
                  </RadioCard.Root>
                </Field.Root>
              </VStack>
            </Dialog.Body>

            <Dialog.Footer>
              <HStack gap={3}>
                <Button variant="ghost" onClick={handleClose}>
                  Cancel
                </Button>
                <Button colorPalette="primary" onClick={handleSubmit}>
                  Create & Open Editor
                </Button>
              </HStack>
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
