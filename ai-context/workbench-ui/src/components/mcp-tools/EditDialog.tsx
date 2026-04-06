import React, { useEffect, useState } from "react";

import { Trash, SendHorizontal } from "lucide-react";

import { Portal, Button, Dialog, CloseButton } from "@chakra-ui/react";

import { useSocket } from "@trustgraph/react-provider";
import { useMcpTools } from "@trustgraph/react-state";
import TextField from "../common/TextField";
import { toaster } from "../ui/toaster";

const EditDialog = ({ open, onOpenChange, onComplete, id, create }) => {
  const socket = useSocket();
  const { updateTool, createTool, deleteTool } = useMcpTools();

  const [newId, setNewId] = useState("");
  const [remoteName, setRemoteName] = useState("");
  const [url, setUrl] = useState("");

  useEffect(() => {
    if (!id || create) return;

    socket
      .config()
      .getConfig([{ type: "mcp", key: id }])
      .then((x) => {
        return JSON.parse(x.values[0].value);
      })
      .then((x) => {
        console.log("Loaded MCP tool data:", x);
        // Store MCP tool information
        setRemoteName(x["remote-name"] || "");
        setUrl(x.url || "");
      })
      .catch((e) => {
        console.log("Error:", e);
        toaster.create({
          title: "Error: " + e.toString(),
          type: "error",
        });
      });
  }, [id, create, socket]);

  // Clear form when dialog is opened for creation
  useEffect(() => {
    if (create) {
      setNewId("");
      setRemoteName("");
      setUrl("");
    }
  }, [create, open]);

  const onEdit = () => {
    // Build the MCP tool structure
    const toolStruct = {
      "remote-name": remoteName,
      url: url,
    };

    if (create) {
      createTool({ id: newId, tool: toolStruct, onSuccess: onComplete });
    } else {
      updateTool({ id, tool: toolStruct, onSuccess: onComplete });
    }
  };

  const onDelete = () => {
    if (create) return;
    deleteTool({ id, onSuccess: onComplete });
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
          <Dialog.Content>
            <Dialog.Header>
              {create && <Dialog.Title>Create MCP Tool</Dialog.Title>}

              {!create && (
                <Dialog.Title>
                  Edit MCP Tool: <code>{id}</code>
                </Dialog.Title>
              )}
            </Dialog.Header>
            <Dialog.Body>
              {create && (
                <TextField
                  label="Tool ID"
                  placeholder="Enter a unique tool ID"
                  value={newId}
                  onValueChange={(v) => setNewId(v)}
                  required={true}
                />
              )}

              <TextField
                label="Remote Name"
                placeholder="Enter the remote MCP tool name"
                value={remoteName}
                onValueChange={(v) => setRemoteName(v)}
                required={true}
              />

              <TextField
                label="MCP Endpoint URL"
                placeholder="Enter MCP endpoint URL"
                value={url}
                onValueChange={(v) => setUrl(v)}
                required={true}
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              {
                // If a 'create' operation, there's nothing to delete, only
                // present if an existing tool exists
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
