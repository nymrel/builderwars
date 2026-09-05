/** Packaged WebView origins are local assets, never recipient-facing URLs. */
export function publicLinkOrigin(origin: string): string {
  if (["capacitor://localhost", "https://localhost", "http://localhost"].includes(origin))
    return "https://builderwars.com";
  const url = new URL(origin);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password ||
      url.search || url.hash || url.pathname !== "/")
    throw Error("A public link needs a supported website origin.");
  return url.origin;
}
