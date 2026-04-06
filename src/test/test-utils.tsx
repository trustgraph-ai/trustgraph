/**
 * Test utilities for wrapping components with required providers
 */

import React from "react";
import { render, RenderOptions } from "@testing-library/react";
import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  SocketContext,
  ConnectionStateContext,
} from "@trustgraph/react-provider";
import type { BaseApi } from "@trustgraph/client";

// Mock socket for testing
const mockSocket = {
  close: () => {},
  onConnectionStateChange: () => () => {},
  flow: () => ({
    triplesQuery: () => Promise.resolve([]),
    graphEmbeddingsQuery: () => Promise.resolve([]),
    nlpQuery: () => Promise.resolve({ graphql_query: "" }),
    objectsQuery: () => Promise.resolve({}),
    embeddings: () => Promise.resolve([]),
  }),
  flows: () => ({
    getFlows: () => Promise.resolve([]),
    startFlow: () => Promise.resolve({}),
    stopFlow: () => Promise.resolve({}),
  }),
} as unknown as BaseApi;

// Custom render function that includes all required providers
const customRender = (ui: React.ReactElement, options?: RenderOptions) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <SocketContext.Provider value={mockSocket}>
      <ConnectionStateContext.Provider value={{ status: "connected" }}>
        <QueryClientProvider client={queryClient}>
          <ChakraProvider value={defaultSystem}>{children}</ChakraProvider>
        </QueryClientProvider>
      </ConnectionStateContext.Provider>
    </SocketContext.Provider>
  );

  return render(ui, { wrapper: Wrapper, ...options });
};

// Re-export everything
export * from "@testing-library/react";

// Override render method
export { customRender as render };
