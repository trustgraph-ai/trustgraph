# Settings Page for TrustGraph UI

## Overview

This document specifies the implementation of a Settings page for the TrustGraph UI application. The Settings page will provide a centralized interface for configuring application preferences, user settings, and system-wide configurations.

## Requirements

The Settings page should provide:

1. **Settings Management Interface**
   - Centralized location for all user and system settings
   - Organized into logical sections/categories using visual grouping
   - Real-time save functionality with visual feedback
   - Reset to defaults capability
   - Import/export settings configuration

2. **Settings Categories**
   - **Authentication**: API key configuration for TrustGraph socket authentication
   - **GraphRAG Configuration**: Entity limits, triple limits, and graph traversal settings
   - **Feature Switches**: Toggle switches for advanced/experimental functionality

3. **Specific Settings**

   **Authentication Section**:
   - **API Key**: Text input field (password type for security)
     - Default: empty string (no authentication)
     - When set: used for TrustGraph socket authentication
     - Should mask the key value when displayed

   **GraphRAG Settings Section**:
   - **Entity Limit**: Number input (default: 50)
   - **Triple Limit**: Number input (default: 30) 
   - **Max Subgraph Size**: Number input (default: 1000)
   - **Path Length**: Number input (default: 2)

   **Feature Switches Section**:
   - **Taxonomy Editor**: Boolean toggle (default: false)
   - **Submissions**: Boolean toggle (default: false)

3. **Navigation Integration**
   - Add settings route at the end of the sidebar navigation
   - Use Settings icon from lucide-react
   - Standard page structure with PageHeader

## Implementation Details

### Routing Integration

**Sidebar Addition** (src/components/Sidebar.tsx):
- Add import: `Settings` from lucide-react
- Add NavItem at end of VStack: `<NavItem to="/settings" icon={Settings} label="Settings" />`

**Route Configuration**:
- Add route in main router configuration
- Path: `/settings`
- Component: `SettingsPage`

### Component Structure

Following the established patterns from UI-TOOLKITS.md:

```
src/
├── pages/
│   └── SettingsPage.tsx           # Main page with PageHeader
├── components/
│   └── settings/
│       ├── Settings.tsx           # Main container component
│       ├── SettingsForm.tsx       # Settings form management  
│       ├── AuthenticationSection.tsx    # API key configuration
│       ├── GraphRagSection.tsx          # GraphRAG settings
│       ├── FeatureSwitchesSection.tsx   # Feature toggles
│       └── SettingsControls.tsx         # Action buttons (save, reset, import/export)
├── state/
│   └── settings.ts               # Settings state management with localStorage
└── model/
    └── settings-types.ts         # TypeScript definitions for settings
```

### UI Framework Considerations

Based on UI-TOOLKITS.md guidelines:

**Chakra UI v3 Components**:
- Use `Field.Root` and `Field.Label` for form inputs
- Use common components: `TextField`, `SelectField`, `Card`
- Use `Alert.Root` for validation feedback
- Follow semantic color tokens (`primary`, `accent`, etc.)

**Icons**:
- Use `Settings` from lucide-react (already established pattern)
- Other icons as needed: `Save`, `RotateCcw`, `Download`, `Upload`

**Notifications**:
- Use `useNotification` hook (NOT direct toaster)
- Provide success/error feedback for save operations

### State Management Pattern

Following the established React Query pattern:

**Settings State Hook** (`useSettings`):
- `getSettings()` to retrieve current settings from localStorage
- `updateSetting()` to modify individual settings and persist to localStorage
- `resetSettings()` to restore defaults and clear localStorage
- `exportSettings()` and `importSettings()` for configuration management
- Handle localStorage serialization/deserialization
- Provide default values when localStorage is empty

**Data Storage**:
- **Browser localStorage**: All settings stored in browser's localStorage
- Settings persist across browser sessions
- Settings are client-side only (no server synchronization)
- Use structured key naming for organized storage

### Testing Strategy

Based on TEST_STRATEGY.md:

**Component Tests**:
- SettingsForm validation and state management
- Settings section rendering and interaction
- Import/export functionality
- Reset to defaults behavior

**Integration Tests**:
- Settings persistence across sessions  
- Settings application to other components
- Route navigation and sidebar integration

**Test Data**:
```tsx
const mockSettings = {
  authentication: {
    apiKey: ''  // Empty by default
  },
  graphrag: {
    entityLimit: 50,
    tripleLimit: 30,
    maxSubgraphSize: 1000,
    pathLength: 2
  },
  featureSwitches: {
    taxonomyEditor: false,
    submissions: false
  }
};
```

## Tasks

1. **Foundation Setup**
   - Create SettingsPage component with PageHeader
   - Add routing integration and sidebar navigation
   - Set up basic component structure

2. **State Management**
   - Implement settings state hook with localStorage integration
   - Define settings data model with typed interfaces
   - Create default settings configuration
   - Handle localStorage persistence and retrieval

3. **UI Implementation**
   - Build AuthenticationSection with masked API key input
   - Create GraphRagSection with NumberField components for limits
   - Implement FeatureSwitchesSection with toggle switches
   - Add visual grouping with Card components for each section
   - Implement form validation and submission  
   - Add import/export functionality
   - Create reset to defaults mechanism

4. **Integration & Testing**
   - Add route configuration
   - Implement component tests
   - Add integration tests for settings persistence
   - Verify UI consistency with design system

## Data Model

### Settings Structure
```tsx
interface Settings {
  authentication: {
    apiKey: string;  // Default: ''
  };
  graphrag: {
    entityLimit: number;        // Default: 50
    tripleLimit: number;        // Default: 30
    maxSubgraphSize: number;    // Default: 1000
    pathLength: number;         // Default: 2
  };
  featureSwitches: {
    taxonomyEditor: boolean;    // Default: false
    submissions: boolean;       // Default: false
  };
}
```

### LocalStorage Keys
- Main settings: `trustgraph-settings`
- Backup/versioning: Consider `trustgraph-settings-backup` for import/export

## Integration Points

### API Key Integration
- Settings API key should be used by TrustGraph socket authentication
- When API key is empty, no authentication is used
- When API key has value, it's passed to socket connection for authentication

### Feature Switches Integration
- **Taxonomy Editor**: Controls visibility of taxonomy-related routes/components
- **Submissions**: Controls visibility of submissions/processing routes/components
- Features should be conditionally rendered based on these settings

## Notes

- **Security**: API key should be masked in UI but stored as plaintext in localStorage
- **Visual Grouping**: Use Card components to separate the three main sections
- **Real-time Updates**: Settings changes should be immediately persisted to localStorage
- **Validation**: Number inputs should have min/max constraints and validation
- **Accessibility**: Ensure full keyboard navigation and screen reader support
- **Responsive**: Settings should work well on mobile and desktop layouts

## Future Considerations

- User-specific vs. system-wide settings
- Settings synchronization across devices
- Advanced settings with warnings/confirmations
- Settings search/filter capability
- Bulk settings operations
- Settings versioning and migration