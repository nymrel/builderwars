import { replay, type RecordData } from "./runtime";

export const LIBRARY_PREFIX = "builderwars.match.v1:";
export const LIBRARY_OPT_OUT = "builderwars.match.opt-out";
export const MAX_SAVED = 20;
export const MAX_LIBRARY_BYTES = 2_000_000;
export const RETENTION_MS = 30 * 24 * 60 * 60 * 1000;
export type SavedMatch = {
  record: RecordData;
  savedAt: number;
  source: "own" | "replay" | "watch";
  watchId: string;
  moveLimit: number;
  key: string;
};
type StorageLike = Pick<
  Storage,
  "length" | "key" | "getItem" | "setItem" | "removeItem"
>;
const validWatchId = (id: string) => /^[a-zA-Z0-9_-]{1,100}$/.test(id);
const completed = new WeakMap<RecordData, boolean>();

/** Only validated public evidence is retained. Never pass runtime Agent settings. */
export class MatchLibrary {
  private cache = new Map<string, { text: string; entry: SavedMatch }>();
  constructor(
    private storage: StorageLike,
    private now = () => Date.now(),
  ) {}
  enabled() {
    return this.storage.getItem(LIBRARY_OPT_OUT) !== "1";
  }
  keys() {
    return Array.from({ length: this.storage.length }, (_, i) =>
      this.storage.key(i),
    ).filter((key): key is string => !!key?.startsWith(LIBRARY_PREFIX));
  }
  list(): SavedMatch[] {
    const entries: SavedMatch[] = [];
    const keys = new Set(this.keys());
    for (const key of this.cache.keys())
      if (!keys.has(key)) this.cache.delete(key);
    for (const key of keys) {
      try {
        const text = this.storage.getItem(key);
        if (!text || text.length > 355000) continue;
        const cached = this.cache.get(key);
        if (
          cached?.text === text &&
          this.now() - cached.entry.savedAt <= RETENTION_MS
        ) {
          entries.push(cached.entry);
          continue;
        }
        const raw = JSON.parse(text);
        if (
          !Number.isFinite(raw.savedAt) ||
          this.now() - raw.savedAt > RETENTION_MS
        )
          continue;
        if (
          !["own", "replay", "watch"].includes(raw.source) ||
          !Number.isInteger(raw.moveLimit) ||
          raw.moveLimit < 2 ||
          raw.moveLimit > 400 ||
          typeof raw.watchId !== "string" ||
          (raw.watchId && !validWatchId(raw.watchId))
        )
          continue;
        const { record, state } = replay(raw.record);
        if (key !== this.entryKey(raw.source, record.id)) continue;
        const entry = {
          key,
          record,
          savedAt: raw.savedAt,
          source: raw.source,
          watchId: raw.watchId,
          moveLimit: raw.moveLimit,
        };
        completed.set(record, state.over);
        this.cache.set(key, { text, entry });
        entries.push(entry);
      } catch {
        /* An invalid entry cannot prevent other matches from opening. */
      }
    }
    return entries
      .sort(
        (a, b) =>
          Math.min(b.savedAt, this.now()) - Math.min(a.savedAt, this.now()),
      )
      .slice(0, MAX_SAVED);
  }
  private entryKey(source: string, id: string) {
    return `${LIBRARY_PREFIX}${source}:${encodeURIComponent(id)}`;
  }
  save(
    record: RecordData,
    source: SavedMatch["source"],
    moveLimit: number,
    watchId = "",
  ) {
    if (!this.enabled() || !record.events.length) return false;
    const parsed = replay(record);
    const clean = parsed.record;
    if (!Number.isInteger(moveLimit) || moveLimit < 2 || moveLimit > 400)
      throw Error("Invalid saved match limit.");
    if (watchId && !validWatchId(watchId))
      throw Error("Invalid saved broadcast.");
    const key = this.entryKey(source, clean.id);
    const envelope = {
      record: clean,
      savedAt: this.now(),
      source,
      moveLimit,
      watchId,
    };
    const value = JSON.stringify(envelope);
    // Envelope-only eviction: validation changes or clock corrections do not
    // silently delete old records. Unknown envelopes count against the same cap.
    const candidates = this.keys()
      .filter((old) => old !== key)
      .map((old) => {
        const text = this.storage.getItem(old) ?? "";
        let metadata: { source?: string; savedAt?: number } = {};
        try {
          metadata = JSON.parse(text);
        } catch {
          /* Keep bounded legacy data. */
        }
        return {
          key: old,
          bytes: text.length * 2,
          priority: ["replay", "watch"].includes(metadata?.source ?? "")
            ? 1
            : 0,
          time: Number.isFinite(metadata?.savedAt)
            ? Math.min(metadata.savedAt!, this.now())
            : 0,
          expired:
            Number.isFinite(metadata?.savedAt) &&
            this.now() - metadata.savedAt! > RETENTION_MS,
        };
      });
    candidates.push({
      key,
      bytes: value.length * 2,
      priority: source === "own" ? 0 : 1,
      time: this.now(),
      expired: false,
    });
    candidates.sort((a, b) => a.priority - b.priority || b.time - a.time);
    const keep = new Set<string>();
    let bytes = 0;
    for (const candidate of candidates) {
      if (
        !candidate.expired &&
        candidate.bytes <= 710000 &&
        keep.size < MAX_SAVED &&
        bytes + candidate.bytes <= MAX_LIBRARY_BYTES
      ) {
        keep.add(candidate.key);
        bytes += candidate.bytes;
      }
    }
    if (!keep.has(key)) return false;
    // Commit first. A failed quota/security write must never destroy older games.
    this.storage.setItem(key, value);
    for (const old of this.keys()) if (!keep.has(old)) this.remove(old);
    completed.set(clean, parsed.state.over);
    this.cache.set(key, { text: value, entry: { ...envelope, key } });
    return true;
  }
  remove(key: string) {
    if (!key.startsWith(LIBRARY_PREFIX)) throw Error("Invalid library key.");
    this.storage.removeItem(key);
    this.cache.delete(key);
  }
  forget() {
    // Disable first so subsequent moves cannot silently re-save deleted history.
    this.storage.setItem(LIBRARY_OPT_OUT, "1");
    for (const key of this.keys()) this.remove(key);
  }
  setEnabled(enabled: boolean) {
    this.storage.setItem(LIBRARY_OPT_OUT, enabled ? "0" : "1");
  }
}

export function canResume(saved: SavedMatch) {
  const over = completed.get(saved.record) ?? replay(saved.record).state.over;
  return (
    saved.source === "own" &&
    !over &&
    saved.record.events.length < saved.moveLimit &&
    saved.record.agents.every(
      (agent) =>
        agent.kind === "human" ||
        (agent.kind === "bot" && ["tactician", "random"].includes(agent.model)),
    )
  );
}
