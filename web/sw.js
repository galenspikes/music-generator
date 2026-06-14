// Service worker: precache the app shell + Pyodide runtime + engine so the app
// works fully offline, and cache-first everything else (the CDN player script
// and its SoundFont) so playback survives offline after the first online load.

const CACHE = "musicgen-v1";

const PRECACHE = [
  "./", "./index.html", "./styles.css", "./app.js", "./manifest.webmanifest",
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

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        // Cache successful and opaque (cross-origin CDN) responses for next time.
        if (res && (res.ok || res.type === "opaque")) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match("./index.html"));
    })
  );
});
