import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    preserveSymlinks: true,
    dedupe: ["react", "react-dom", "@trustgraph/react-provider"],
  },
  server: {
    proxy: {
      "/api/socket": {
        //        target: "wss://broker.app.trustgraph.ai/",
        target: "ws://localhost:8088/",
        changeOrigin: true,
        ws: true,
        secure: false,
        // Preserve query parameters (like ?token=hello) when rewriting
        rewrite: (path) => path.replace("/api/socket", "/api/v1/socket"),
      },
      "/api/export-core": {
        target: "http://localhost:8088/",
        changeOrigin: true,
        secure: false,
        rewrite: (x) => x.replace("/api/export-core", "/api/v1/export-core"),
      },
      "/api/import-core": {
        target: "http://localhost:8088/",
        changeOrigin: true,
        secure: false,
        rewrite: (x) => x.replace("/api/import-core", "/api/v1/import-core"),
      },
    },
  },
});
