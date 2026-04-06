# Gateway Authentication for TrustGraph UI

## Overview

This document specifies the implementation of gateway authentication for the TrustGraph UI application. The gateway authentication system will provide secure communication between the UI and the TrustGraph backend services through an authentication token mechanism.

## Requirements

The gateway authentication system should provide:

1. **Authentication Modes**
   - **Unauthenticated Mode**: When no API key is entered (empty string), the system operates without authentication
   - **Authenticated Mode**: When an API key is specified in settings, all communications include the authentication token

2. **Token Management**
   - Secure storage and retrieval of authentication credentials via settings system
   - Authentication is determined by presence/absence of API key
   - Token persists across sessions (stored in localStorage via settings)
   - Token should be masked in UI displays

3. **Integration Points**
   - **WebSocket Connections**: Append `?token=<apiToken>` to WebSocket connection URL
   - **REST API Calls**: Include token as Bearer token in Authorization header
   - Settings page for token configuration
   - Error handling for 401/403 responses

## Implementation Details

### Settings Integration

**Authentication Settings** (already exists in settings-types.ts):
```typescript
authentication: {
  apiKey: string;  // Gateway authentication token/secret
}
```

### Socket Layer Integration

**WebSocket Authentication**:
```typescript
// In createTrustGraphSocket or SocketProvider
const wsUrl = settings.authentication.apiKey 
  ? `/api/socket?token=${settings.authentication.apiKey}`
  : `/api/socket`;
```

**REST API Authentication**:
```typescript
// For any REST endpoints (if used)
const headers = settings.authentication.apiKey
  ? { 'Authorization': `Bearer ${settings.authentication.apiKey}` }
  : {};
```

**Current State**:
- `useSocket()` hook now has access to settings via `useSettings()`
- Socket context created once at app initialization
- Settings changes require socket reconnection for auth updates

**Required Changes**:
1. Modify `createTrustGraphSocket` to accept optional token parameter
2. Update socket initialization to append token to WebSocket URL when present
3. Add Bearer token to any REST API calls (if applicable)
4. Handle authentication errors (401/403) gracefully
5. Consider socket reconnection when authentication settings change

### User Interface

**Settings Page**:
- Password input field for gateway secret
- Show/hide toggle for secret visibility
- Clear button to remove authentication
- Save confirmation with success/error feedback

**Authentication Status**:
- Optional status indicator in header/sidebar
- Error notifications for auth failures
- Redirect to settings on 401/403 errors

## Socket Initialization Timing

### Critical Requirements
1. **The socket MUST NOT be created until settings have been loaded from localStorage/backend**. Creating the socket too early will result in incorrect authentication state.
2. **The socket MUST reconnect when the API key changes**. This ensures authentication state stays synchronized with user settings.

### Initialization Scenarios

1. **Scenario 1: Token Already Configured**
   - User has previously saved an API key in settings
   - Settings load from localStorage → contains `apiKey: "token123"`
   - Socket creation MUST wait for settings load
   - Socket connects with `?token=token123` appended to URL
   - **Risk if socket created early**: Connects without auth, requires reconnection

2. **Scenario 2: Explicitly Unauthenticated**
   - User has explicitly chosen no authentication (saved empty token)
   - Settings load from localStorage → contains `apiKey: ""`
   - Socket creation MUST wait for settings load
   - Socket connects WITHOUT token parameter
   - **Risk if socket created early**: Might use stale token from previous session

3. **Scenario 3: First-Time User / No Settings**
   - No settings have been saved yet
   - Settings system returns defaults (empty apiKey)
   - **Options**:
     a. Wait for settings to initialize with defaults, then create socket (safest)
     b. Create socket immediately without auth (assumes unauthenticated default)
     c. Show setup wizard requiring auth decision before socket creation
   - **Recommendation**: Option (a) - always wait for settings initialization

### Socket Reconnection Requirements

When the API key changes (user updates settings), the socket must:

1. **Detect the Change**
   - Monitor `settings.authentication.apiKey` for changes
   - Triggered when user saves new API key in settings
   - Also triggered when user clears API key (switches to unauthenticated)

2. **Clean Disconnect**
   - Close existing WebSocket connection gracefully
   - Cancel any pending requests/subscriptions
   - Clear any auth-related state

3. **Reconnect with New Auth**
   - Create new socket with updated token (or no token)
   - Re-establish WebSocket connection
   - Show brief loading/reconnecting state to user

4. **Handle Edge Cases**
   - API key changes from `""` to `"token123"` (unauthenticated → authenticated)
   - API key changes from `"token123"` to `"token456"` (change tokens)
   - API key changes from `"token123"` to `""` (authenticated → unauthenticated)
   - Rapid API key changes (debounce or queue reconnections)

### Implementation Strategy

```typescript
// BAD - Socket created immediately, no reconnection
const socket = createTrustGraphSocket(); // ❌ No access to settings yet
export const SocketContext = createContext(socket);

// GOOD - Socket created after settings load, reconnects on auth change
const SocketProvider = ({ children }) => {
  const { settings, isLoaded } = useSettings();
  const [socket, setSocket] = useState(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  
  useEffect(() => {
    if (!isLoaded) return; // Wait for settings
    
    // Show reconnecting state during transitions
    setIsReconnecting(true);
    
    // Clean up old socket if it exists
    if (socket) {
      console.log("Closing existing socket for reconnection...");
      socket.close();
    }
    
    // Create new socket with current auth settings
    const newSocket = createTrustGraphSocket(settings.authentication.apiKey);
    
    // Wait for connection to establish
    newSocket.addEventListener('open', () => {
      console.log("Socket connected with auth:", 
                  settings.authentication.apiKey ? 'enabled' : 'disabled');
      setIsReconnecting(false);
    });
    
    setSocket(newSocket);
    
    return () => newSocket?.close();
  }, [isLoaded, settings.authentication.apiKey]); // Re-run when apiKey changes
  
  if (!socket || isReconnecting) {
    return (
      <Box>
        <LoadingSpinner />
        <Text>{isReconnecting ? 'Reconnecting...' : 'Initializing...'}</Text>
      </Box>
    );
  }
  
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
};
```

## Technical Approach

### Phase 1: Deferred Socket Initialization
1. Convert static socket creation to dynamic SocketProvider
2. Wait for settings to load before creating socket
3. Show loading state while settings/socket initialize
4. Pass loaded auth token to socket creation

### Phase 2: Basic Authentication
1. Append `?token=<token>` to WebSocket URL if token exists
2. Add Bearer token to REST API headers if token exists
3. Handle basic auth success/failure

### Phase 3: Socket Reconnection on Auth Change
1. Detect when authentication settings change
2. Close existing socket connection gracefully
3. Create new socket with updated authentication
4. Handle in-flight requests during reconnection
5. Restore any active subscriptions/state (if needed)

### Phase 4: Enhanced Features (Future)
1. Token validation endpoint
2. Authentication status indicator
3. Auto-retry with exponential backoff on auth failures
4. Better error messages for authentication issues

## Security Considerations

1. **Token Storage**:
   - Stored in localStorage via settings system
   - Never logged to console in production
   - Masked in UI displays

2. **Token Transmission**:
   - Sent via secure headers
   - HTTPS required in production
   - No token in URL parameters

3. **Error Handling**:
   - Generic error messages to users
   - Detailed errors only in development mode
   - Rate limiting on failed attempts

## Testing Strategy

1. **Unit Tests**:
   - Settings storage and retrieval
   - Header injection logic
   - Error handling paths

2. **Integration Tests**:
   - Full authentication flow
   - Token persistence across sessions
   - Error recovery scenarios

3. **Manual Testing**:
   - UI interaction flows
   - Network failure scenarios
   - Token expiration handling

## Migration Path

1. **Backwards Compatibility**:
   - Support unauthenticated mode (empty token)
   - Graceful degradation for older backends
   - Feature detection for auth requirements

2. **Rollout Strategy**:
   - Deploy with auth disabled by default
   - Enable per-user via settings
   - Monitor error rates during rollout

## Implementation Example

```typescript
// In trustgraph-socket.ts
export const createTrustGraphSocket = (token?: string) => {
  // Use relative URL for WebSocket connection
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const baseUrl = `${protocol}//${host}/api/socket`;
  const wsUrl = token ? `${baseUrl}?token=${token}` : baseUrl;
  
  console.log(`Creating socket with auth: ${token ? 'enabled' : 'disabled'}`);
  
  // Create WebSocket connection with authentication
  const socket = new WebSocket(wsUrl);
  
  // ... rest of socket implementation
};

// In SocketProvider.tsx (NEW FILE)
export const SocketProvider = ({ children }) => {
  const { settings, isLoaded } = useSettings();
  const [socket, setSocket] = useState(null);
  const [isSocketReady, setIsSocketReady] = useState(false);
  
  useEffect(() => {
    // CRITICAL: Wait for settings to load
    if (!isLoaded) {
      console.log("Waiting for settings to load before creating socket...");
      return;
    }
    
    console.log("Settings loaded, creating socket with auth:", 
                settings.authentication.apiKey ? 'enabled' : 'disabled');
    
    // Clean up existing socket before creating new one
    if (socket) {
      console.log("API key changed, closing existing socket...");
      socket.close();
      setIsSocketReady(false);
    }
    
    // Create socket with current auth settings
    const newSocket = createTrustGraphSocket(settings.authentication.apiKey);
    
    // Mark socket as ready when connection opens
    newSocket.addEventListener('open', () => {
      console.log("Socket connected successfully");
      setIsSocketReady(true);
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket?.close();
      setIsSocketReady(false);
    };
  }, [isLoaded, settings.authentication.apiKey]); // Reconnects when API key changes
  
  // Show loading state until both settings and socket are ready
  if (!isSocketReady) {
    return (
      <Box>
        <CenterSpinner />
        <Text>Initializing connection...</Text>
      </Box>
    );
  }
  
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
};

// In App.tsx or index.tsx
<QueryClientProvider client={queryClient}>
  <SocketProvider> {/* Now waits for settings before creating socket */}
    <ChakraProvider>
      <App />
    </ChakraProvider>
  </SocketProvider>
</QueryClientProvider>
```

## Open Questions

1. **Socket Reconnection Strategy**:
   - Should socket reconnect automatically when auth settings change?
   - How to handle in-flight requests during reconnection?
   - Should we show a loading state during reconnection?

2. **Error Handling**:
   - How does the backend communicate auth failures (401 vs 403)?
   - Should we automatically redirect to settings on auth failure?
   - How to differentiate between network errors and auth errors?

3. **Token Security**:
   - Should we support token rotation/refresh?
   - How long should tokens be valid?
   - Should we add CSRF protection for REST calls?

## References

- [Settings System Documentation](./SETTINGS.md)
- [Socket Implementation](../../src/api/trustgraph/socket.ts)
- [TrustGraph Socket API](../../src/api/trustgraph/trustgraph-socket.ts)