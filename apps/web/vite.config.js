import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  server: {
    port: 12702,
    proxy: {
      "/api": {
        target: "http://localhost:12701",
        changeOrigin: true,
      },
    },
  },
})
