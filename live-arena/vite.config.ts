import { defineConfig, type Plugin } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { readFile } from "node:fs/promises";
import type { IncomingMessage } from "node:http";

const root = fileURLToPath(new URL(".", import.meta.url));
const webPages = {
  main: resolve(root, "index.html"),
  about: resolve(root, "about.html"),
  games: resolve(root, "games.html"),
  verify: resolve(root, "verify.html"),
  guide: resolve(root, "guide.html"),
  duels: resolve(root, "duels.html"),
  archive: resolve(root, "archive.html"),
};
const originRoutes: Record<string, string> = {
  "/about": "/about.html",
  "/games": "/games.html",
  "/verify": "/verify.html",
  "/guide": "/guide.html",
  "/duels": "/duels.html",
};

function originCleanUrls(): Plugin {
  const rewrite = (req: IncomingMessage) => {
    const raw = req.url?.split("?")[0] || "";
    const path = raw.length > 1 ? raw.replace(/\/$/, "") : raw;
    const dest = originRoutes[path] ?? (/^\/(circuits(?:\/[a-z0-9-]+)?|matches\/[a-z0-9-]+|agents\/[a-z0-9-]+\/[a-z0-9-]+|developers)$/.test(path) ? (process.env.NODE_ENV === "development" ? "/archive.html" : `${path}.html`) : undefined);
    if (dest) req.url = dest + (req.url?.includes("?") ? `?${req.url.split("?")[1]}` : "");
  };
  return {
    name: "origin-clean-urls",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        if (/^\/(circuits|matches|agents|developers)(?:\/|$)/.test(req.url?.split("?")[0] ?? "")) req.url = "/archive.html";
        else rewrite(req);
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

function publicPages(): Plugin {
  return {
    name: "prerender-public-evidence",
    enforce: "post",
    async generateBundle(_options, bundle) {
      const template = bundle["archive.html"];
      if (!template || template.type !== "asset") throw Error("Public archive template was not emitted.");
      const pages = JSON.parse(await readFile(resolve(root, "public/competition/page-routes.json"), "utf8")) as Array<{ path: string; title: string; description: string; ssr: string }>;
      const escape = (s: string) => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '\"': "&quot;", "'": "&#39;" })[c]!);
      for (const page of pages) {
        const url = `https://builderwars.com${page.path}`;
        const html = String(template.source).replace(/<title>[^<]*<\/title>/, `<title>${escape(page.title)}</title>`)
          .replace(/(<meta name="description" content=")[^"]*/, `$1${escape(page.description)}`)
          .replace(/(<meta property="og:title" content=")[^"]*/, `$1${escape(page.title)}`)
          .replace(/(<meta property="og:description" content=")[^"]*/, `$1${escape(page.description)}`)
          .replace(/(<meta property="og:url" content=")[^"]*/, `$1${url}`)
          .replace(/(<link rel="canonical" href=")[^"]*/, `$1${url}`)
          .replace("<!--PUBLIC_CONTENT-->", page.ssr);
        this.emitFile({ type: "asset", fileName: `${page.path.slice(1)}.html`, source: html });
      }
    },
  };
}

// Packaged assets do not receive Vercel headers. No loopback exception or remote scripts.
export const nativeContentPolicy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https: wss:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'";
export default defineConfig(({ mode }) => ({
  worker: { format: "es" },
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
  }] : [originCleanUrls(), publicPages()],
}));
