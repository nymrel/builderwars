"use strict";

const CACHE_NAME = "builderwars-mobile-arena-demo-v5";
const LOCAL_ASSETS = [
  "./index.html?v=5",
  "./styles.css?v=5",
  "./app.js?v=5",
  "./manifest.webmanifest",
  "./assets/arena-mark.svg",
  "./data/demo-state.json"
];

self.addEventListener("install", (event) => {
  const requests = LOCAL_ASSETS.map((asset) => new Request(asset, { cache: "reload" }));
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(requests)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const requestURL = new URL(event.request.url);
  if (requestURL.origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).then((response) => {
    if (!response || response.status !== 200 || response.type !== "basic") return response;
    const copy = response.clone();
    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
    return response;
  }).catch(() => caches.match(event.request).then((cached) => cached || caches.match("./index.html?v=5"))));
});
