import "@testing-library/jest-dom";
import { vi, beforeEach } from "vitest";
import type { MockedObject } from "vitest";

// Mock WebSocket globally
global.WebSocket = vi.fn(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1,
})) as MockedObject<WebSocket>;

// Mock ResizeObserver
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock window.location
Object.defineProperty(window, "location", {
  value: {
    href: "http://localhost:3000",
    origin: "http://localhost:3000",
    pathname: "/",
    search: "",
    hash: "",
  },
  writable: true,
});

// Set up DOM for Portal components globally
// Create portal containers that persist across tests
const setupPortalContainers = () => {
  // Ensure portal containers exist for Dialog and other Portal components
  if (!document.getElementById("chakra-portal")) {
    const portalRoot = document.createElement("div");
    portalRoot.setAttribute("id", "chakra-portal");
    document.body.appendChild(portalRoot);
  }

  // Also create a generic portal root that some components might use
  if (!document.getElementById("portal-root")) {
    const portalRoot = document.createElement("div");
    portalRoot.setAttribute("id", "portal-root");
    document.body.appendChild(portalRoot);
  }
};

// Set up portals immediately when setup runs
setupPortalContainers();

beforeEach(() => {
  // Ensure portal containers are clean but still exist
  const chakraPortal = document.getElementById("chakra-portal");
  if (chakraPortal) {
    chakraPortal.innerHTML = "";
  }

  const portalRoot = document.getElementById("portal-root");
  if (portalRoot) {
    portalRoot.innerHTML = "";
  }

  // Recreate if they were removed
  setupPortalContainers();
});
