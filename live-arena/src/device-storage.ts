import { NativeCheckpoint, validCheckpointEntry, type CheckpointPort, type CheckpointValues } from "./native-checkpoint";
import { MatchLibrary, LIBRARY_PREFIX, LIBRARY_OPT_OUT } from "./library";
import { PracticeMemory, MEMORY_KEY } from "./learning";

type StoragePort = Pick<Storage, "length" | "key" | "getItem" | "setItem" | "removeItem">;
const owned = (key: string) => key === LIBRARY_OPT_OUT || key === MEMORY_KEY || key.startsWith(LIBRARY_PREFIX);

/** Synchronous consumer view, explicitly asynchronous durability. One instance per
 * native process. Never substitute WebView storage after a failed native open. */
export class DeviceStorage implements StoragePort {
  private version = 0;
  private savedVersion = 0;
  private erasure = false;
  private draining: Promise<void> | undefined;
  private legacyDeletes = new Set<string>();
  private failed = false;
  private constructor(private checkpoint: NativeCheckpoint, private values: CheckpointValues, private legacy: StoragePort) {}
  static async open(port: CheckpointPort, legacy: StoragePort) {
    const checkpoint = await NativeCheckpoint.open(port);
    if (!checkpoint.hasCheckpoint) {
      const values: CheckpointValues = {};
      // Migrate validated public records only, preserving their retention dates.
      // Legacy copies remain until an explicit deletion; invalid data is not erased.
      for (const { key, ...entry } of new MatchLibrary(legacy).list()) values[key] = JSON.stringify(entry);
      if (legacy.getItem(LIBRARY_OPT_OUT) === "1") values[LIBRARY_OPT_OUT] = "1";
      const memory = new PracticeMemory(legacy).snapshot();
      if (memory.episodes.length) values[MEMORY_KEY] = JSON.stringify(memory);
      await checkpoint.save(values); // Empty is an authoritative migration marker too.
    }
    return new DeviceStorage(checkpoint, checkpoint.snapshot(), legacy);
  }
  get length() { return Object.keys(this.values).length; }
  key(index: number) { return Object.keys(this.values)[index] ?? null; }
  getItem(key: string) { return this.values[key] ?? null; }
  setItem(key: string, value: string) {
    if (!validCheckpointEntry(key, value)) throw Error("Storage entry exceeds BuilderWars device limits.");
    if (this.values[key] !== value) { this.values[key] = value; this.version++; }
  }
  removeItem(key: string) {
    if (!owned(key)) throw Error("Storage key is outside BuilderWars device data.");
    delete this.values[key];
    this.version++;
    this.erasure = true; // Preserve clear-then-readd even when saves coalesce.
    this.legacyDeletes.add(key);
  }
  forgetLegacyMatches() {
    for (let i = 0; i < this.legacy.length; i++) {
      const key = this.legacy.key(i);
      if (key?.startsWith(LIBRARY_PREFIX)) this.legacyDeletes.add(key);
    }
  }
  get status(): "saved" | "saving" | "unavailable" | "cleanup-pending" {
    if (this.failed) return "unavailable";
    if (this.draining || this.version !== this.savedVersion) return "saving";
    if (this.checkpoint.cleanupFailures || this.legacyDeletes.size) return "cleanup-pending";
    return "saved";
  }
  flush(): Promise<void> {
    const requestedVersion = this.version;
    if (!this.draining) this.draining = this.drain().finally(() => { this.draining = undefined; });
    // A caller can arrive after drain's last check but before its finally runs.
    // Cover this caller's version, not merely the previously scheduled drain.
    const acknowledged = this.draining.then(() => this.savedVersion < requestedVersion ? this.flush() : undefined);
    // No automatic retry loop on disk failure. A later explicit save may retry.
    void acknowledged.catch(() => {});
    return acknowledged;
  }
  private async drain() {
    this.failed = false;
    try {
      do {
        const version = this.version, erasePrior = this.erasure;
        this.erasure = false;
        try { await this.checkpoint.save({ ...this.values }, erasePrior); }
        catch (error) { this.erasure ||= erasePrior; throw error; }
        this.savedVersion = version;
        // Only explicitly forgotten keys. Never clear unrelated or invalid legacy
        // records during migration, and never claim erasure when cleanup failed.
        for (const key of this.legacyDeletes) {
          try { this.legacy.removeItem(key); this.legacyDeletes.delete(key); }
          catch { /* Visible cleanup-pending; retry on the next explicit save. */ }
        }
      } while (this.version !== this.savedVersion);
    } catch (error) { this.failed = true; throw error; }
  }
}
