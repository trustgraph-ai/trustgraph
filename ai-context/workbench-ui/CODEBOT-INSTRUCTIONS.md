# UI Toolkits and Framework Notes

## Change Management and API Stability

**CRITICAL**: Components in `src/components/common/` are foundational to the entire application. DO NOT modify these components without explicit approval from the application design authority. Changes to common components have extensive downstream impact and can break multiple features across the application.

### Change Impact Assessment
Before modifying any common component:
1. **Document all consumers** - Search the entire codebase for usage
2. **Assess breaking changes** - Any interface changes affect all consumers
3. **Test extensively** - Changes can break seemingly unrelated features
4. **Get approval** - Design authority must approve all common component changes

### Lessons from SelectField Issues
Recent issues with SelectField demonstrate why common component changes are dangerous:
- **September 2025**: Changes to SelectField to support one feature (Ontology editor) broke document submission
- **Root cause**: Interface contract violations between array/string APIs
- **Impact**: Multiple components across different domains affected
- **Resolution required**: Systematic updates to 15+ components across the application

**Key takeaway**: Changing common components to fix one feature often breaks others. Always prefer adapter patterns or feature-specific solutions over modifying shared infrastructure.

## Directory Structure and Organization Rationale

### Core Principles

We follow a **domain-driven, flat structure** that avoids unnecessary nesting and keeps related code together:

1. **Avoid generic aggregation directories** - No `src/hooks/`, `src/constants/`, `src/utils/` that become dumping grounds
2. **Colocate by domain** - Keep related code together in feature-specific directories  
3. **Flat when possible** - Single files don't need their own subdirectories
4. **Clear separation of concerns** - Different types of logic go in appropriate places

### Directory Layout

```
src/
├── components/          # UI components organized by domain
│   ├── schemas/         # All schema-related UI components
│   │   ├── EditSchemaDialog.tsx      # Main orchestrator component
│   │   ├── SchemaFieldEditor.tsx     # Individual field editing
│   │   ├── SchemaFieldsList.tsx      # Fields list management
│   │   ├── SchemaTableStates.tsx     # Reusable table states
│   │   ├── useSchemaForm.ts          # Form state logic (colocated)
│   │   └── ...
│   ├── taxonomies/      # All taxonomy-related UI components
│   └── common/          # Truly shared/generic components
├── model/               # Data models, types, and domain constants
│   ├── schemas-table.tsx            # Schema data models
│   ├── schemaTypes.ts               # Schema type constants
│   └── ...
├── state/               # Application state management
│   ├── schemas.ts                   # Schema API calls and state
│   └── ...
├── api/                 # Direct API communication
└── utils/               # Pure utility functions (no React/UI)
```

### Rationale by Directory

**`src/components/[domain]/`**
- Contains ALL UI components for a specific domain (schemas, taxonomies, etc.)
- Includes domain-specific hooks like `useSchemaForm.ts` 
- **Why**: Keeps everything needed to work on a feature in one place
- **Avoid**: Generic `src/hooks/` that becomes a dumping ground

**`src/model/`**
- Data types, interfaces, constants, and domain models
- **Why**: Centralized data definitions that can be imported anywhere
- **Example**: `schemaTypes.ts` contains `SCHEMA_TYPE_OPTIONS` and `DEFAULT_FIELD`

**`src/state/`**
- High-level application state management
- React Query hooks for API calls and caching
- **Why**: Separates data fetching/caching from UI logic

**`src/api/`**
- Direct API communication layer
- WebSocket management
- **Why**: Abstracts network concerns from business logic

### Benefits of This Approach

1. **Discoverability**: All schema-related code is in `src/components/schemas/`
2. **Maintainability**: Changes to schema features are localized
3. **Reusability**: Shared types in `src/model/` can be imported anywhere
4. **Scalability**: New domains get their own component directories
5. **Avoids Anti-patterns**: No generic directories that accumulate unrelated files

### Example: Schema Feature Organization

When working on schema-related features, everything you need is in one place:
- UI components: `src/components/schemas/`
- Data models: `src/model/schemas-table.tsx`, `src/model/schemaTypes.ts` 
- API/state: `src/state/schemas.ts`

This eliminates the need to hunt through multiple generic directories to understand or modify a feature.

## Icon Library

**CRITICAL**: Always use `lucide-react` for icons throughout the application. Do NOT use `react-icons` or any other icon library.

```tsx
// ✅ Correct - Use lucide-react
import { Plus, Save, Trash2, Edit, Settings } from "lucide-react";

// ❌ Wrong - Don't use react-icons
import { FiPlus, FiSave } from "react-icons/fi";
```

**Common icon mappings from react-icons to lucide-react:**
- `FiPlus` → `Plus`
- `FiX` → `X`
- `FiSave` → `Save`
- `FiTrash2` → `Trash2`
- `FiEdit/FiEdit3` → `Edit`
- `FiSettings` → `Settings`
- `FiDownload` → `Download`
- `FiUpload` → `Upload`
- `FiMove` → `Move`
- `FiMoreVertical` → `MoreVertical`
- `FiList` → `List`

## Chakra UI Version

**CRITICAL**: This project uses **Chakra UI v3**, NOT v2. Always check component APIs against v3 documentation.

## Key Chakra v3 Migration Points

### Modal → Dialog
```tsx
// ❌ Chakra v2
<Modal isOpen={open} onClose={onClose}>
  <ModalOverlay />
  <ModalContent>
    <ModalHeader>Title</ModalHeader>
    <ModalBody>Content</ModalBody>
  </ModalContent>
</Modal>

// ✅ Chakra v3
<Dialog.Root open={open} onOpenChange={(x) => onOpenChange(x.open)}>
  <Portal>
    <Dialog.Backdrop />
    <Dialog.Positioner>
      <Dialog.Content>
        <Dialog.Header>
          <Dialog.Title>Title</Dialog.Title>
        </Dialog.Header>
        <Dialog.Body>Content</Dialog.Body>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog.Root>
```

### Toast System
```tsx
// ❌ Chakra v2
const toast = useToast();
toast({ title: "Success", status: "success" });

// ✅ Chakra v3
import { toaster } from "../ui/toaster";
toaster.create({ title: "Success", status: "success" });
```

### Form Components
```tsx
// ❌ Chakra v2
<FormControl>
  <FormLabel>Label</FormLabel>
  <Input />
</FormControl>

// ✅ Chakra v3
<Field.Root>
  <Field.Label>Label</Field.Label>
  <Input />
</Field.Root>
```

### Tabs Structure
```tsx
// ❌ Chakra v2
<Tabs>
  <TabList>
    <Tab>Tab 1</Tab>
  </TabList>
  <TabPanels>
    <TabPanel>Content</TabPanel>
  </TabPanels>
</Tabs>

// ✅ Chakra v3
<Tabs.Root>
  <Tabs.List>
    <Tabs.Trigger value="tab1">Tab 1</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="tab1">Content</Tabs.Content>
</Tabs.Root>
```

### Menu Components
```tsx
// ❌ Chakra v2
<Menu>
  <MenuButton>Button</MenuButton>
  <MenuList>
    <MenuItem>Item</MenuItem>
  </MenuList>
</Menu>

// ✅ Chakra v3
<Menu.Root>
  <Menu.Trigger>Button</Menu.Trigger>
  <Menu.Content>
    <Menu.Item>Item</Menu.Item>
  </Menu.Content>
</Menu.Root>
```

### Props Changes
```tsx
// ❌ Chakra v2 props
colorScheme="blue"
isDisabled={true}

// ✅ Chakra v3 props
colorPalette="blue"
disabled={true}
```

### Layout Components
```tsx
// ❌ Chakra v2
<Divider />

// ✅ Chakra v3
<Separator />
```

### Spacing Props
```tsx
// ❌ Old pattern
<VStack spacing={4}>
<HStack spacing={2}>

// ✅ Chakra v3
<VStack gap={4}>
<HStack gap={2}>
```

### Button Icons
```tsx
// ❌ Old pattern
<Button leftIcon={<Plus />}>Add</Button>
<IconButton icon={<Upload />} aria-label="Upload" />

// ✅ Chakra v3
<Button><Plus /> Add</Button>
<IconButton aria-label="Upload"><Upload /></IconButton>
```

### Input Groups (Simplified)
```tsx
// ❌ Chakra v2
<InputGroup>
  <InputLeftElement>🔍</InputLeftElement>
  <Input placeholder="Search..." />
</InputGroup>

// ✅ Chakra v3 (simplified approach)
<Input placeholder="🔍 Search..." />
```

### Avatar Structure
```tsx
// ❌ Chakra v2
<Avatar name="John Doe" />

// ✅ Chakra v3
<Avatar.Root>
  <Avatar.Fallback name="John Doe" />
</Avatar.Root>
```

### Alert Component
```tsx
// ❌ Chakra v2
<Alert status="error">
  <AlertIcon />
  <Text>Error message</Text>
</Alert>

// ✅ Chakra v3
<Alert.Root status="error">
  <Alert.Indicator />
  <Alert.Content>
    <Alert.Description>Error message</Alert.Description>
  </Alert.Content>
</Alert.Root>
```

**Alert Status Options:**
- `status="error"` - Red error alerts
- `status="warning"` - Orange warning alerts  
- `status="success"` - Green success alerts
- `status="info"` - Blue info alerts

**Alert with Title:**
```tsx
<Alert.Root status="warning">
  <Alert.Indicator />
  <Alert.Content>
    <Alert.Title>Warning Title</Alert.Title>
    <Alert.Description>Warning description text</Alert.Description>
  </Alert.Content>
</Alert.Root>
```

### Progress Component
```tsx
// ❌ Chakra v2
<Progress value={60} colorScheme="blue" />

// ✅ Chakra v3
<Progress.Root value={60}>
  <Progress.Track>
    <Progress.Range />
  </Progress.Track>
  <Progress.Label />
  <Progress.ValueText />
</Progress.Root>
```

**Progress with custom styling:**
```tsx
<Progress.Root value={75} colorPalette="green" size="sm">
  <Progress.Track>
    <Progress.Range />
  </Progress.Track>
</Progress.Root>
```

## Layout Components Still Work

**Important**: VStack, HStack, Box, Grid, GridItem, Text, Button, Input, etc. still work the same way in v3. The confusion around VStack/HStack causing "invalid component type" errors is usually due to **circular import dependencies**, not Chakra version issues.

## Common Debugging Steps

1. **Check imports**: Ensure all Chakra components are imported from `@chakra-ui/react`
2. **Verify component structure**: Use the v3 nested component patterns (Component.Root, Component.Trigger, etc.)
3. **Check props**: Use `colorPalette` instead of `colorScheme`, `disabled` instead of `isDisabled`
4. **Circular imports**: If getting "invalid component type" errors with basic components like VStack, check for circular import dependencies

## Migration Verification Checklist

When migrating components to Chakra v3:
- [ ] Replace `<Alert>` with `<Alert.Root>`
- [ ] Replace `<AlertIcon />` with `<Alert.Indicator />`
- [ ] Wrap text in `<Alert.Content><Alert.Description>...</Alert.Description></Alert.Content>`
- [ ] Replace `<Progress>` with `<Progress.Root><Progress.Track><Progress.Range /></Progress.Track></Progress.Root>`
- [ ] Use `<Card.Root><Card.Header /><Card.Body /></Card.Root>` structure for cards
- [ ] Replace `<Modal>` with `<Dialog.Root>` 
- [ ] Replace `spacing` props with `gap` props
- [ ] Replace `colorScheme` with `colorPalette`
- [ ] Replace `isDisabled` with `disabled`
- [ ] Test build after changes
- [ ] Verify visual styling is preserved
- [ ] Be systematic: search for old patterns, document the fix, then apply consistently

## Project-Specific Patterns

### Notifications
**CRITICAL: NEVER use the toaster directly.** The `toaster` from `@chakra-ui/react` or `../ui/toaster` must NOT be imported or used directly. Always use the `useNotification` hook:

```tsx
// ❌ NEVER do this - toaster is forbidden
import { toaster } from "../ui/toaster";
import { toaster } from "@chakra-ui/react";
toaster.create({ title: "Success", status: "success" });

// ✅ ALWAYS do this instead
import { useNotification } from "../../state/notify";

const notify = useNotification();
notify.success("Operation completed successfully");
notify.error("Something went wrong");
notify.info("FYI: This is informational");
```

**Why toaster is forbidden:**
- Direct toaster usage bypasses the project's notification standards
- The `useNotification` hook provides consistent error prefixing and styling
- It maintains a unified notification interface across the application
- Direct toaster usage can cause inconsistent user experience

### Common Components
**ALWAYS** prefer using pre-built components from `src/components/common/` instead of raw Chakra components. These components handle Chakra v3 APIs correctly and reduce boilerplate:

```tsx
// ❌ Don't use raw Chakra components
<Field.Root required>
  <Field.Label>Name</Field.Label>
  <Input value={value} onChange={(e) => setValue(e.target.value)} />
</Field.Root>

// ✅ Use common components instead
<TextField 
  label="Name" 
  value={value} 
  onValueChange={setValue} 
  required 
/>
```

**Available Common Components:**
- `TextField` - Text input with label and validation
- `TextAreaField` - Multi-line text input  
- `SelectField` - Dropdown select with rich options
- `BasicTable` - Pre-configured Tanstack Table
- `Card` - Consistent card layout with title/description
- `ProgressSubmitButton` - Submit button with loading state
- `PageHeader` - Standard page header layout
- `StatusBadge` - Consistent status indicators
- `CenterSpinner` - Loading spinner
- `ChipInputField` - Tag/chip input field
- `NumberField` - Numeric input with validation
- `Slider` - Range slider component

#### SelectField Usage
**CRITICAL**: SelectField expects array values for selection and MUST include description fields for dropdown display:

```tsx
// ✅ Correct usage
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";

<SelectField
  label="Select Option"
  items={[
    {
      value: 'option1',
      label: 'Option 1',
      description: (
        <SelectOptionText>
          Option 1
        </SelectOptionText>
      )
    },
    {
      value: 'option2',
      label: 'Option 2',
      description: (
        <SelectOptionText>
          Option 2
        </SelectOptionText>
      )
    }
  ]}
  value={selectedValues}         // array - current selection (empty array for no selection)
  onValueChange={(values) => setSelectedValues(values)}  // receives array
/>
```

**Important Notes:**
- Pass an empty array `[]` for no selection, not an empty string
- The `value` prop should always be an array
- The `onValueChange` callback receives an array
- For single selection, extract the first element: `values.length > 0 ? values[0] : null`
- **REQUIRED**: The `description` field MUST be provided using `SelectOptionText` or `SelectOption` components
- **Missing descriptions will result in empty dropdown options**

**Example with single selection extraction:**
```tsx
const [selectedValues, setSelectedValues] = useState([]);

// Get the selected value (for single select behavior)
const selectedValue = selectedValues.length > 0 ? selectedValues[0] : null;

// Handle submission
const handleSubmit = () => {
  if (selectedValue) {
    onSubmit(selectedValue);
  }
};
```

**Common Mistake - Missing Descriptions:**
```tsx
// ❌ WRONG - Will show empty dropdown options
items={[
  {value: 'option1', label: 'Option 1'},  // Missing description!
  {value: 'option2', label: 'Option 2'}   // Missing description!
]}

// ✅ CORRECT - Includes required descriptions
items={[
  {
    value: 'option1',
    label: 'Option 1',
    description: <SelectOptionText>Option 1</SelectOptionText>
  },
  {
    value: 'option2',
    label: 'Option 2',
    description: <SelectOptionText>Option 2</SelectOptionText>
  }
]}
```

### Theming and Colors
**ALWAYS** use semantic color tokens instead of direct color palettes. The theme provides semantic tokens that automatically handle light/dark mode:

```tsx
// ❌ Don't use direct color palettes
colorPalette="blue"
bg="gray.100"
color="deepPlum.700"

// ✅ Use semantic tokens instead
colorPalette="primary"
bg="bg.muted" 
color="primary.fg"
```

**Available Semantic Color Palettes:**
- `primary` - Main brand color (airForceBlue)
- `accent` - Secondary brand color (deepPlum)
- `observing` - For observation callouts (warmNeutral)
- `thinking` - For thinking callouts (deepPlum variants)
- `insightful` - For answer callouts (neutralGreen)

**Semantic Token Structure:**
Each palette has these variants:
- `.solid` - Strong, high contrast (buttons, badges)
- `.contrast` - Text on solid backgrounds
- `.fg` - Foreground text color
- `.muted` - Subtle backgrounds
- `.subtle` - Light backgrounds
- `.emphasized` - Medium emphasis backgrounds
- `.focusRing` - Focus indicators

**Background/Text Tokens:**
- `background` - Main page background
- `text` - Main text color
- `bg.muted` - Subtle background areas
- `fg.muted` - Muted text

### Page Structure
**ALWAYS** use consistent page structure with PageHeader:

```tsx
// ❌ Don't embed headings in components
export const MyComponent = () => {
  return (
    <VStack>
      <Heading>My Page Title</Heading>
      <Content />
    </VStack>
  );
};

// ✅ Use PageHeader at the page level
// In pages/MyPage.tsx:
import PageHeader from "../components/common/PageHeader";
import MyComponent from "../components/MyComponent";

const MyPage = () => {
  return (
    <>
      <PageHeader
        icon={<IconName />}
        title="Page Title"
        description="Brief description of what this page does"
      />
      <MyComponent />
    </>
  );
};

// In components/MyComponent.tsx (no heading):
export const MyComponent = () => {
  return (
    <VStack>
      <Content />
    </VStack>
  );
};
```

**Page Structure Rules:**
1. Page components go in `src/pages/` directory
2. Always use `PageHeader` component for consistent headers
3. Page title and description should be at page level, not component level
4. Components should not contain their own page-level headings
5. Use appropriate lucide-react icons for the page icon

### Progress Management and Loading States

**CRITICAL**: Always use the `useActivity` hook for loading states instead of managing spinners manually. This provides consistent loading indicators across the application.

```tsx
// ❌ Don't manage loading states manually
const [isLoading, setIsLoading] = useState(false);
const handleSubmit = async () => {
  setIsLoading(true);
  try {
    await submitData();
  } finally {
    setIsLoading(false);
  }
};

// ✅ Use useActivity hook instead
import { useActivity } from "../../state/activity";

const submitMutation = useMutation({
  mutationFn: submitData,
});

// Automatically shows/hides loading indicator
useActivity(submitMutation.isPending, "Submitting data");
```

**Progress System Components:**

1. **`useProgressStateStore`** - Zustand store that manages global activity tracking
   - `activity: Set<string>` - Active operations being tracked
   - `error: string` - Current error state
   - `addActivity(name)` - Add a loading operation
   - `removeActivity(name)` - Remove a loading operation
   - `setError(message)` - Set/clear error state

2. **`useActivity(isActive, description)`** - React hook for automatic activity management
   - `isActive: boolean` - Whether the activity is currently running
   - `description: string` - User-friendly description of the activity
   - Automatically adds/removes activities based on the boolean condition
   - Handles cleanup when component unmounts or dependencies change

**Usage Patterns:**

```tsx
// ✅ With React Query mutations
const updateMutation = useMutation({ mutationFn: updateData });
useActivity(updateMutation.isPending, "Updating settings");

// ✅ With React Query queries  
const dataQuery = useQuery({ queryKey: ['data'], queryFn: fetchData });
useActivity(dataQuery.isLoading, "Loading data");

// ✅ Multiple activities for complex operations
useActivity(settingsQuery.isLoading, "Loading settings");
useActivity(updateSettingsMutation.isPending, "Saving settings");
useActivity(resetSettingsMutation.isPending, "Resetting settings");

// ✅ Manual activity management (when useActivity isn't sufficient)
const addActivity = useProgressStateStore((state) => state.addActivity);
const removeActivity = useProgressStateStore((state) => state.removeActivity);

const handleComplexOperation = async () => {
  const activityId = "Processing complex operation";
  addActivity(activityId);
  try {
    await step1();
    await step2();
    await step3();
  } finally {
    removeActivity(activityId);
  }
};
```

**Benefits of the Progress System:**
- **Consistent UX**: All loading states are managed centrally
- **Automatic cleanup**: Activities are removed when operations complete or components unmount
- **Deduplication**: Multiple identical activity names are automatically deduplicated
- **Global visibility**: The UI can show a global loading indicator when any activities are active
- **Error handling**: Centralized error state management
- **Zero boilerplate**: Just call `useActivity()` with a boolean and description

**Integration with TanStack Query:**
The progress system integrates perfectly with TanStack Query's loading states:

```tsx
// All these patterns work seamlessly together
export const useSettings = () => {
  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  const updateMutation = useMutation({
    mutationFn: updateSettings,
  });

  // Automatic activity tracking
  useActivity(settingsQuery.isLoading, "Loading settings");
  useActivity(updateMutation.isPending, "Saving settings");

  return {
    settings: settingsQuery.data,
    isLoading: settingsQuery.isLoading,
    updateSettings: updateMutation.mutate,
    isSaving: updateMutation.isPending,
  };
};
```

### Table Components

**CRITICAL**: Always use TanStack Table with our standardized table components instead of manually implementing Chakra Table structures.

**Standard Table Pattern:**

1. **Create Model File** (`src/model/[feature]-table.tsx`):
```tsx
import { createColumnHelper } from "@tanstack/react-table";

export type MyData = {
  id: string;
  name: string;
  description: string;
};

export const columnHelper = createColumnHelper<MyData>();

export const columns = [
  columnHelper.accessor("id", {
    header: "ID",
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor("name", {
    header: "Name", 
    cell: (info) => info.getValue(),
  }),
  columnHelper.accessor("description", {
    header: "Description",
    cell: (info) => info.getValue(),
  }),
];
```

2. **Use Common Table Components**:
```tsx
// ❌ Don't manually implement table structure
<Table.Root>
  <Table.Header>
    <Table.Row>
      <Table.ColumnHeader>Name</Table.ColumnHeader>
    </Table.Row>
  </Table.Header>
  <Table.Body>
    {data.map(row => (
      <Table.Row key={row.id}>
        <Table.Cell>{row.name}</Table.Cell>
      </Table.Row>
    ))}
  </Table.Body>
</Table.Root>

// ✅ Use standardized components and models
import { BasicTable } from "../common/BasicTable";
import { columns, MyData } from "../../model/my-data-table";

const table = useReactTable({
  data: myData as MyData[],
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});

return <BasicTable table={table} />;
```

**Available Table Components:**
- `BasicTable` - Standard table display
- `ClickableTable` - Table with row click handlers  
- `SelectableTable` - Table with row selection checkboxes

**Standard Column Patterns:**
```tsx
// Selection column (for SelectableTable)
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
});

// Data columns with custom formatting
columnHelper.accessor("timestamp", {
  header: "Created",
  cell: (info) => timeString(info.getValue()),
});

// Tags/badges column
columnHelper.accessor("tags", {
  header: "Tags",
  cell: (info) => 
    info.getValue()?.map((tag) => (
      <Tag.Root key={tag} mr={2}>
        <Tag.Label>{tag}</Tag.Label>
      </Tag.Root>
    )),
});
```

**Benefits of Standardized Tables:**
- ✅ Consistent behavior and styling across the application
- ✅ Built-in sorting, selection, and interaction patterns
- ✅ Type safety with column definitions
- ✅ Easier testing and maintenance
- ✅ Better performance with TanStack optimizations
- ✅ Automatic loading state integration with progress system

### Other Patterns
- Use Tanstack Query for state management with existing socket-based config API
- Follow kebab-case naming conventions for IDs and URLs
- Always prefer TanStack Table models over manual Chakra Table implementation