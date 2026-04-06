import React, { useState } from "react";
import { Box, Table, Button, Input, IconButton, Text } from "@chakra-ui/react";
import { Plus, Trash2 } from "lucide-react";

interface NamespacePrefixEditorProps {
  namespaces: Record<string, string>;
  onChange: (namespaces: Record<string, string>) => void;
}

export const NamespacePrefixEditor: React.FC<NamespacePrefixEditorProps> = ({
  namespaces,
  onChange,
}) => {
  const [editingPrefix, setEditingPrefix] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<{
    prefix: string;
    uri: string;
  } | null>(null);

  const entries = Object.entries(namespaces || {});

  const handleAddPrefix = () => {
    const newPrefix = "";
    const newUri = "";
    setEditingPrefix("__new__");
    setEditingValue({ prefix: newPrefix, uri: newUri });
  };

  const handleSaveEdit = () => {
    if (!editingValue) return;

    const newNamespaces = { ...namespaces };

    // If editing existing entry, remove old key
    if (editingPrefix && editingPrefix !== "__new__") {
      delete newNamespaces[editingPrefix];
    }

    // Add new/updated entry
    if (editingValue.prefix.trim()) {
      newNamespaces[editingValue.prefix.trim()] = editingValue.uri.trim();
    }

    onChange(newNamespaces);
    setEditingPrefix(null);
    setEditingValue(null);
  };

  const handleCancelEdit = () => {
    setEditingPrefix(null);
    setEditingValue(null);
  };

  const handleDelete = (prefix: string) => {
    const newNamespaces = { ...namespaces };
    delete newNamespaces[prefix];
    onChange(newNamespaces);
  };

  const handleStartEdit = (prefix: string, uri: string) => {
    setEditingPrefix(prefix);
    setEditingValue({ prefix, uri });
  };

  return (
    <Box>
      <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb={2}>
        Namespace Prefixes
      </Text>

      <Table.Root size="sm" variant="outline">
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader width="30%">Prefix</Table.ColumnHeader>
            <Table.ColumnHeader>Namespace URI</Table.ColumnHeader>
            <Table.ColumnHeader width="60px"></Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {entries.map(([prefix, uri]) => (
            <Table.Row key={prefix}>
              <Table.Cell>
                {editingPrefix === prefix ? (
                  <Input
                    size="sm"
                    value={editingValue?.prefix || ""}
                    onChange={(e) =>
                      setEditingValue({
                        prefix: e.target.value,
                        uri: editingValue?.uri || "",
                      })
                    }
                    onBlur={handleSaveEdit}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveEdit();
                      if (e.key === "Escape") handleCancelEdit();
                    }}
                    autoFocus
                  />
                ) : (
                  <Text
                    fontFamily="mono"
                    fontSize="sm"
                    cursor="pointer"
                    onClick={() => handleStartEdit(prefix, uri)}
                  >
                    {prefix}
                  </Text>
                )}
              </Table.Cell>
              <Table.Cell>
                {editingPrefix === prefix ? (
                  <Input
                    size="sm"
                    value={editingValue?.uri || ""}
                    onChange={(e) =>
                      setEditingValue({
                        prefix: editingValue?.prefix || "",
                        uri: e.target.value,
                      })
                    }
                    onBlur={handleSaveEdit}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveEdit();
                      if (e.key === "Escape") handleCancelEdit();
                    }}
                  />
                ) : (
                  <Text
                    fontFamily="mono"
                    fontSize="sm"
                    cursor="pointer"
                    onClick={() => handleStartEdit(prefix, uri)}
                    css={{
                      wordBreak: "break-all",
                    }}
                  >
                    {uri}
                  </Text>
                )}
              </Table.Cell>
              <Table.Cell>
                <IconButton
                  size="sm"
                  variant="ghost"
                  aria-label="Delete prefix"
                  onClick={() => handleDelete(prefix)}
                >
                  <Trash2 size={14} />
                </IconButton>
              </Table.Cell>
            </Table.Row>
          ))}

          {editingPrefix === "__new__" && (
            <Table.Row>
              <Table.Cell>
                <Input
                  size="sm"
                  placeholder="prefix"
                  value={editingValue?.prefix || ""}
                  onChange={(e) =>
                    setEditingValue({
                      prefix: e.target.value,
                      uri: editingValue?.uri || "",
                    })
                  }
                  onBlur={handleSaveEdit}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveEdit();
                    if (e.key === "Escape") handleCancelEdit();
                  }}
                  autoFocus
                />
              </Table.Cell>
              <Table.Cell>
                <Input
                  size="sm"
                  placeholder="http://example.org/namespace#"
                  value={editingValue?.uri || ""}
                  onChange={(e) =>
                    setEditingValue({
                      prefix: editingValue?.prefix || "",
                      uri: e.target.value,
                    })
                  }
                  onBlur={handleSaveEdit}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveEdit();
                    if (e.key === "Escape") handleCancelEdit();
                  }}
                />
              </Table.Cell>
              <Table.Cell>
                <IconButton
                  size="sm"
                  variant="ghost"
                  aria-label="Cancel"
                  onClick={handleCancelEdit}
                >
                  <Trash2 size={14} />
                </IconButton>
              </Table.Cell>
            </Table.Row>
          )}
        </Table.Body>
      </Table.Root>

      {editingPrefix !== "__new__" && (
        <Button
          size="sm"
          variant="ghost"
          mt={2}
          onClick={handleAddPrefix}
          leftIcon={<Plus size={14} />}
        >
          Add Prefix
        </Button>
      )}
    </Box>
  );
};
