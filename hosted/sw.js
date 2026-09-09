const CACHE='procureflow-v18';
const CORE=['/','/app.css?v=18','/auth.css?v=18','/mobile.css?v=18','/chat.css?v=18','/accounts.css?v=18','/hosted.js?v=18','/i18n.js?v=18','/accounts.js?v=18','/chat.js?v=18','/manifest.webmanifest','/icon.svg','/manual.html'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.pathname.startsWith('/api/'))return;event.respondWith(fetch(event.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));return response}).catch(()=>caches.match(event.request).then(hit=>hit||caches.match('/'))))});
