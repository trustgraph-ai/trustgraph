import React, { useEffect, useState, useRef } from "react";

import { Trash, SendHorizontal, Plus } from "lucide-react";

import { Portal, Button, Dialog, Box, CloseButton } from "@chakra-ui/react";

import { useSocket } from "@trustgraph/react-provider";
import { useAgentTools } from "@trustgraph/react-state";
import { useMcpTools } from "@trustgraph/react-state";
import { usePrompts } from "@trustgraph/react-state";
import SelectField from "../common/SelectField";
import TextAreaField from "../common/TextAreaField";
import TextField from "../common/TextField";
import ChipInputField from "../common/ChipInputField";
import { toaster } from "../ui/toaster";
import EditableArgumentsTable from "./EditableArgumentsTable";

const EditDialog = ({ open, onOpenChange, onComplete, id, create }) => {
  const socket = useSocket();
  const { updateTool, createTool, deleteTool } = useAgentTools();
  const { tools: mcpTools } = useMcpTools();
  const { prompts } = usePrompts();

  const [newId, setNewId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState("knowledge-query");
  const [args, setArgs] = useState([]);
  const [templateId, setTemplateId] = useState("");
  const [mcpToolId, setMcpToolId] = useState("");
  const [collection, setCollection] = useState("");
  const [group, setGroup] = useState([]);
  const [state, setState] = useState("");
  const [applicableStates, setApplicableStates] = useState([]);

  const [editArgIx, setEditArgIx] = useState(-1);

  useEffect(() => {
    if (!id) return;

    socket
      .config()
      .getConfig([{ type: "tool", key: id }])
      .then((x) => {
        return JSON.parse(x.values[0].value);
      })
      .then((x) => {
        // Store flow information
        setName(x.name || "");
        setDescription(x.description);
        setType(x.type);
        setArgs(x.arguments || []);
        // Handle both old 'template' and new 'template_id' attributes
        setTemplateId(x.template_id || x.template || "");
        // Handle both old 'mcp-tool' and new 'mcp_tool_id' attributes
        setMcpToolId(x.mcp_tool_id || x["mcp-tool"] || "");
        // Handle collection attribute for knowledge-query tools
        setCollection(x.collection || "");
        // Handle new optional fields
        setGroup(x.group || []);
        setState(x.state || "");
        setApplicableStates(x["applicable-states"] || []);
      })
      .catch((e) => {
        console.log("Error:", e);
        toaster.create({
          title: "Error: " + e.toString(),
          type: "error",
        });
      });
  }, [id, create, socket]);

  const typeOptions = [
    {
      value: "text-completion",
      label: "Text completion",
      description: "Consults an LLM for a response with no further knowledge",
    },
    {
      value: "knowledge-query",
      label: "Knowledge query",
      description: "Uses the GraphRAG service for knowledge",
    },
    {
      value: "structured-query",
      label: "Structured Query",
      description:
        "Execute natural language questions against records in a structured data / object store",
    },
    {
      value: "mcp-tool",
      label: "MCP Tool",
      description: "Uses the mcp-tool service to access a remote MCP tool",
    },
    {
      value: "prompt",
      label: "Prompt Template",
      description: "Executes a prompt template with variables",
    },
  ];

  const contentRef = useRef<HTMLDivElement>(null);

  // Create options for MCP tools select menu
  const mcpToolOptions = mcpTools.map(([id]) => ({
    value: id,
    label: id,
    description: id,
  }));

  // Create options for prompt templates select menu
  const promptTemplateOptions = prompts.map(([id]) => ({
    value: id,
    label: id,
    description: id,
  }));

  const onEdit = () => {
    // Build the tool structure
    const toolStruct = {
      id: create ? newId : id,
      name: name,
      description: description,
      type: type,
      arguments: args,
      ...(type === "prompt" && templateId && { template: templateId }),
      ...(type === "mcp-tool" && mcpToolId && { "mcp-tool": mcpToolId }),
      ...((type === "knowledge-query" || type === "structured-query") &&
        collection && { collection: collection }),
      ...(group && group.length > 0 && { group: group }),
      ...(state && { state: state }),
      ...(applicableStates &&
        applicableStates.length > 0 && {
          "applicable-states": applicableStates,
        }),
    };

    if (create) {
      createTool({ id: newId, tool: toolStruct, onSuccess: onComplete });
    } else {
      updateTool({ id, tool: toolStruct, onSuccess: onComplete });
    }
  };

  const addArgument = () => {
    setArgs((x) => [
      ...x,
      {
        name: "argname",
        description: "???",
        type: "string",
      },
    ]);
  };

  const deleteArgument = (index) => {
    setArgs((x) => x.filter((_, i) => i !== index));
  };

  const setArgAttr = (id, key, value) => {
    const newArgs = args.map((arg, ix) => {
      if (id == ix) {
        return {
          ...arg,
          [key]: value,
        };
      } else {
        return arg;
      }
    });
    setArgs(newArgs);
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
          <Dialog.Content ref={contentRef}>
            <Dialog.Header>
              {create && <Dialog.Title>Create tool</Dialog.Title>}

              {!create && (
                <Dialog.Title>
                  Edit tool: <code>{id}</code>
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
                label="Tool Name"
                placeholder="Enter a human-readable name for the tool"
                value={name}
                onValueChange={(v) => setName(v)}
                required={true}
              />

              <TextAreaField
                label="Description of the tool"
                placeholder="Description"
                value={description}
                onValueChange={(v) => setDescription(v)}
                required={true}
              />

              <SelectField
                label="Tool type"
                items={typeOptions}
                value={type ? [type] : []}
                onValueChange={(v) => setType(v[0])}
                contentRef={contentRef}
              />

              {type === "prompt" && (
                <SelectField
                  label="Template ID"
                  items={promptTemplateOptions}
                  value={templateId ? [templateId] : []}
                  onValueChange={(v) => setTemplateId(v[0] || "")}
                  contentRef={contentRef}
                />
              )}

              {type === "mcp-tool" && (
                <SelectField
                  label="MCP Tool ID"
                  items={mcpToolOptions}
                  value={mcpToolId ? [mcpToolId] : []}
                  onValueChange={(v) => setMcpToolId(v[0] || "")}
                  contentRef={contentRef}
                />
              )}

              {(type === "knowledge-query" || type === "structured-query") && (
                <TextField
                  label="Collection"
                  placeholder="Enter the knowledge collection (optional)"
                  value={collection}
                  onValueChange={(v) => setCollection(v)}
                  required={false}
                />
              )}

              <ChipInputField
                label="Groups"
                values={group}
                onValuesChange={setGroup}
              />

              <TextField
                label="Next State"
                placeholder="Optional: Specify which state the agent should move to after successfully using this tool. Used to create multi-step workflows."
                value={state}
                onValueChange={(v) => setState(v)}
                required={false}
              />

              <ChipInputField
                label="Applicable States"
                values={applicableStates}
                onValuesChange={setApplicableStates}
              />

              {(type === "prompt" || type === "mcp-tool") && (
                <>
                  <EditableArgumentsTable
                    args={args}
                    editArgIx={editArgIx}
                    setEditArgIx={setEditArgIx}
                    setArgAttr={setArgAttr}
                    deleteArg={deleteArgument}
                  />

                  <Box mt={5}>
                    <Button
                      variant="solid"
                      onClick={() => addArgument()}
                      colorPalette="primary"
                      size="xs"
                    >
                      <Plus /> add argument
                    </Button>
                  </Box>
                </>
              )}
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
