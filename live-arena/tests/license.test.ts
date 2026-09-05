import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

// Repository-scoped parity check; standalone app-root deployments run build only.
test("deployable app carries the unchanged root MIT license", async () => {
  const normalize = (text: string) => text.replaceAll("\r\n", "\n");
  const [app, root] = await Promise.all([
    readFile(new URL("../LICENSE", import.meta.url), "utf8"),
    readFile(new URL("../../LICENSE", import.meta.url), "utf8"),
  ]);
  assert.equal(normalize(app), normalize(root));
});
