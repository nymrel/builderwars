import manifest from "./referee-manifest";
type Referee = typeof import("./referee");
type RefereeGlobal = typeof globalThis & { __builderwarsReferee?: Referee };
async function load(): Promise<Referee> {
  if (typeof document === "undefined") {
    const base = new URL(/* @vite-ignore */ "../public/", import.meta.url);
    return import(/* @vite-ignore */ new URL(manifest.file, base).href);
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.type = "module";
    script.src = `/${manifest.file}`;
    script.integrity = manifest.integrity;
    script.crossOrigin = "anonymous";
    script.onload = () => {
      const core = (globalThis as RefereeGlobal).__builderwarsReferee;
      delete (globalThis as RefereeGlobal).__builderwarsReferee;
      if (core) resolve(core);
      else reject(Error("Referee module did not initialize."));
    };
    script.onerror = () => reject(Error("Could not load the verified game engine. Reload to try again."));
    document.head.append(script);
  });
}
const core = await load().catch(error => {
  if (typeof document !== "undefined") {
    const app = document.getElementById("app");
    if (app) app.textContent = "BuilderWars could not load its verified game engine. Check your connection and reload. No match or model request has started.";
  }
  throw error;
});
export const refereeManifest = manifest;
export const { RULES, createGame, applyMove, legalMoves, moveLabel, square, validateRules,
  botMove, gamePrompt, replayStepper, replay, encodeReplay, decodeReplay, download,
  canonical, sha256, createProof, verifyProof, parseProof, PROOF_LIMIT, PROOF_PROTOCOL } = core;
export type { Rules, GameState, GameKind } from "./games";
export type { RecordData, Event } from "./records";
