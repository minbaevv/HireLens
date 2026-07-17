// Минимальный service worker для PWA (B3).
// Цель: дать браузеру установить приложение и кэшировать статику,
// НЕ трогая API. Данные интервью/аута/кандидатов всегда идут только
// в сеть — отдавать кандидату из кэша устаревший ответ AI нельзя.
//
// ⚠️ Это не полноценный precache через build-манифест (workbox/
// vite-plugin-pwa) — простой runtime-кэш без новых npm-зависимостей.

const CACHE_NAME = 'ai-hr-shell-v1'
const APP_SHELL = ['/', '/manifest.webmanifest']
const CACHEABLE_EXT = /\.(js|css|svg|png|jpg|jpeg|woff2?|ico)$/

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).catch(() => {})
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  const isSameOrigin = url.origin === self.location.origin
  const isNavigation = request.mode === 'navigate'
  const isStaticAsset = isSameOrigin && CACHEABLE_EXT.test(url.pathname)

  if (!isNavigation && !isStaticAsset) return

  event.respondWith(
    caches.match(request).then((cached) => {
      const networkFetch = fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const clone = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone))
          }
          return response
        })
        .catch(() => cached)
      return cached || networkFetch
    })
  )
})
