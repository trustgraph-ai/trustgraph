/**
 * Authenticated fetch utility
 *
 * Provides fetch functions that automatically include Bearer token authentication
 * when an API key is configured in settings.
 */

/**
 * Creates an authenticated fetch function that includes Bearer token when available
 * @param apiKey - Optional API key for authentication
 * @returns Fetch function with automatic auth headers
 */
export const createAuthenticatedFetch = (apiKey?: string) => {
  return (url: string, options: RequestInit = {}) => {
    const headers: HeadersInit = {
      ...options.headers,
    };

    // Add Bearer token if API key is present
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    return fetch(url, {
      ...options,
      headers,
    });
  };
};

/**
 * Hook-based authenticated fetch that uses current settings
 * This is a React hook that must be called from within a component
 */
export const useAuthenticatedFetch = () => {
  // Note: This will be implemented when we need it in components
  // For now, we'll use the createAuthenticatedFetch directly with settings
  throw new Error(
    "useAuthenticatedFetch not yet implemented - use createAuthenticatedFetch with settings",
  );
};
