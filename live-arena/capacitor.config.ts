import type { CapacitorConfig } from "@capacitor/cli";

// Local development identifier only: no store registration or signing is implied.
const config: CapacitorConfig = {
  appId: "com.nymrel.builderwars",
  appName: "BuilderWars",
  webDir: "dist-native",
  server: { hostname: "localhost", androidScheme: "https", cleartext: false },
  android: { allowMixedContent: false, webContentsDebuggingEnabled: false },
  ios: { webContentsDebuggingEnabled: false },
  plugins: { CapacitorHttp: { enabled: false }, CapacitorCookies: { enabled: false } },
};
export default config;
