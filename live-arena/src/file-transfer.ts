export const EXPORT_LIMITS = { profile: 8192, replay: 350000, rules: 350000, proof: 1500000, verifier: 1500000, image: 8 * 1024 * 1024, evaluation: 8 * 1024 * 1024 } as const;
export type ExportKind = keyof typeof EXPORT_LIMITS;
export const EXPORT_CACHE = "builderwars-exports";
export const CACHE_TTL = 24 * 60 * 60 * 1000;
export const CACHE_MAX_FILES = 32, CACHE_MAX_BYTES = 64 * 1024 * 1024;
export type TransferOutcome = "download-requested" | "sheet-closed" | "cancelled";
export type CacheEntry = { name: string; type: string; size: number; mtime: number };
export interface NativeFilePort {
  list(): Promise<CacheEntry[]>;
  write(name: string, base64: string): Promise<string>;
  remove(name: string): Promise<void>;
  share(value: { files?: string[]; text?: string }): Promise<"sheet-closed" | "cancelled">;
}
const safeName = /^[A-Za-z0-9][A-Za-z0-9._-]{0,149}\.(json|jsonl|mjs|png)$/;
const ownedName = /^\d{13}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-[A-Za-z0-9][A-Za-z0-9._-]{0,149}\.(json|jsonl|mjs|png)$/;
export function validExportName(name: string) { return safeName.test(name) && !name.includes(".."); }

/** Only prepared public bytes enter this service; never give it runtime credentials. */
export class FileTransfer {
  private busy = false;
  constructor(private options: {
    native?: () => Promise<NativeFilePort>;
    webDownload: (name: string, blob: Blob) => void;
    active?: () => boolean;
    epoch?: () => number;
    now?: () => number;
    id?: () => string;
  }) {}
  private assertActive() {
    if (this.options.active?.() === false) throw Error("Return to the app and try exporting again.");
  }
  preparationGuard() {
    const epoch = this.options.epoch?.();
    return () => {
      if (!this.options.native) return;
      this.assertActive();
      if (epoch !== this.options.epoch?.()) throw Error("The app was backgrounded during preparation. Export or share again.");
    };
  }
  private async room(port: NativeFilePort, size: number) {
    const entries = await port.list();
    if (entries.length > 200) throw Error("Export cache needs inspection before more files can be shared.");
    const now = this.options.now?.() ?? Date.now();
    let count = 0, bytes = 0;
    for (const entry of entries) {
      if (entry.type === "file" && ownedName.test(entry.name) && !entry.name.includes("..") &&
          Number.isFinite(entry.mtime) && entry.mtime >= 0 && now - entry.mtime >= CACHE_TTL) {
        try { await port.remove(entry.name); continue; }
        catch { /* Retain and count failed cleanup; never silently overrun the budget. */ }
      }
      count++;
      bytes += Number.isFinite(entry.size) && entry.size >= 0 ? entry.size : CACHE_MAX_BYTES;
    }
    if (count >= CACHE_MAX_FILES || bytes + size > CACHE_MAX_BYTES)
      throw Error("Export cache is temporarily full. Recent handoffs are retained for receiving apps; try again after 24 hours.");
  }
  async export(name: string, blob: Blob, kind: ExportKind): Promise<TransferOutcome> {
    if (!validExportName(name)) throw Error("Invalid export filename. Use a simple public filename without paths.");
    if (!EXPORT_LIMITS[kind] || blob.size > EXPORT_LIMITS[kind]) throw Error("Export exceeds this format's size limit.");
    if (this.busy) throw Error("Finish the current export or share sheet first.");
    this.busy = true;
    const check = this.preparationGuard();
    let port: NativeFilePort | undefined, cacheName = "", handedOff = false;
    try {
      if (!this.options.native) { this.options.webDownload(name, blob); return "download-requested"; }
      check();
      port = await this.options.native();
      await this.room(port, blob.size);
      check();
      cacheName = `${this.options.now?.() ?? Date.now()}-${this.options.id?.() ?? crypto.randomUUID()}-${name}`;
      if (!ownedName.test(cacheName) || cacheName.includes("..")) throw Error("Cannot create a safe export name.");
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 32768) binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
      const uri = await port.write(cacheName, btoa(binary));
      if (!uri.startsWith("file://")) throw Error("Native cache did not return a shareable file.");
      check();
      // Unknown share errors may follow a handoff. Do not erase its bytes prematurely.
      handedOff = true;
      const result = await port.share({ files: [uri] });
      if (result === "cancelled") { handedOff = false; }
      return result;
    } finally {
      if (port && cacheName && !handedOff) {
        try { await port.remove(cacheName); } catch { /* Age/budget cleanup retries later. */ }
      }
      this.busy = false;
    }
  }
  async shareText(text: string): Promise<TransferOutcome> {
    if (!this.options.native) throw Error("Native sharing is unavailable.");
    if (new TextEncoder().encode(text).length > 100000) throw Error("Shared text is too large.");
    if (this.busy) throw Error("Finish the current export or share sheet first.");
    this.busy = true;
    const check = this.preparationGuard();
    try {
      check();
      const port = await this.options.native();
      check();
      return await port.share({ text });
    } finally { this.busy = false; }
  }
}
export function webDownload(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function transferMessage(outcome: TransferOutcome) {
  return outcome === "download-requested" ? "Download requested. Check your browser downloads."
    : outcome === "cancelled" ? "Sharing cancelled. Nothing is confirmed saved or published."
      : "Share sheet closed. Check the chosen destination; saving or publication is not confirmed.";
}
export async function boundedResponse(response: Response, maximum: number): Promise<Blob> {
  if (!response.ok || !response.body) throw Error("The bundled export asset is unavailable.");
  const reader = response.body.getReader(), parts: Uint8Array<ArrayBuffer>[] = [];
  let size = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      size += part.value.byteLength;
      if (size > maximum) throw Error("Export asset exceeds its size limit.");
      parts.push(new Uint8Array(part.value));
    }
    return new Blob(parts, { type: "text/javascript" });
  } finally { try { await reader.cancel(); } finally { reader.releaseLock(); } }
}
