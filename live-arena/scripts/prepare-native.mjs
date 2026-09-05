import { readFile, writeFile } from "node:fs/promises";

// Capacitor 8.4.3 on Windows emits OS separators into Swift string literals.
// Normalize only generated local package paths; do not rewrite native source generally.
const file = new URL("../ios/App/CapApp-SPM/Package.swift", import.meta.url);
const source = await readFile(file, "utf8");
const portable = source.replace(/path: "([^"\r\n]+)"/g, (_, value) => `path: "${value.replaceAll("\\", "/")}"`);
if (portable !== source) await writeFile(file, portable);
if (!portable.includes('path: "../../../node_modules/@capacitor/app"')) throw Error("Unexpected generated App package binding.");
for (const platform of ["android/app/src/main/assets/public", "ios/App/App/public"]) {
  const html = await readFile(new URL(`../${platform}/index.html`, import.meta.url), "utf8");
  if (!html.includes('http-equiv="Content-Security-Policy"') || html.includes("127.0.0.1:8765"))
    throw Error(`Missing packaged content policy: ${platform}`);
}
console.log("Native copied assets and portable Swift package paths checked. No native binary was built.");
