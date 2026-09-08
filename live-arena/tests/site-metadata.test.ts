import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

const html = readFileSync(join(root, "index.html"), "utf8");

function meta(attr: "name" | "property", key: string): string | null {
  const re = new RegExp(`<meta ${attr}="${key}" content="([^"]*)"`);
  const m = html.match(re);
  return m ? m[1] : null;
}

function jsonLdBlocks(): unknown[] {
  const out: unknown[] = [];
  const re = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g;
  for (const m of html.matchAll(re)) out.push(JSON.parse(m[1]!));
  return out;
}

const ORIGIN = "https://builderwars.com";

test("index.html ships a JSON-LD graph with website, app and publisher entities", () => {
  const blocks = jsonLdBlocks();
  assert.equal(blocks.length, 1, "expected exactly one ld+json block");
  const graph = (blocks[0] as { "@graph": Record<string, unknown>[] })["@graph"];
  const byType = new Map<string, Record<string, unknown>>(
    graph.map(node => [node["@type"] as string, node])
  );

  const website = byType.get("WebSite")!;
  assert.equal(website.url, `${ORIGIN}/`);
  assert.equal(website.name, "BuilderWars");

  const app = byType.get("WebApplication")!;
  assert.equal(app.url, `${ORIGIN}/`);
  assert.equal(app.applicationCategory, "GameApplication");
  // Free product disclosure: an Offer with price 0.
  const offers = app.offers as { price: string; priceCurrency: string };
  assert.equal(offers.price, "0");
  assert.equal(offers.priceCurrency, "USD");

  // Entity graph: publisher chain resolves Nymrel -> JalenBuilds LLC.
  const org = byType.get("Organization")!;
  assert.equal(org.name, "Nymrel");
  assert.equal(org.url, "https://nymrel.com");
  const parent = org.parentOrganization as { name: string };
  assert.equal(parent.name, "JalenBuilds LLC");

  // @id references inside the graph must resolve to nodes in the same graph.
  const ids = new Set(graph.map(node => node["@id"]));
  for (const node of graph) {
    const pub = node.publisher as { "@id": string } | undefined;
    const ref = pub?.["@id"];
    if (ref) assert.ok(ids.has(ref), `dangling @id reference: ${ref}`);
  }
});

test("index.html social metadata points at a real og image", () => {
  const ogImage = meta("property", "og:image");
  assert.equal(ogImage, `${ORIGIN}/og-image.png`);
  assert.equal(meta("property", "og:image:width"), "1200");
  assert.equal(meta("property", "og:image:height"), "630");
  assert.ok(meta("property", "og:image:alt"), "og:image:alt is required");
  assert.equal(meta("name", "twitter:card"), "summary_large_image");
  assert.equal(meta("name", "twitter:image"), ogImage);

  // The referenced asset must exist in public/ and be a 1200x630 PNG.
  const png = readFileSync(join(root, "public", "og-image.png"));
  assert.ok(png.length > 10_000, "og-image.png suspiciously small");
  assert.deepEqual([...png.slice(1, 4)], [0x50, 0x4e, 0x47], "not a PNG");
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  assert.equal(width, 1200);
  assert.equal(height, 630);
});

test("canonical, og:url and sitemap origin stay aligned", () => {
  const canonical = html.match(/<link rel="canonical" href="([^"]*)"/)?.[1];
  assert.equal(canonical, `${ORIGIN}/`);
  assert.equal(meta("property", "og:url"), `${ORIGIN}/`);
  const sitemap = readFileSync(join(root, "public", "sitemap.xml"), "utf8");
  assert.ok(sitemap.includes(`${ORIGIN}/`), "sitemap must keep the same origin");
  // The image URL must be same-origin so the CSP img-src 'self' rule keeps serving it.
  const ogImage = meta("property", "og:image")!;
  assert.ok(ogImage.startsWith(ORIGIN), "og:image must be same-origin");
});
