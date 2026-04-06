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
      "/api/socket": {
        target: "ws://localhost:8088/",
        ws: true,
        rewrite: (p) => p.replace("/api/socket", "/api/v1/socket"),
      },
      "/api/v1": {
        target: "http://localhost:8088/",
      },
    },
  },
});
