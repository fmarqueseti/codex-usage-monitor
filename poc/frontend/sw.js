const CACHE='codex-usage-monitor-v1';
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(['/','/css/app.css','/js/app.js','/manifest.webmanifest']))));
self.addEventListener('fetch',event=>{if(event.request.url.includes('/api/'))return;event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)))});
