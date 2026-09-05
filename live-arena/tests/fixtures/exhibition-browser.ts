/** Browser-fixture bridge. Synthetic only; no native client, engine or provider calls. */
import { exhibitionFixture } from "./exhibition";

const capped = await exhibitionFixture();
const failed = await exhibitionFixture([], 2, "failed");
const mate = await exhibitionFixture(["f2f3", "e7e5", "g2g4", "d8h4"], 1, "complete");
console.log(JSON.stringify({ capped, failed, mate }));
