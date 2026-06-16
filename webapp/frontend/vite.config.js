import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During dev the React app runs on :5173 and proxies /api to the FastAPI
// backend on :8753, so the browser talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8753",
    },
  },
  build: { outDir: "dist" },
});
