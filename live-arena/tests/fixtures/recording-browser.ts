/** Synthetic browser inputs, generated with the actual pinned referee. */
import { RULES, replay, encodeReplay, createProof, refereeManifest, type RecordData } from "../../src/runtime";
import { makeMatchPackage, unknownDeclarations } from "../../src/match-package";
import { exhibitionFixture } from "./exhibition";
const record: RecordData = {
  schema: "builderwars.exhibition.v1", id: "synthetic-recording-transition", createdAt: "2026-10-05T00:00:00Z",
  rules: RULES.connect4, status: "Fixture",
  agents: [0, 1].map(i => ({ name: `Synthetic ${i}`, kind: "human", model: "human", effort: "default", strategy: "" })),
  events: ["0", "1", "0", "1", "0", "1", "0"].map((move, i) => ({ ply: i + 1, seat: (i % 2) as 0 | 1, move, label: "", comment: "", model: "human", elapsed: 0, tokens: null, cost: null })),
};
console.log(JSON.stringify({
  record: replay(record).record,
  package: makeMatchPackage(record, unknownDeclarations(), null),
  link: await encodeReplay(record),
  proof: await createProof(record, refereeManifest.digest, 80, "reverified_import"),
  exhibition: await exhibitionFixture(),
}));
