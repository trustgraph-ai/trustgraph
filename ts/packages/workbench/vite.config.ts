import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api/v1/rpc": {
        target: "ws://localhost:8088/",
        ws: true,
      },
      "/api/v1": {
        target: "http://localhost:8088/",
      },
      "/otel": {
        target: "http://localhost:4328/",
        rewrite: (p) => p.replace(/^\/otel/, ""),
      },
    },
  },
});
