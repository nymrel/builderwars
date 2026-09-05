import test from "node:test";
import assert from "node:assert/strict";
import { bindNativeLifecycle, validateNativeEndpoint, type NativeAppEvents } from "../src/native-lifecycle";
import config from "../capacitor.config";
import { nativeContentPolicy } from "../vite.config";

function fakeApp() {
  const listeners = new Map<string, (value?: any) => void>();
  let removed = 0;
  const app = {
    async addListener(event: string, listener: (value?: any) => void) {
      listeners.set(event, listener);
      return { async remove() { listeners.delete(event); removed++; } };
    },
    async getState() { return { isActive: true }; },
  };
  return { app: app as NativeAppEvents, emit: (event: string, value?: unknown) => listeners.get(event)?.(value), removed: () => removed };
}
test("native pause is idempotent and foreground never invokes a start callback", async () => {
  const fake = fakeApp(); let pauses = 0, foregrounds = 0;
  const dispose = await bindNativeLifecycle(fake.app, () => pauses++, () => foregrounds++);
  fake.emit("pause"); fake.emit("appStateChange", { isActive: false });
  assert.equal(pauses, 1);
  fake.emit("appStateChange", { isActive: true });
  assert.equal(foregrounds, 1);
  fake.emit("pause"); assert.equal(pauses, 2);
  await dispose();
  assert.equal(fake.removed(), 2);
  fake.emit("pause"); assert.equal(pauses, 2);
});
test("late initial active snapshot cannot undo a newer pause", async () => {
  const fake = fakeApp(); let pauses = 0, foregrounds = 0;
  fake.app.getState = async () => { fake.emit("pause"); return { isActive: true }; };
  await bindNativeLifecycle(fake.app, () => pauses++, () => foregrounds++);
  assert.equal(pauses, 1); assert.equal(foregrounds, 0);
});
test("failed native initialization removes only owned listeners", async () => {
  const fake = fakeApp();
  fake.app.getState = async () => { throw Error("unavailable"); };
  await assert.rejects(bindNativeLifecycle(fake.app, () => {}, () => {}), /unavailable/);
  assert.equal(fake.removed(), 2);
});
test("a pause during listener registration wins over Android's still-active snapshot", async () => {
  const fake = fakeApp(); const calls: string[] = [];
  const original = fake.app.addListener.bind(fake.app);
  fake.app.addListener = async (event: any, callback: any) => {
    const handle = await original(event, callback);
    if (event === "appStateChange") fake.emit("pause");
    return handle;
  };
  await bindNativeLifecycle(fake.app, () => calls.push("suspend"), () => calls.push("foreground"));
  assert.deepEqual(calls, ["suspend"]);
});
test("native phones reject desktop loopback routes; browser route is preserved", () => {
  for (const url of ["http://127.0.0.1:8765/move", "https://127.0.0.1/move", "https://127.0.0.2/move", "https://127.255.255.254/move", "https://localhost./move", "https://a.localhost./move", "https://[::ffff:127.0.0.1]/move", "https://localhost/move", "https://a.localhost/move", "https://[::1]/move", "https://0.0.0.0/move"])
    assert.throws(() => validateNativeEndpoint("harness", url, true), /phones/);
  assert.doesNotThrow(() => validateNativeEndpoint("harness", "https://harness.example/move", true));
  assert.doesNotThrow(() => validateNativeEndpoint("harness", "http://127.0.0.1:8765/move", false));
});
test("packaged build has no remote shell, mixed content, fetch patch or debug WebView", () => {
  assert.equal(config.webDir, "dist-native");
  assert.equal(config.server?.url, undefined);
  assert.equal(config.server?.allowNavigation, undefined);
  assert.equal(config.server?.cleartext, false);
  assert.equal(config.android?.allowMixedContent, false);
  assert.equal(config.android?.webContentsDebuggingEnabled, false);
  assert.equal(config.ios?.webContentsDebuggingEnabled, false);
  assert.equal(config.plugins?.CapacitorHttp?.enabled, false);
  assert.equal(config.plugins?.CapacitorCookies?.enabled, false);
  assert.match(nativeContentPolicy, /script-src 'self';/);
  assert.doesNotMatch(nativeContentPolicy, /127\.0\.0\.1|unsafe-eval|script-src[^;]*https/);
});
