import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL(".", import.meta.url));

async function read(name: string) {
  return readFile(path.join(root, name), "utf8");
}

const pages = ["about.html", "games.html", "verify.html", "guide.html"] as const;

test("origin pages name BuilderWars, Nymrel, and JalenBuilds LLC", async () => {
  for (const page of pages) {
    const html = await read(page);
    assert.match(html, /BuilderWars/);
    assert.match(html, /Nymrel/);
    assert.match(html, /JalenBuilds LLC/);
    assert.match(html, /contact@jalenbuilds.com/);
    assert.match(html, /parentOrganization/);
    assert.match(html, /canonical" href="https:\/\/builderwars.com\//);
    assert.match(html, /class="origin"/);
    assert.match(html, /href="\/"/);
  }
});

test("origin CSS uses the studio warm paper palette", async () => {
  const css = await read("origin.css");
  assert.match(css, /--paper:\s*#faf8f2/i);
  assert.match(css, /--linen:\s*#f4f0e6/i);
  assert.match(css, /--cedar:\s*#2a332e/i);
  assert.match(css, /--terracotta:\s*#a8541f/i);
});

test("Vite web build and Vercel routes admit the origin page family", async () => {
  const vite = await read("vite.config.ts");
  const vercel = await read("vercel.json");
  for (const page of pages) {
    assert.match(vite, new RegExp(page.replace(".", "\\.")));
    const route = page.replace(".html", "");
    assert.match(vercel, new RegExp(`"/${route}"`));
    assert.match(vercel, new RegExp(`"/${page}"`));
  }
  assert.match(vite, /mode === "native" \? \{\} : \{ input: webPages \}/);
});

test("guide and verify keep the honest product boundary", async () => {
  const guide = await read("guide.html");
  const verify = await read("verify.html");
  const games = await read("games.html");
  assert.match(guide, /will not proxy a consumer ChatGPT or Claude login/i);
  assert.match(verify, /model_attested/);
  assert.match(verify, /does not prove/i);
  assert.match(games, /Not on this website yet/);
  assert.match(games, /Nim and Ten Fronts/);
});
