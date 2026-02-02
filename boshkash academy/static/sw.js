self.addEventListener('install', (e) => {
    console.log('Service Worker: Installed');
});

self.addEventListener('fetch', (e) => {
    // Simple pass-through for now
    e.respondWith(fetch(e.request));
});
