// One rules/dependency closure is used by the browser and the portable verifier.
import * as games from "./games";
import * as records from "./records";
import * as proof from "./proof";
// The browser loads this exact module with script integrity under script-src self.
// No untrusted proof can supply executable code or choose the module URL.
(globalThis as typeof globalThis & { __builderwarsReferee?: unknown }).__builderwarsReferee = { ...games, ...records, ...proof };
export * from "./games";
export * from "./records";
export * from "./proof";
