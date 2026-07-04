import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Standalone Chord Recipes instrument — its own Vite project (separate PWA
// scope from webapp/frontend) sharing only the backend API and a few trivial
// fetch wrappers in webapp/shared/. During dev it runs on :5174 and proxies
// /api (and /showcase) to the FastAPI backend on :8753, same pattern as the
// main webapp's vite.config.js.
export default defineConfig({
  base: "/chords/",
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/icon-192.png", "icons/icon-512.png"],
      manifest: {
        name: "Chord Recipes",
        short_name: "Chords",
        description: "A tap-driven chord-progression instrument and library.",
        start_url: "/chords/",
        scope: "/chords/",
        display: "standalone",
        background_color: "#101215",
        theme_color: "#101215",
        icons: [
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Only precache this app's own build output; API responses and
        // soundfont samples are handled by the runtime routes below.
        globPatterns: ["**/*.{js,css,html,svg,png,ico}"],
        runtimeCaching: [
          {
            urlPattern: /\/api\/(vocab|recipes)$/,
            handler: "StaleWhileRevalidate",
            options: { cacheName: "chords-catalogue" },
          },
          {
            urlPattern: /\/api\/progressions/,
            handler: "NetworkFirst",
            options: { cacheName: "chords-progressions", networkTimeoutSeconds: 3 },
          },
          {
            // The soundfont sample host smplr's Soundfont() instrument fetches
            // from (see webapp/shared: audio.js) — cache aggressively so the
            // instrument works offline after first load.
            urlPattern: ({ url }) =>
              url.hostname === "gleitz.github.io" || url.hostname === "goldst.dev",
            handler: "CacheFirst",
            options: {
              cacheName: "chords-soundfont-samples",
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@shared": path.resolve(__dirname, "../shared"),
    },
  },
  server: {
    port: 5174,
    fs: { allow: [path.resolve(__dirname, "..")] },
    proxy: {
      "/api": "http://127.0.0.1:8753",
      "/showcase": "http://127.0.0.1:8753",
    },
  },
  build: { outDir: "dist" },
});
