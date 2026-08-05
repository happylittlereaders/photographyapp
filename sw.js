// Minimal service worker: exists mainly so the browser recognizes this
// as an installable PWA. Streamlit's own network traffic passes through
// untouched.
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Network-first, no custom caching -- Streamlit content changes often.
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
