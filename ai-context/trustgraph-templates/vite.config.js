import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom', '@tanstack/react-query'],
    alias: {
      react: path.resolve('./node_modules/react'),
      'react-dom': path.resolve('./node_modules/react-dom'),
    },
  },
  server: {
    proxy: {
      "/api/socket": {
        //        target: "wss://broker.app.trustgraph.ai/",
        target: "ws://localhost:8088/",
        changeOrigin: true,
        ws: true,
        secure: false,
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
})
