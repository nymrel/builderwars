import { defineConfig, type Plugin } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { IncomingMessage } from "node:http";

const root = fileURLToPath(new URL(".", import.meta.url));
const webPages = {
  main: resolve(root, "index.html"),
  about: resolve(root, "about.html"),
  games: resolve(root, "games.html"),
  verify: resolve(root, "verify.html"),
  guide: resolve(root, "guide.html"),
};
const originRoutes: Record<string, string> = {
  "/about": "/about.html",
  "/games": "/games.html",
  "/verify": "/verify.html",
  "/guide": "/guide.html",
};

function originCleanUrls(): Plugin {
  const rewrite = (req: IncomingMessage) => {
    const raw = req.url?.split("?")[0] || "";
    const path = raw.length > 1 ? raw.replace(/\/$/, "") : raw;
    const dest = originRoutes[path];
    if (dest) req.url = dest + (req.url?.includes("?") ? `?${req.url.split("?")[1]}` : "");
  };
  return {
    name: "origin-clean-urls",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        rewrite(req);
        next();
      });
    },
    configurePreviewServer(server) {
      server.middlewares.use((req, _res, next) => {
        rewrite(req);
        next();
      });
    },
  };
}

// Packaged assets do not receive Vercel headers. No loopback exception or remote scripts.
export const nativeContentPolicy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https: wss:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'";
export default defineConfig(({ mode }) => ({
  build: {
    target: "es2022",
    outDir: mode === "native" ? "dist-native" : "dist",
    ...(mode === "native" ? {} : { rollupOptions: { input: webPages } }),
  },
  plugins: mode === "native" ? [{
    name: "native-content-policy",
    transformIndexHtml: { order: "pre" as const, handler: () => [
      { tag: "meta", attrs: { "http-equiv": "Content-Security-Policy", content: nativeContentPolicy }, injectTo: "head-prepend" as const },
      { tag: "meta", attrs: { name: "referrer", content: "no-referrer" }, injectTo: "head-prepend" as const },
    ] },
  }] : [originCleanUrls()],
}));
