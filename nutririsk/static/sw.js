/**
 * NutriRisk AI — Progressive Web App (PWA) Service Worker
 * Provides offline asset caching, network-first resilience, and standalone App Mode support.
 */

const CACHE_NAME = "nutririsk-cache-v1";
const STATIC_ASSETS = [
  "/",
  "/static/manifest.json",
  "/static/css/bootstrap.min.css",
  "/static/css/style.css",
  "/static/js/bootstrap.bundle.min.js",
  "/static/js/chart.umd.min.js",
  "/static/js/main.js",
  "/static/img/icon-192.png",
  "/static/img/icon-512.png",
  "/static/img/apple-touch-icon.png"
];

// 1. Install Event: Pre-cache core static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[Service Worker] Pre-caching static assets for NutriRisk AI App...");
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activate Event: Clean up outdated caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("[Service Worker] Deleting outdated cache:", name);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch Event: Network-first for pages, Cache-first for static assets
self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Skip non-GET requests (e.g. POST /predict or /login)
  if (req.method !== "GET") {
    return;
  }

  // Static Assets: Cache-first strategy
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((cachedResp) => {
        if (cachedResp) {
          return cachedResp;
        }
        return fetch(req).then((networkResp) => {
          if (networkResp && networkResp.status === 200) {
            const clone = networkResp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return networkResp;
        });
      })
    );
    return;
  }

  // HTML Pages: Network-first strategy with offline fallback
  event.respondWith(
    fetch(req).then((networkResp) => {
      if (networkResp && networkResp.status === 200) {
        const clone = networkResp.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
      }
      return networkResp;
    }).catch(async () => {
      const cached = await caches.match(req);
      if (cached) {
        return cached;
      }
      // Return custom offline clinical fallback response
      return new Response(
        `<!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>NutriRisk AI — Offline App Mode</title>
          <link rel="stylesheet" href="/static/css/bootstrap.min.css">
          <link rel="stylesheet" href="/static/css/style.css">
        </head>
        <body class="bg-light d-flex align-items-center justify-content-center min-vh-100">
          <div class="card p-4 shadow-sm text-center" style="max-width: 460px;">
            <div style="font-size: 3rem;">📡</div>
            <h3 class="fw-bold text-dark mt-2">Offline App Mode</h3>
            <p class="text-muted small">You are currently offline. NutriRisk AI is operating in standalone offline mode. Historical records and cached screens remain accessible.</p>
            <a href="/" class="btn btn-primary-teal w-100">Retry Connection</a>
          </div>
        </body>
        </html>`,
        { headers: { "Content-Type": "text/html; charset=utf-8" } }
      );
    })
  );
});
