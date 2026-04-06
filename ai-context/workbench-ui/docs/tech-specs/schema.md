# Schema Support for TrustGraph UI

## Overview

This document specifies the UI work needed to support structured data schemas in TrustGraph. Schemas enable the system to work with structured data (rows in tables/objects) alongside unstructured data processing.

## Schema Representation

Based on the STRUCTURED_DATA.md specification, schemas are stored in TrustGraph's configuration system with:

- **Type**: `schema` (fixed value for all structured data schemas)
- **Key**: Unique schema identifier (e.g., `customer_records`, `transaction_log`)
- **Value**: JSON schema definition

### Schema Structure Example:
```json
{
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

### Field Types Supported:
- `string`
- `integer`
- `float`
- `boolean`
- `timestamp`
- `enum` (with predefined values)

### Field Properties:
- `name`: Field identifier
- `type`: Data type
- `primary_key`: Boolean flag for primary key fields
- `required`: Boolean flag for required fields
- `enum`: Array of allowed values for enum types

## Requirements

Based on the Prompts page implementation pattern, the Schema UI should provide:

1. **Schema Management Page**
   - List all schemas in a table view
   - Create new schemas via modal dialog
   - Edit existing schemas
   - Delete schemas with confirmation
   - View schema details in a readable format

2. **UI Components Needed**
   - Main schemas page with table listing
   - Create/Edit schema dialog with form validation
   - Schema field editor (add/remove/edit fields)
   - Field type selector with appropriate options
   - Primary key and index configuration
   - Schema preview/viewer component

3. **State Management**
   - Use React Query for data fetching and mutations
   - Implement CRUD operations following the prompts pattern
   - Handle loading states and error notifications
   - Cache management and invalidation

## Implementation Details

### API Integration Pattern (from Prompts example)

1. **Configuration Keys**
   - Individual schemas: `{ type: "schema", key: "{schema_id}" }`
   - List all schemas by querying all keys with `type: "schema"`

2. **State Management Hook** (`useSchemas`)
   - `getValues("schema")` to list all schemas (returns array of {key, value} objects)
   - `putConfig()` to create/update schemas
   - `deleteConfig()` to remove schemas
   - No need for separate index management

3. **Component Structure**
   - `SchemasPage.tsx` - Main page component
   - `components/schemas/Schemas.tsx` - Container component
   - `components/schemas/SchemasTable.tsx` - List view
   - `components/schemas/SchemaControls.tsx` - Action buttons
   - `components/schemas/EditSchemaDialog.tsx` - Create/Edit form
   - `components/schemas/SchemaViewer.tsx` - Read-only schema display
   - `state/schemas.ts` - React Query hooks
   - `model/schemas-table.tsx` - TypeScript definitions

4. **Field Editor Requirements**
   - Dynamic field list with add/remove capabilities
   - Field property editors:
     - Name (text input)
     - Type (dropdown: string, integer, float, boolean, timestamp, enum)
     - Primary key (checkbox)
     - Required (checkbox)
     - Enum values (list editor, shown only for enum type)
   - Index configuration (multi-select from available fields)

5. **Validation Rules**
   - Schema name: Required, unique
   - At least one field required
   - At least one primary key field
   - Field names must be unique within schema
   - Enum type requires at least one enum value

## Tasks

1. Create schema state management hook (`useSchemas`)
2. Implement SchemasPage and routing
3. Build SchemasTable component with sorting/filtering
4. Create EditSchemaDialog with field editor
5. Add schema validation logic
6. Implement schema viewer component
7. Add TypeScript models and table configurations
8. Integration testing with backend API

## Notes

- Follow the existing Prompts page pattern for consistency
- Use Chakra UI components matching current design system
- Implement proper error handling and user feedback
- Consider adding import/export functionality for schemas
- May need to handle schema versioning in the future
- Implementation is simpler than prompts since we use `getValues("schema")` instead of maintaining a separate index
- Reference the agent-tools implementation pattern which also uses `getValues()` directly
