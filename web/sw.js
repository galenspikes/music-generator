// Service worker. Strategy:
//   - App shell (html/js/css/json, same-origin small files): NETWORK-FIRST so a
//     new deploy shows up immediately; falls back to cache when offline.
//   - Heavy, effectively-immutable assets (Pyodide runtime, engine.zip, icons):
//     CACHE-FIRST (fetched once, reused offline).
//   - Cross-origin CDN (player + soundfont): cache-first so playback survives
//     offline after the first online load.
// Bump CACHE to force returning visitors onto the latest shell.

const CACHE = "musicgen-v4";

const PRECACHE = [
  "./", "./index.html", "./styles.css", "./app.js", "./builder.js",
  "./manifest.webmanifest", "./examples.json", "./recipes.json",
  "./icons/icon-192.png", "./icons/icon-512.png",
  "./engine.zip",
  "./pyodide/pyodide.mjs", "./pyodide/pyodide.asm.js", "./pyodide/pyodide.asm.wasm",
  "./pyodide/python_stdlib.zip", "./pyodide/pyodide-lock.json",
  "./pyodide/numpy-1.26.4-cp312-cp312-pyodide_2024_0_wasm32.whl",
  "./pyodide/PyYAML-6.0.1-cp312-cp312-pyodide_2024_0_wasm32.whl",
  "./pyodide/packaging-23.2-py3-none-any.whl",
  "./pyodide/micropip-0.6.0-py3-none-any.whl",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

const isImmutable = (u) =>
  u.pathname.includes("/pyodide/") || u.pathname.endsWith("/engine.zip") || u.pathname.includes("/icons/");

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  if (sameOrigin && !isImmutable(url)) {
    // network-first for the app shell
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req).then((hit) => hit || caches.match("./index.html")))
    );
    return;
  }

  // cache-first for big/immutable assets and cross-origin (CDN)
  e.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res && (res.ok || res.type === "opaque")) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match("./index.html")))
  );
});
