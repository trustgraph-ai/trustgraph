import React from "react";
import ReactDOM from "react-dom/client";
import { RegistryProvider, useAtomMount } from "@effect/atom-react";
import App from "@/App";
import { connectionStateAtom, themeClassAtom } from "@/atoms/workbench";
import { getWorkbenchQaInitialValues } from "@/qa/initial-values";
import "@/index.css";

function AppRoot() {
  useAtomMount(themeClassAtom);
  useAtomMount(connectionStateAtom);

  return <App />;
}

const rootElement = document.getElementById("root");
if (rootElement === null) {
  // Host boundary: the workbench cannot render without its mount point.
  throw new Error("Workbench root element #root not found");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <RegistryProvider defaultIdleTTL={1_000} initialValues={getWorkbenchQaInitialValues()}>
      <AppRoot />
    </RegistryProvider>
  </React.StrictMode>,
);

// Dismiss splash screen once React has mounted
requestAnimationFrame(() => {
  const splash = document.getElementById("splash");
  if (splash !== null) {
    splash.classList.add("fade-out");
    splash.addEventListener("transitionend", () => splash.remove());
  }
});
