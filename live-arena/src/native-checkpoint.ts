/** Single-writer native checkpoint protocol. Acknowledgement follows file promotion,
 * never a WebView localStorage write. Not a power-loss/fsync or multi-writer claim.
 * Integration must await save before displaying a successful save acknowledgement.
 */
export type CheckpointValues = Record<string, string>;
export type CheckpointFile = { name: string; type: string; size: number };
export type CheckpointPort = {
  list(): Promise<CheckpointFile[]>;
  read(name: string): Promise<string>;
  write(name: string, text: string): Promise<void>;
  promote(from: string, to: string): Promise<void>;
  remove(name: string): Promise<void>;
};
const SCHEMA = "builderwars.native-checkpoint.v1";
export const CHECKPOINT_DIRECTORY = "builderwars-checkpoints-v1";
export const CHECKPOINT_MAX_BYTES = 6_000_000;
const pattern = /^checkpoint-([1-9][0-9]{0,15})-([a-f0-9-]{36})\.json$/;
const partPattern = /^checkpoint-([1-9][0-9]{0,15})-[a-f0-9-]{36}\.json\.part$/;
const ownedKey = (key: string) => key === "builderwars.match.opt-out" ||
  key === "builderwars.practice-memory.v1" ||
  (key.startsWith("builderwars.match.v1:") && key.length <= 512);
const bytes = (text: string) => new TextEncoder().encode(text).byteLength;
async function digest(text: string) {
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)))].map(x => x.toString(16).padStart(2, "0")).join("");
}
const signed = (revision: number, purgeBefore: number, payload: string) => JSON.stringify([SCHEMA, revision, purgeBefore, payload]);
async function readEnvelope(text: string, revision: number) {
  if (bytes(text) > CHECKPOINT_MAX_BYTES) throw Error("Native checkpoint is oversized.");
  const raw = JSON.parse(text);
  if (!raw || raw.schema !== SCHEMA || raw.revision !== revision || typeof raw.payload !== "string" ||
      !Number.isSafeInteger(raw.purgeBefore) || raw.purgeBefore < 0 || raw.purgeBefore > revision ||
      raw.digest !== await digest(signed(revision, raw.purgeBefore, raw.payload)))
    throw Error("Native checkpoint failed integrity validation.");
  return { values: validate(JSON.parse(raw.payload)), purgeBefore: raw.purgeBefore, payload: raw.payload };
}
function validate(values: unknown): CheckpointValues {
  if (!values || typeof values !== "object" || Array.isArray(values)) throw Error("Invalid native checkpoint values.");
  const entries = Object.entries(values);
  if (entries.length > 22 || entries.some(([key, value]) => !ownedKey(key) || typeof value !== "string" || value.length > (key === "builderwars.practice-memory.v1" ? 256000 : 355000)))
    throw Error("Native checkpoint exceeds the permitted storage scope.");
  return Object.fromEntries(entries.sort(([a], [b]) => a.localeCompare(b)));
}
function inventory(files: CheckpointFile[]) {
  const found = files.flatMap(file => {
    const match = pattern.exec(file.name);
    if (!match) return [];
    const revision = Number(match[1]);
    if (!Number.isSafeInteger(revision) || file.type !== "file" || !Number.isFinite(file.size) || file.size < 0 || file.size > CHECKPOINT_MAX_BYTES)
      throw Error("Invalid native checkpoint file. Existing data was not changed.");
    return [{ ...file, revision }];
  }).sort((a, b) => b.revision - a.revision);
  if (found.length > 128 || found.some((file, i) => i > 0 && file.revision === found[i - 1].revision))
    throw Error("Ambiguous native checkpoint history. Existing data was not changed.");
  return found;
}

export class NativeCheckpoint {
  private tail: Promise<unknown> = Promise.resolve();
  private revision = 0;
  private values: CheckpointValues = {};
  private present = false;
  private purgeBefore = 0;
  private queued = 0;
  private failures = 0;
  private constructor(private port: CheckpointPort) {}
  static async open(port: CheckpointPort) {
    const store = new NativeCheckpoint(port);
    const latest = inventory(await port.list())[0];
    if (latest) {
      const raw = await readEnvelope(await port.read(latest.name), latest.revision);
      store.values = raw.values;
      store.purgeBefore = raw.purgeBefore;
      store.revision = latest.revision;
      store.present = true;
      // Never fall back from a corrupt committed file: it could resurrect forgotten
      // matches or opt-out state. Unpromoted .part files are ignored instead.
    }
    store.failures = await store.prune();
    return store;
  }
  get hasCheckpoint() { return this.present; }
  get cleanupFailures() { return this.failures; }
  snapshot(): CheckpointValues { return { ...this.values }; }
  private async prune() {
    let failures = 0;
    try {
      const files = await this.port.list();
      const older = inventory(files).filter(file => file.revision < this.revision);
      const remove = new Set(older.filter((file, i) => i > 0 || file.revision < this.purgeBefore).map(file => file.name));
      for (const file of files) {
        const part = partPattern.exec(file.name);
        if (part && file.type === "file" && Number(part[1]) <= this.revision) remove.add(file.name);
      }
      for (const name of remove) {
        try { await this.port.remove(name); } catch { failures++; }
      }
    } catch { failures++; }
    return failures;
  }
  async save(values: CheckpointValues): Promise<{ revision: number; cleanupFailures: number }> {
    // Capture at submission, not after a caller may have changed its live record.
    if (this.queued >= 16) throw Error("Native checkpoint queue is full. Await pending saves before retrying.");
    const copy = validate(values);
    this.queued++;
    const pending = this.tail.catch(() => {}).then(async () => {
      if (this.revision >= Number.MAX_SAFE_INTEGER) throw Error("Native checkpoint revision exhausted.");
      const revision = ++this.revision;
      // Persist the erasure boundary so failed cleanup is retried after restart.
      // A removed key must not remain in the ordinary previous-generation backup.
      const removesData = Object.keys(this.values).some(key => !(key in copy));
      const purgeBefore = removesData ? revision : this.purgeBefore;
      const payload = JSON.stringify(copy);
      const text = JSON.stringify({ schema: SCHEMA, revision, purgeBefore, payload, digest: await digest(signed(revision, purgeBefore, payload)) });
      if (bytes(text) > CHECKPOINT_MAX_BYTES) throw Error("Native checkpoint is oversized.");
      const name = `checkpoint-${revision}-${crypto.randomUUID()}.json`;
      const temporary = `${name}.part`;
      try {
        await this.port.write(temporary, text);
        // Check the complete file before promoting it. Partial writes never replace
        // the previous committed checkpoint. Destination is fresh, in the same folder.
        const stored = await readEnvelope(await this.port.read(temporary), revision);
        if (stored.payload !== payload || stored.purgeBefore !== purgeBefore) throw Error("Native checkpoint write did not round-trip.");
        await this.port.promote(temporary, name);
      } catch (error) {
        try { await this.port.remove(temporary); } catch { /* Exact temporary file only. */ }
        throw error;
      }
      this.values = copy;
      this.present = true;
      this.purgeBefore = purgeBefore;
      this.failures = await this.prune();
      return { revision, cleanupFailures: this.failures };
    }).finally(() => { this.queued--; });
    this.tail = pending;
    // Callers still observe rejection; a missed caller cannot cause an unhandled
    // background rejection or prevent the next explicit retry.
    void pending.catch(() => {});
    return pending;
  }
}
