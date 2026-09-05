import { defineConfig } from "vite";
// Packaged assets do not receive Vercel headers. No loopback exception or remote scripts.
export const nativeContentPolicy = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https: wss:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'";
export default defineConfig(({ mode }) => ({
  build: { target: "es2022", outDir: mode === "native" ? "dist-native" : "dist" },
  plugins: mode === "native" ? [{
    name: "native-content-policy",
    transformIndexHtml: { order: "pre", handler: () => [
      { tag: "meta", attrs: { "http-equiv": "Content-Security-Policy", content: nativeContentPolicy }, injectTo: "head-prepend" },
      { tag: "meta", attrs: { name: "referrer", content: "no-referrer" }, injectTo: "head-prepend" },
    ] },
  }] : [],
}));
