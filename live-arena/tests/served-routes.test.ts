import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import test from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));

type Rewrite = {
  source: string;
  destination: string;
};

type VercelConfig = {
  rewrites?: Rewrite[];
};

async function loadConfig(): Promise<VercelConfig> {
  return JSON.parse(await readFile(path.join(root, "vercel.json"), "utf8")) as VercelConfig;
}

async function serveLikeVercel(t: test.TestContext) {
  const config = await loadConfig();
  const rewrites = config.rewrites ?? [];

  const server = createServer(async (req, res) => {
    const pathname = new URL(req.url ?? "/", "http://127.0.0.1").pathname;
    const destination = pathname === "/"
      ? "/index.html"
      : rewrites.find((rewrite) => rewrite.source === pathname)?.destination;

    if (!destination) {
      res.statusCode = 404;
      res.end("Not Found");
      return;
    }

    try {
      const body = await readFile(path.join(root, destination.slice(1)));
      res.statusCode = 200;
      res.end(body);
    } catch {
      res.statusCode = 404;
      res.end("Not Found");
    }
  });

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise<void>((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  }));

  const address = server.address();
  assert.ok(address && typeof address === "object");
  return `http://127.0.0.1:${address.port}`;
}

test("Vercel routing has no non-asset SPA catch-all", async () => {
  const config = await loadConfig();
  const rewrites = config.rewrites ?? [];
  assert.equal(
    rewrites.some((rewrite) => rewrite.destination === "/index.html" && rewrite.source !== "/"),
    false,
  );
});

test("served public routes stay 200 while unknown clean paths are 404", async (t) => {
  const base = await serveLikeVercel(t);

  for (const pathname of ["/", "/guide", "/games", "/verify"]) {
    const response = await fetch(`${base}${pathname}`);
    assert.equal(response.status, 200, pathname);
  }

  for (const pathname of ["/__bw57_missing_20261007__", "/__bw57_missing_20261007__/"]) {
    const response = await fetch(`${base}${pathname}`);
    assert.equal(response.status, 404, pathname);
  }
});

test("hash Arena entry points continue to load the root document", async (t) => {
  const base = await serveLikeVercel(t);

  for (const fragment of ["#watch", "#forge", "#replay=sample"]) {
    const response = await fetch(`${base}/${fragment}`);
    assert.equal(response.status, 200, fragment);
  }
});
