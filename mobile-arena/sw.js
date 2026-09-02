"use strict";

const CACHE_NAME = "builderwars-mobile-arena-v40";
const NAVIGATION_FALLBACK = "./index.html?v=40";
const LOCAL_ASSETS = [
  NAVIGATION_FALLBACK,
  "./styles.css?v=40",
  "./data-adapter.js?v=40",
  "./app.js?v=40",
  "./ten-fronts.html?v=40",
  "./ten-fronts-blitz.css?v=40",
  "./ten-fronts-blitz.js?v=40",
  "./manifest.webmanifest",
  "./assets/arena-mark.svg",
  "./data/demo-state.json",
  "./data/arena-read-model.v1.json",
  "./data/tester-feedback-rubric.v1.json",
  "./data/creator-game-lab.v1.json"
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
  }).catch(async () => {
    const cached = await caches.match(event.request);
    if (cached) return cached;
    if (event.request.mode === "navigate") {
      return (await caches.match(NAVIGATION_FALLBACK)) || Response.error();
    }
    return Response.error();
  }));
});
