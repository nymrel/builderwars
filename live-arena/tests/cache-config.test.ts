import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

type HeaderRule = { source: string; headers: Array<{ key: string; value: string }> };

test("content-hashed Vite assets are browser-cacheable for one year", async () => {
  const config = JSON.parse(
    await readFile(new URL("../vercel.json", import.meta.url), "utf8"),
  ) as { headers: HeaderRule[] };
  const assets = config.headers.find((rule) => rule.source === "/assets/(.*)");
  assert.ok(assets, "vercel.json must define an /assets cache rule");
  const cache = assets.headers.find(
    (header) => header.key.toLowerCase() === "cache-control",
  );
  assert.equal(cache?.value, "public, max-age=31536000, immutable");
});
