// ⚡ Remna-Bot Overlay Service Worker
// Intercepts all HTML page requests and injects the overlay persistently.
// Persists across page reloads, route changes, and app refreshes in Telegram.

const CACHE_NAME = 'remnabot-overlay-v1';
const OVERLAY_CSS = '/remnabot_overlay.css';
const OVERLAY_JS = '/remnabot_overlay.js';

// Pre-cache our overlay assets on install
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll([OVERLAY_CSS, OVERLAY_JS]).catch(() => {});
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

// Intercept all fetch requests
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Serve our overlay assets from cache for maximum speed
    if (url.pathname === OVERLAY_CSS || url.pathname === OVERLAY_JS) {
        event.respondWith(
            caches.match(event.request).then(cached => {
                const networkFetch = fetch(event.request).then(response => {
                    // Update cache with fresh version
                    if (response.ok) {
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
                    }
                    return response;
                });
                return cached || networkFetch;
            })
        );
        return;
    }

    // Skip: non-GET, API calls, Next.js chunks, images, fonts
    if (event.request.method !== 'GET') return;
    if (url.pathname.startsWith('/api/')) return;
    if (url.pathname.startsWith('/_next/')) return;
    if (url.pathname.startsWith('/remna_embed')) return;
    if (url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff|woff2|ttf)$/)) return;

    // Only process HTML page requests (panel SPA routes)
    const acceptHeader = event.request.headers.get('accept') || '';
    if (!acceptHeader.includes('text/html')) return;

    // Intercept HTML and inject our overlay
    event.respondWith(
        fetch(event.request).then(response => {
            const contentType = response.headers.get('content-type') || '';
            if (!contentType.includes('text/html')) return response;

            return response.text().then(html => {
                const injection = `
  <link rel="stylesheet" href="${OVERLAY_CSS}">
  <script src="${OVERLAY_JS}" defer></script>
`;
                const modified = html.includes('</head>')
                    ? html.replace('</head>', injection + '</head>')
                    : html + injection;

                const headers = new Headers(response.headers);
                headers.set('Cache-Control', 'no-cache, no-store, must-revalidate');
                headers.delete('Content-Length'); // body length changed

                return new Response(modified, {
                    status: response.status,
                    statusText: response.statusText,
                    headers
                });
            });
        }).catch(() => fetch(event.request))
    );
});
