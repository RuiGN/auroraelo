/**
 * Aurora Elo — Service Worker (PWA)
 *
 * Estratégia: Network First para páginas dinâmicas Django,
 * Cache First para assets estáticos (CSS/JS/imagens).
 *
 * Versão do cache: incrementar ao fazer deploy com mudanças de assets.
 */

const CACHE_VERSION = "v1";
const STATIC_CACHE = `aurora-static-${CACHE_VERSION}`;
const PAGES_CACHE  = `aurora-pages-${CACHE_VERSION}`;

// Assets estáticos que devem ser pré-cacheados na instalação
const PRECACHE_ASSETS = [
  "/static/duralux/css/bootstrap.min.css",
  "/static/duralux/css/theme.min.css",
  "/static/duralux/vendors/css/feather.min.css",
  "/static/css/aurora-theme-override.css",
  "/static/design_system/css/aurora.css",
  "/static/aurora_elo/img/aurora-elo-logo.webp",
  "/static/aurora_elo/img/aurora-elo-icon.png",
  "/static/aurora_elo/manifest.json",
];

// Rotas que NUNCA devem ser interceptadas pelo SW (admin, API, auth)
const BYPASS_PREFIXES = [
  "/admin/",
  "/api/",
  "/accounts/",
  "/health/",
  "/stripe/",
  "/jsi18n/",
];

// ─────────────────────────────────────────────────────────────────────────────
// Install: pré-carrega os assets estáticos
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Activate: limpa caches de versões anteriores
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter(
              (key) => key !== STATIC_CACHE && key !== PAGES_CACHE
            )
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Fetch: roteamento de estratégia
// ─────────────────────────────────────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Ignora requisições cross-origin
  if (url.origin !== self.location.origin) return;

  // Ignora rotas de bypass (admin, API, auth)
  if (BYPASS_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) return;

  // Ignora métodos não-GET
  if (event.request.method !== "GET") return;

  const isStaticAsset = url.pathname.startsWith("/static/");

  if (isStaticAsset) {
    // Cache First para estáticos (imutáveis por hash de manifest)
    event.respondWith(
      caches.match(event.request).then(
        (cached) =>
          cached ||
          fetch(event.request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(STATIC_CACHE).then((cache) => cache.put(event.request, clone));
            }
            return response;
          })
      )
    );
  } else {
    // Network First para páginas Django (dados sempre frescos)
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(PAGES_CACHE).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() =>
          // Fallback para cache quando offline
          caches.match(event.request).then(
            (cached) =>
              cached ||
              new Response(
                `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Aurora Elo — Offline</title>
                <style>
                  body { font-family: system-ui, sans-serif; background: #0A2540; color: #e2e8f0;
                         display: flex; align-items: center; justify-content: center;
                         min-height: 100vh; margin: 0; text-align: center; padding: 2rem; }
                  .card { background: rgba(255,255,255,.08); border-radius: 1rem;
                          padding: 2.5rem; max-width: 400px; }
                  h1 { font-size: 1.5rem; margin-bottom: .75rem; }
                  p { color: #94a3b8; margin-bottom: 1.5rem; }
                  button { background: #7c3aed; color: #fff; border: 0; border-radius: .5rem;
                           padding: .75rem 1.5rem; font-size: 1rem; cursor: pointer; }
                </style></head>
                <body><div class="card">
                  <h1>Sem conexão</h1>
                  <p>Verifique sua internet e tente novamente.</p>
                  <button onclick="location.reload()">Tentar novamente</button>
                </div></body></html>`,
                { headers: { "Content-Type": "text/html; charset=utf-8" } }
              )
          )
        )
    );
  }
});
