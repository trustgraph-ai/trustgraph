# Collections Support for TrustGraph UI

## Overview

This document specifies the implementation of collections support in the TrustGraph UI. Collections provide a way to organize and manage groups of documents with metadata including name, description, and tags. The feature adds collection management capabilities to the Library page through a tabbed interface.

## API Integration

### Backend API Summary

The TrustGraph API provides three collection operations via the `collection-management` endpoint:

#### 1. List Collections
- **Operation**: `list-collections`
- **Request**:
  ```json
  {
    "operation": "list-collections",
    "user": "username",
    "tag_filter": ["tag1", "tag2"]  // optional
  }
  ```
- **Response**: Array of collection metadata objects
- **Fields**: user, collection, name, description, tags, created_at, updated_at

#### 2. Update Collection (also creates)
- **Operation**: `update-collection`
- **Request**:
  ```json
  {
    "operation": "update-collection",
    "user": "username",
    "collection": "collection-id",
    "name": "Display Name",          // optional
    "description": "Description",     // optional
    "tags": ["tag1", "tag2"]         // optional
  }
  ```
- **Response**: Single collection metadata object in `collections` array
- **Note**: Creates collection if it doesn't exist; updates if it does

#### 3. Delete Collection
- **Operation**: `delete-collection`
- **Request**:
  ```json
  {
    "operation": "delete-collection",
    "user": "username",
    "collection": "collection-id"
  }
  ```
- **Response**: Empty object `{}`

### Collection Metadata Structure

```typescript
interface CollectionMetadata {
  user: string;
  collection: string;        // Collection ID (unique identifier)
  name: string;              // Display name
  description: string;       // Description text
  tags: string[];            // Array of tags
  created_at: string;        // ISO timestamp
  updated_at: string;        // ISO timestamp
}
```

## Implementation Plan

### Phase 1: Socket Layer Integration

**File**: `src/api/trustgraph/trustgraph-socket.ts`

Add collection management methods to the socket interface:

```typescript
// Add to Socket interface
export interface Socket {
  // ... existing methods ...

  // Collection management
  collectionManagement: () => CollectionManagement;
}

// New CollectionManagement interface
export interface CollectionManagement {
  listCollections: (
    user: string,
    tagFilter?: string[]
  ) => Promise<CollectionMetadata[]>;

  updateCollection: (
    user: string,
    collection: string,
    name?: string,
    description?: string,
    tags?: string[]
  ) => Promise<CollectionMetadata>;

  deleteCollection: (
    user: string,
    collection: string
  ) => Promise<void>;
}

// Implementation in BaseApi class
class BaseApi {
  // ... existing methods ...

  collectionManagement(): CollectionManagement {
    return {
      listCollections: async (user, tagFilter) => {
        const request = {
          operation: "list-collections",
          user,
          ...(tagFilter && { tag_filter: tagFilter }),
        };
        const response = await this.request("collection-management", request);
        return response.collections || [];
      },

      updateCollection: async (user, collection, name, description, tags) => {
        const request = {
          operation: "update-collection",
          user,
          collection,
          ...(name !== undefined && { name }),
          ...(description !== undefined && { description }),
          ...(tags !== undefined && { tags }),
        };
        const response = await this.request("collection-management", request);
        return response.collections[0];
      },

      deleteCollection: async (user, collection) => {
        const request = {
          operation: "delete-collection",
          user,
          collection,
        };
        await this.request("collection-management", request);
      },
    };
  }
}
```

### Phase 2: State Management Hook

**File**: `src/state/collections.ts` (new file)

Create a React Query-based state management hook following the library.ts pattern:

```typescript
import { useQueryClient, useQuery, useMutation } from "@tanstack/react-query";
import { useSocket, useConnectionState } from "../api/trustgraph/socket";
import { useNotification } from "./notify";
import { useActivity } from "./activity";
import { useSettings } from "./settings";

export interface CollectionMetadata {
  user: string;
  collection: string;
  name: string;
  description: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export const useCollections = () => {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const queryClient = useQueryClient();
  const notify = useNotification();
  const { settings } = useSettings();

  const isSocketReady =
    connectionState?.status === "authenticated" ||
    connectionState?.status === "unauthenticated";

  // Query for fetching all collections
  const collectionsQuery = useQuery({
    queryKey: ["collections", settings.user],
    enabled: isSocketReady && !!settings.user,
    queryFn: () => {
      return socket.collectionManagement().listCollections(settings.user);
    },
  });

  // Mutation for creating/updating a collection
  const updateCollectionMutation = useMutation({
    mutationFn: ({ collection, name, description, tags, onSuccess }) => {
      return socket
        .collectionManagement()
        .updateCollection(
          settings.user,
          collection,
          name,
          description,
          tags
        )
        .then(() => {
          if (onSuccess) onSuccess();
        });
    },
    onError: (err) => {
      console.log("Error:", err);
      notify.error(err.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      notify.success("Collection saved successfully");
    },
  });

  // Mutation for deleting collections
  const deleteCollectionsMutation = useMutation({
    mutationFn: ({ collections, onSuccess }) => {
      return Promise.all(
        collections.map((collection) =>
          socket
            .collectionManagement()
            .deleteCollection(settings.user, collection)
        )
      ).then(() => {
        if (onSuccess) onSuccess();
      });
    },
    onError: (err) => {
      console.log("Error:", err);
      notify.error(err.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      notify.success("Collections deleted successfully");
    },
  });

  // Activity indicators
  useActivity(collectionsQuery.isLoading, "Loading collections");
  useActivity(updateCollectionMutation.isPending, "Saving collection");
  useActivity(deleteCollectionsMutation.isPending, "Deleting collections");

  return {
    // Collection data and query state
    collections: collectionsQuery.data || [],
    isLoading: collectionsQuery.isLoading,
    isError: collectionsQuery.isError,
    error: collectionsQuery.error,

    // Update/create collection operations
    updateCollection: updateCollectionMutation.mutate,
    isUpdating: updateCollectionMutation.isPending,
    updateError: updateCollectionMutation.error,

    // Delete collection operations
    deleteCollections: deleteCollectionsMutation.mutate,
    isDeleting: deleteCollectionsMutation.isPending,
    deleteError: deleteCollectionsMutation.error,

    // Manual refetch
    refetch: collectionsQuery.refetch,
  };
};
```

### Phase 3: Data Model

**File**: `src/model/collection-table.tsx` (new file)

Define table columns for collections display:

```typescript
import { createColumnHelper } from "@tanstack/react-table";
import { Tag } from "@chakra-ui/react";
import { Checkbox } from "../components/ui/checkbox";
import { selectionState } from "../components/common/SelectableTable";
import { CollectionMetadata } from "../state/collections";

export const columnHelper = createColumnHelper<CollectionMetadata>();

export const columns = [
  // Selection column
  columnHelper.display({
    id: "select",
    header: ({ table }) => (
      <Checkbox.Root
        checked={selectionState(table)}
        onChange={table.getToggleAllRowsSelectedHandler()}
      >
        <Checkbox.HiddenInput />
        <Checkbox.Control />
      </Checkbox.Root>
    ),
    cell: ({ row }) => (
      <Checkbox.Root
        checked={row.getIsSelected()}
        onChange={row.getToggleSelectedHandler()}
      >
        <Checkbox.HiddenInput />
        <Checkbox.Control />
      </Checkbox.Root>
    ),
  }),

  // Collection ID column
  columnHelper.accessor("collection", {
    header: "Collection ID",
    cell: (info) => info.getValue(),
  }),

  // Name column
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => info.getValue(),
  }),

  // Description column
  columnHelper.accessor("description", {
    header: "Description",
    cell: (info) => info.getValue(),
  }),

  // Tags column
  columnHelper.accessor("tags", {
    header: "Tags",
    cell: (info) =>
      info.getValue()?.map((tag) => (
        <Tag.Root key={tag} mr={2} size="sm">
          <Tag.Label>{tag}</Tag.Label>
        </Tag.Root>
      )),
  }),

  // Created column
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => new Date(info.getValue()).toLocaleString(),
  }),

  // Updated column
  columnHelper.accessor("updated_at", {
    header: "Updated",
    cell: (info) => new Date(info.getValue()).toLocaleString(),
  }),
];
```

### Phase 4: UI Components

#### 4.1 Collections Component

**File**: `src/components/library/Collections.tsx` (new file)

Main collections management component following the Documents.tsx pattern:

```typescript
import React, { useState } from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns } from "../../model/collection-table";
import { useCollections } from "../../state/collections";
import { useNotification } from "../../state/notify";

import CollectionActions from "./CollectionActions";
import CollectionDialog from "./CollectionDialog";
import SelectableTable from "../common/SelectableTable";
import CollectionControls from "./CollectionControls";

const Collections = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCollection, setEditingCollection] = useState(null);

  const notify = useNotification();
  const collectionsState = useCollections();

  const collections = collectionsState.collections || [];

  const table = useReactTable({
    data: collections,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const selected = table.getSelectedRowModel().rows.map((x) => x.original.collection);

  const onCreateNew = () => {
    setEditingCollection(null);
    setDialogOpen(true);
  };

  const onEdit = () => {
    if (selected.length !== 1) {
      notify.info("Please select exactly one collection to edit");
      return;
    }
    const collection = collections.find(c => c.collection === selected[0]);
    setEditingCollection(collection);
    setDialogOpen(true);
  };

  const onDelete = () => {
    collectionsState.deleteCollections({
      collections: selected,
      onSuccess: () => {
        table.setRowSelection({});
      },
    });
  };

  const onSaveCollection = (collection, name, description, tags) => {
    collectionsState.updateCollection({
      collection,
      name,
      description,
      tags,
      onSuccess: () => {
        setDialogOpen(false);
        table.setRowSelection({});
      },
    });
  };

  return (
    <>
      <CollectionActions
        selectedCount={selected.length}
        onEdit={onEdit}
        onDelete={onDelete}
      />

      <CollectionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={onSaveCollection}
        editingCollection={editingCollection}
      />

      <SelectableTable table={table} />

      <CollectionControls onCreate={onCreateNew} />
    </>
  );
};

export default Collections;
```

#### 4.2 Collection Actions Bar

**File**: `src/components/library/CollectionActions.tsx` (new file)

Action buttons for bulk operations on selected collections:

```typescript
import React from "react";
import { HStack, Button, Text } from "@chakra-ui/react";
import { Edit, Trash2 } from "lucide-react";

interface CollectionActionsProps {
  selectedCount: number;
  onEdit: () => void;
  onDelete: () => void;
}

const CollectionActions = ({ selectedCount, onEdit, onDelete }: CollectionActionsProps) => {
  if (selectedCount === 0) return null;

  return (
    <HStack mb={4} p={4} bg="bg.muted" borderRadius="md">
      <Text flex={1}>
        {selectedCount} collection{selectedCount !== 1 ? "s" : ""} selected
      </Text>
      <Button onClick={onEdit} size="sm">
        <Edit /> Edit
      </Button>
      <Button onClick={onDelete} colorPalette="red" size="sm">
        <Trash2 /> Delete
      </Button>
    </HStack>
  );
};

export default CollectionActions;
```

#### 4.3 Collection Dialog

**File**: `src/components/library/CollectionDialog.tsx` (new file)

Dialog for creating/editing collections:

```typescript
import React, { useState, useEffect } from "react";
import { Dialog } from "@chakra-ui/react";
import { Portal } from "@chakra-ui/react";

import TextField from "../common/TextField";
import TextAreaField from "../common/TextAreaField";
import ChipInputField from "../common/ChipInputField";
import ProgressSubmitButton from "../common/ProgressSubmitButton";

interface CollectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (collection: string, name: string, description: string, tags: string[]) => void;
  editingCollection?: any;
}

const CollectionDialog = ({
  open,
  onOpenChange,
  onSave,
  editingCollection,
}: CollectionDialogProps) => {
  const [collection, setCollection] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);

  useEffect(() => {
    if (editingCollection) {
      setCollection(editingCollection.collection);
      setName(editingCollection.name);
      setDescription(editingCollection.description);
      setTags(editingCollection.tags || []);
    } else {
      setCollection("");
      setName("");
      setDescription("");
      setTags([]);
    }
  }, [editingCollection, open]);

  const handleSubmit = () => {
    onSave(collection, name, description, tags);
  };

  const isValid = collection.trim() !== "" && name.trim() !== "";

  return (
    <Dialog.Root open={open} onOpenChange={(e) => onOpenChange(e.open)}>
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>
                {editingCollection ? "Edit Collection" : "Create Collection"}
              </Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <TextField
                label="Collection ID"
                value={collection}
                onValueChange={setCollection}
                disabled={!!editingCollection}
                required
                helperText={editingCollection ? "ID cannot be changed" : "Unique identifier for the collection"}
              />
              <TextField
                label="Name"
                value={name}
                onValueChange={setName}
                required
                helperText="Display name for the collection"
              />
              <TextAreaField
                label="Description"
                value={description}
                onValueChange={setDescription}
                helperText="Brief description of the collection"
              />
              <ChipInputField
                label="Tags"
                value={tags}
                onValueChange={setTags}
                helperText="Press Enter to add tags"
              />
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <ProgressSubmitButton onClick={handleSubmit} disabled={!isValid}>
                {editingCollection ? "Update" : "Create"}
              </ProgressSubmitButton>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};

export default CollectionDialog;
```

#### 4.4 Collection Controls

**File**: `src/components/library/CollectionControls.tsx` (new file)

Control buttons for collection operations:

```typescript
import React from "react";
import { HStack, Button } from "@chakra-ui/react";
import { Plus } from "lucide-react";

interface CollectionControlsProps {
  onCreate: () => void;
}

const CollectionControls = ({ onCreate }: CollectionControlsProps) => {
  return (
    <HStack mt={4} justify="flex-end">
      <Button onClick={onCreate} colorPalette="primary">
        <Plus /> Create Collection
      </Button>
    </HStack>
  );
};

export default CollectionControls;
```

### Phase 5: Update Library Page with Tabs

**File**: `src/pages/LibraryPage.tsx`

Update the library page to use tabs for Documents and Collections:

```typescript
import React from "react";
import { LibraryBig } from "lucide-react";
import { Tabs } from "@chakra-ui/react";

import PageHeader from "../components/common/PageHeader";
import Documents from "../components/library/Documents";
import Collections from "../components/library/Collections";

const LibraryPage = () => {
  return (
    <>
      <PageHeader
        icon={<LibraryBig />}
        title="Library"
        description="Managing documents and collections"
      />
      <Tabs.Root defaultValue="documents">
        <Tabs.List>
          <Tabs.Trigger value="documents">Documents</Tabs.Trigger>
          <Tabs.Trigger value="collections">Collections</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="documents">
          <Documents />
        </Tabs.Content>
        <Tabs.Content value="collections">
          <Collections />
        </Tabs.Content>
      </Tabs.Root>
    </>
  );
};

export default LibraryPage;
```

## Type Definitions

**File**: `src/api/trustgraph/messages.ts`

Add collection-related message types:

```typescript
// Collection management request
export interface CollectionRequest extends RequestMessage {
  operation: "list-collections" | "update-collection" | "delete-collection";
  user: string;
  collection?: string;
  name?: string;
  description?: string;
  tags?: string[];
  tag_filter?: string[];
}

// Collection management response
export interface CollectionResponse {
  collections?: Array<{
    user: string;
    collection: string;
    name: string;
    description: string;
    tags: string[];
    created_at: string;
    updated_at: string;
  }>;
}
```

## Testing Checklist

- [ ] List collections displays all collections for the user
- [ ] Tag filter works when listing collections
- [ ] Create new collection with ID, name, description, and tags
- [ ] Edit existing collection (ID is disabled, other fields editable)
- [ ] Delete single collection
- [ ] Delete multiple collections
- [ ] Selection state persists correctly
- [ ] Loading indicators show during operations
- [ ] Error notifications display for failures
- [ ] Success notifications display for completed operations
- [ ] Tab switching preserves state
- [ ] Collections table sorts correctly
- [ ] Empty state displays when no collections exist
- [ ] Validation prevents creating collections with empty ID or name

## Future Enhancements

1. **Collection Assignment**: Allow assigning documents to collections from the Documents tab
2. **Collection Filtering**: Filter documents by collection
3. **Bulk Collection Operations**: Move multiple documents between collections
4. **Collection Statistics**: Show document count per collection
5. **Collection Search**: Search collections by name, description, or tags
6. **Collection Export**: Export collection metadata

## Migration Notes

- No breaking changes to existing functionality
- Documents tab functionality remains unchanged
- New collections functionality is additive
- Follows established patterns from library.ts and Documents.tsx
- Uses consistent Chakra v3 components and patterns
