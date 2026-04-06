import React, { useEffect, useState, useRef } from "react";

import { Trash, SendHorizontal } from "lucide-react";

import { Portal, Button, Dialog, Box, CloseButton } from "@chakra-ui/react";

import { usePrompts } from "@trustgraph/react-state";
import { useSocket } from "@trustgraph/react-provider";
import SelectField from "../common/SelectField";
import TextAreaField from "../common/TextAreaField";
import TextField from "../common/TextField";
import { toaster } from "../ui/toaster";

const EditDialog = ({ open, onOpenChange, onComplete, id, create }) => {
  const socket = useSocket();
  const { updatePrompt, createPrompt, deletePrompt } = usePrompts();

  const [newId, setNewId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [format, setFormat] = useState("");
  const [schema, setSchema] = useState("");

  useEffect(() => {
    if (create) {
      setFormat("text");
      return;
    }

    if (!id) return;

    socket
      .config()
      .getConfig([{ type: "prompt", key: "template." + id }])
      .then((x) => {
        return JSON.parse(x.values[0].value);
      })
      .then((x) => {
        // Store flow information
        setPrompt(x.prompt);
        setFormat(x["response-type"]);
        if (x.schema) setSchema(JSON.stringify(x.schema, null, 4));
        else setSchema("");
      })
      .catch((e) => {
        console.log("Error:", e);
        toaster.create({
          title: "Error: " + e.toString(),
          type: "error",
        });
      });
  }, [id, create, socket]);

  const formatOptions = [
    {
      value: "json",
      label: "JSON",
      description: "Structured output using JSON",
    },
    { value: "text", label: "text", description: "Unstructured text output" },
  ];

  const contentRef = useRef<HTMLDivElement>(null);

  const onEdit = () => {
    // Build the prompt structure
    const promptStruct = {
      prompt: prompt,
      "response-type": format,
    };

    // Add schema if not an empty string.  Schema is an object embedded
    // in the structure.  It must be JSON schema if specified, we're
    // not checking that here.
    if (schema) {
      const parsedSchema = JSON.parse(schema);
      promptStruct["schema"] = parsedSchema;
    }

    if (create) {
      createPrompt({
        id: newId,
        prompt: promptStruct,
        onSuccess: onComplete,
      });
    } else {
      updatePrompt({ id, prompt: promptStruct, onSuccess: onComplete });
    }
  };

  const onDelete = () => {
    if (create) return;
    deletePrompt({ id, onSuccess: onComplete });
  };

  return (
    <Dialog.Root
      placement="center"
      size="xl"
      open={open}
      onOpenChange={(x) => {
        onOpenChange(x.open);
      }}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content ref={contentRef}>
            <Dialog.Header>
              {create && <Dialog.Title>Create prompt</Dialog.Title>}

              {!create && (
                <Dialog.Title>
                  Edit prompt: <code>{id}</code>
                </Dialog.Title>
              )}
            </Dialog.Header>
            <Dialog.Body>
              {create && (
                <TextField
                  label="Prompt ID"
                  placeholder="Enter a unique prompt ID"
                  value={newId}
                  onValueChange={(v) => setNewId(v)}
                  required={true}
                />
              )}

              <TextAreaField
                label="Prompt"
                placeholder="Enter AI prompt"
                value={prompt}
                onValueChange={(v) => setPrompt(v)}
                required={true}
              />

              <Box mt={5}>With following flows:</Box>

              <Box mt={5}>
                <SelectField
                  label="Format"
                  items={formatOptions}
                  value={format ? [format] : []}
                  onValueChange={(x) => {
                    setFormat(Array.isArray(x) ? x[0] : x);
                  }}
                  contentRef={contentRef}
                />
              </Box>

              <TextAreaField
                label="Schema"
                placeholder="Enter JSON schema for validation"
                value={schema}
                onValueChange={(v) => setSchema(v)}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              {
                // If a 'create' operation, there's nothing to delete, only
                // present if an existing prompt exists
              }
              {!create && (
                <Button
                  variant="solid"
                  onClick={() => onDelete()}
                  colorPalette="red"
                >
                  <Trash /> Delete
                </Button>
              )}
              <Button onClick={() => onEdit()} colorPalette="primary">
                <SendHorizontal /> Submit
              </Button>
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

export default EditDialog;
