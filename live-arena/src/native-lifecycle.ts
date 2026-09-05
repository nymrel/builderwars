/** Narrow, injectable native event boundary. Never resumes execution automatically. */
export type ListenerHandle = { remove(): Promise<void> };
export type NativeAppEvents = {
  addListener(event: "pause", listener: () => void): Promise<ListenerHandle>;
  addListener(event: "appStateChange", listener: (state: { isActive: boolean }) => void): Promise<ListenerHandle>;
  getState(): Promise<{ isActive: boolean }>;
};
export async function bindNativeLifecycle(
  app: NativeAppEvents,
  onSuspend: () => void,
  onForeground: () => void,
): Promise<() => Promise<void>> {
  const handles: ListenerHandle[] = [];
  let inactive = false, disposed = false, events = 0;
  function update(active: boolean) {
    if (disposed) return;
    events++;
    if (!active && !inactive) { inactive = true; onSuspend(); }
    else if (active && inactive) { inactive = false; onForeground(); }
  }
  async function dispose() {
    disposed = true;
    await Promise.allSettled(handles.map(handle => handle.remove()));
  }
  try {
    handles.push(await app.addListener("pause", () => update(false)));
    handles.push(await app.addListener("appStateChange", state => update(state.isActive)));
    const state = await app.getState();
    // Prefer any observed event, including events during listener registration.
    // Android may still report active between onPause and onStop.
    if (events === 0) update(state.isActive);
    return dispose;
  } catch (error) {
    await dispose();
    throw error;
  }
}

export function validateNativeEndpoint(kind: string, endpoint: string, native: boolean) {
  if (!native || kind !== "harness") return;
  const url = new URL(endpoint);
  const host = url.hostname.toLowerCase().replace(/\.+$/, "").replace(/^\[|\]$/g, "");
  const loopback = ["localhost", "::1", "::", "0.0.0.0"].includes(host) || host.endsWith(".localhost") ||
    /^127\./.test(host) || /^::(?:ffff:)?7f[0-9a-f]{2}:[0-9a-f]{1,4}$/.test(host);
  if (url.protocol !== "https:" || loopback)
    throw Error("On phones, use an HTTPS harness on another host. The desktop localhost bridge is not available in this app.");
}
