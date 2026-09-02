// Cache app shell sahaja. API dan siaran MJPEG tidak pernah dicache.
const CACHE_NAME="smart-trafik-shell-v7",APP_SHELL=["./index.html","./offline.html","./manifest.json","./icons/icon-192.svg","./icons/icon-512.svg"];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(APP_SHELL)).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(names=>Promise.all(names.filter(name=>name!==CACHE_NAME).map(name=>caches.delete(name)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{const url=new URL(event.request.url);if(url.pathname.startsWith("/api/")||url.pathname==="/video-feed"||event.request.method!=="GET")return;if(event.request.mode==="navigate"){event.respondWith(fetch(event.request).catch(()=>caches.match("./offline.html")));return}event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)))});
