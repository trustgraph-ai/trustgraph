# Socket Reliability Refactor

## Overview

This document outlines a comprehensive refactor to address critical issues in the TrustGraph UI WebSocket connection handling that are causing exponential retry storms and excessive logging.

## Current Problems

### Issue #1: Dual Retry System Conflict ⚠️ CRITICAL

**Problem**: Two independent retry mechanisms create multiplicative retry storms:

1. **BaseApi Socket-Level Reconnection** (`trustgraph-socket.ts`)
   - Triggers on `onClose()` events
   - 10 attempts with exponential backoff (2-60 seconds)
   - Handles socket-level connection failures

2. **ServiceCall Request-Level Retries** (`service-call.ts`)
   - Triggers on send failures and timeouts
   - 3 retries per request with backoff
   - **Calls `socket.reopen()` which triggers BaseApi reconnection**

**Result**: Single connection failure → 3 request retries × 10 socket reconnections = **30+ retry attempts**

```typescript
// service-call.ts:160, 174 - PROBLEM LINES
console.log("Reopen...");
this.socket.reopen(); // ← Triggers BaseApi reconnection
```

### Issue #2: SocketProvider Dependency Loop ✅ FIXED
**Status**: Resolved by removing `socket` from dependency array

### Issue #3: Inconsistent Request Retry Backoff ⚠️ MEDIUM
**Location**: `service-call.ts:170`

```typescript
// Inconsistent retry strategies:
setTimeout(this.attempt.bind(this), backoffDelay);  // Exponential backoff ✅
setTimeout(this.attempt.bind(this), 500);          // Fixed 500ms ❌ (spams)
setTimeout(this.attempt.bind(this), backoffDelay);  // Exponential backoff ✅
```

### Issue #4: Concurrent Socket Reopen Calls ⚠️ MEDIUM
**Problem**: Multiple failed requests simultaneously call `socket.reopen()`:
- No coordination between ServiceCalls
- Redundant reconnection attempts
- Race conditions in connection state

## Proposed Solution: Centralized Retry Strategy

### Architectural Decision

**Adopt Option A: Let BaseApi handle ALL reconnection logic**

**Rationale**:
- ✅ Single source of truth for connection state
- ✅ BaseApi already has robust exponential backoff
- ✅ Eliminates retry system conflicts
- ✅ Cleaner separation of concerns
- ✅ Minimal code changes required

### Implementation Plan

#### Phase 1: Remove ServiceCall Reconnection Triggers

**File**: `src/api/trustgraph/service-call.ts`

**Changes**:
1. Remove `this.socket.reopen()` calls (lines 160, 174)
2. Replace with passive waiting for socket reconnection
3. Standardize backoff for all retry paths

```typescript
// BEFORE (service-call.ts:156-161)
console.log("Reopen...");
this.socket.reopen(); // ← REMOVE THIS

// AFTER
console.log("Message send failure, waiting for socket reconnection...");
// Let BaseApi handle reconnection, just retry the request
```

#### Phase 2: Improve Request Queueing Strategy

**Current Behavior**: ServiceCall attempts fail when socket is not ready

**New Behavior**: ServiceCall waits for socket to become available

```typescript
// Enhanced attempt() method logic
attempt() {
  if (this.complete) return;
  
  this.retries--;
  if (this.retries < 0) {
    // Give up after retries exhausted
    this.error("Ran out of retries");
    return;
  }

  if (this.socket.ws && this.socket.ws.readyState === WebSocket.OPEN) {
    // Socket ready - send message
    try {
      this.socket.ws.send(JSON.stringify(this.msg));
      this.timeoutId = setTimeout(this.onTimeout.bind(this), this.timeout);
    } catch (e) {
      // Send failed - wait and retry (no socket reopen)
      setTimeout(this.attempt.bind(this), this.calculateBackoff());
    }
  } else {
    // Socket not ready - wait for BaseApi to reconnect
    console.log("Request", this.mid, "waiting for socket reconnection...");
    setTimeout(this.attempt.bind(this), this.calculateBackoff());
  }
}

calculateBackoff() {
  return Math.min(
    SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, 3 - this.retries) + Math.random() * 1000,
    30000
  );
}
```

#### Phase 3: Enhanced BaseApi Connection Management

**File**: `src/api/trustgraph/trustgraph-socket.ts`

**Improvements**:
1. Add connection state tracking
2. Prevent redundant reconnection attempts
3. Improve logging for debugging

```typescript
class BaseApi {
  reconnectionState: 'idle' | 'reconnecting' | 'failed' = 'idle';

  scheduleReconnect() {
    // Prevent concurrent reconnection attempts
    if (this.reconnectionState === 'reconnecting') {
      console.log("[socket] Reconnection already in progress, skipping");
      return;
    }
    
    if (this.reconnectTimer) return;
    
    this.reconnectionState = 'reconnecting';
    // ... existing logic
  }

  onOpen() {
    console.log("[socket open]");
    this.reconnectAttempts = 0;
    this.reconnectionState = 'idle'; // Reset state
    
    // Clear any pending reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
  }
}
```

## Expected Benefits

### Immediate Impact
- **80-90% reduction in retry attempts** - eliminates dual retry system
- **Cleaner logs** - single source of reconnection messages
- **Predictable behavior** - one retry algorithm instead of two

### Log Message Changes
```
// BEFORE: Chaotic dual retry messages
[socket] Reconnecting in 2000ms (attempt 1)
Request test-123 timed out
Message send failure, retry...
Reopen...
[socket] Reconnecting in 4000ms (attempt 2) 
Request test-123 ran out of retries
Request test-456 timed out
Reopen...
[socket] Reconnecting in 8000ms (attempt 3)

// AFTER: Clean, coordinated messages  
[socket] Reconnecting in 2000ms (attempt 1)
Request test-123 waiting for socket reconnection...
Request test-456 waiting for socket reconnection...
[socket open]
Request test-123 sent successfully
Request test-456 sent successfully
```

### Performance Improvements
- **Reduced CPU usage** - fewer concurrent timers and retry loops
- **Less network spam** - coordinated reconnection attempts
- **Better user experience** - faster recovery from connection issues

## Risk Assessment

### Low Risk Changes
- ✅ Removing `socket.reopen()` calls from ServiceCall
- ✅ Standardizing backoff calculations
- ✅ Adding connection state tracking

### Potential Issues
- ⚠️ **Request timeout behavior may change** - requests may take longer to fail
- ⚠️ **Need to test edge cases** - rapid API key changes, server restarts
- ⚠️ **Verify inflight request cleanup** - ensure requests don't hang indefinitely

### Mitigation Strategies
1. **Preserve existing timeout behavior** - requests should still timeout appropriately
2. **Add circuit breaker** - stop retrying after socket reconnection gives up
3. **Comprehensive testing** - test connection failure scenarios

## Testing Strategy

### Unit Tests
- Mock WebSocket state transitions
- Verify ServiceCall doesn't trigger socket reopens
- Test backoff calculations are consistent

### Integration Tests  
- Test connection failure and recovery scenarios
- Verify request queueing during reconnection
- Test concurrent request handling

### Manual Testing Scenarios
1. **Server shutdown** - verify clean reconnection behavior
2. **Network interruption** - test mobile/wifi scenarios
3. **API key changes** - ensure proper socket recreation
4. **High load** - multiple concurrent requests during connection issues

## Implementation Timeline

### Phase 1: Core Fixes (1-2 hours)
- Remove `socket.reopen()` calls from ServiceCall
- Standardize ServiceCall backoff calculations
- Add basic connection state tracking

### Phase 2: Enhanced Reliability (2-3 hours)
- Implement request queueing improvements
- Add comprehensive logging
- Enhanced error handling

### Phase 3: Testing & Validation (2-4 hours)
- Unit test coverage
- Integration testing
- Performance validation

**Total Estimated Effort**: 5-9 hours

## Success Metrics

### Quantitative Goals
- **Reduce retry attempts by 80%+** during connection failures
- **Eliminate concurrent socket reopen calls**  
- **Standardize all retry backoff to exponential**

### Qualitative Goals
- **Cleaner, more understandable logs**
- **Predictable connection recovery behavior**
- **Better separation of concerns in codebase**

## Future Enhancements

### Potential Improvements (Out of Scope)
1. **Request prioritization** - critical requests retry faster
2. **Connection health monitoring** - proactive reconnection
3. **Metrics collection** - track connection reliability
4. **Advanced queueing** - persist important requests across sessions

### Monitoring Additions
```typescript
// Connection reliability metrics
interface SocketMetrics {
  connectionAttempts: number;
  successfulConnections: number;
  averageReconnectionTime: number;
  requestsLostDuringReconnection: number;
}
```

## Conclusion

This refactor addresses the root cause of socket retry storms by establishing BaseApi as the single authority for connection management. The changes are surgical and low-risk, focusing on removing the problematic dual retry system while preserving all existing functionality.

**Next Steps**: Implement Phase 1 changes and validate that retry storms are eliminated before proceeding with enhanced features.