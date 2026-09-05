import Peer, { type DataConnection } from "peerjs";
import { replay, type RecordData } from "./records";
export class Broadcast {
  constructor(private createPeer: () => Peer = () => new Peer()) {}
  peer: Peer | null = null;
  viewers = new Set<DataConnection>();
  timer: ReturnType<typeof setTimeout> | null = null;
  updateTimer: ReturnType<typeof setTimeout> | null = null;
  heartbeat: ReturnType<typeof setInterval> | null = null;
  cancelHost: (() => void) | null = null;
  record: RecordData | null = null;
  close() {
    const oldPeer = this.peer;
    this.peer = null;
    this.cancelHost?.();
    this.cancelHost = null;
    if (this.heartbeat) clearInterval(this.heartbeat);
    this.heartbeat = null;
    if (this.timer) clearTimeout(this.timer);
    if (this.updateTimer) clearTimeout(this.updateTimer);
    this.updateTimer = null;
    this.timer = null;
    this.viewers.forEach((c) => c.close());
    this.viewers.clear();
    oldPeer?.destroy();
  }
  publish(record: RecordData) {
    this.record = record;
    for (const c of this.viewers)
      if (c.open) c.send({ type: "snapshot", record });
  }
  async host(
    onCount: (n: number) => void,
    onError: (message: string) => void,
  ): Promise<string> {
    this.close();
    const peer = this.createPeer();
    this.peer = peer;
    this.heartbeat = setInterval(() => {
      for (const connection of this.viewers)
        if (connection.open) connection.send({ type: "heartbeat" });
    }, 5000);
    peer.on("connection", (c) => {
      if (this.peer !== peer) {
        c.close();
        return;
      }
      if (this.viewers.size >= 16) {
        c.close();
        return;
      }
      this.viewers.add(c);
      let lastResync = 0;
      c.on("data", (data) => {
        if (
          (data as { type?: unknown })?.type !== "resync" ||
          this.peer !== peer ||
          !c.open ||
          Date.now() - lastResync < 5000
        )
          return;
        lastResync = Date.now();
        if (this.record) c.send({ type: "snapshot", record: this.record });
      });
      c.on("open", () => {
        if (this.peer !== peer) return;
        onCount(this.viewers.size);
        if (this.record) c.send({ type: "snapshot", record: this.record });
      });
      c.on("close", () => {
        if (this.peer !== peer) return;
        this.viewers.delete(c);
        onCount(this.viewers.size);
      });
      c.on("error", () => {
        if (this.peer !== peer) return;
        this.viewers.delete(c);
        onCount(this.viewers.size);
      });
    });
    return await new Promise((resolve, reject) => {
      this.cancelHost = () => reject(Error("Broadcast cancelled."));
      this.timer = setTimeout(() => {
        this.cancelHost = null;
        this.close();
        reject(
          Error("Broadcast connection timed out. Retry on another network."),
        );
      }, 20000);
      peer.once("open", (id) => {
        if (this.peer !== peer) return;
        if (this.timer) clearTimeout(this.timer);
        this.timer = null;
        this.cancelHost = null;
        resolve(id);
      });
      peer.on("error", (e) => {
        if (this.peer !== peer) return;
        if (this.timer) clearTimeout(this.timer);
        this.timer = null;
        this.cancelHost = null;
        onError("Live connection interrupted. Replays remain available.");
        reject(Error(e.type));
      });
    });
  }
  async watch(
    id: string,
    onRecord: (r: ReturnType<typeof replay>) => void,
    onStatus: (message: string) => void,
    onUnavailable: () => void = () => {},
  ) {
    this.close();
    if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id))
      throw Error("Invalid broadcast id.");
    const peer = this.createPeer();
    this.peer = peer;
    const current = () => this.peer === peer;
    let hasRecord = false,
      offline = false;
    let latest: unknown;
    let channelClosed = false;
    const acceptLatest = () => {
      if (!current()) return;
      const msg = latest as { type?: unknown; record?: unknown };
      latest = undefined;
      try {
        if (msg?.type === "snapshot") {
          onRecord(replay(msg.record));
          hasRecord = true;
          offline = false;
          alive();
        }
      } catch {
        onStatus("Invalid broadcast update rejected.");
      }
    };
    const unavailable = () => {
      if (!current()) return;
      if (this.updateTimer) clearTimeout(this.updateTimer);
      this.updateTimer = null;
      // Preserve the final received board, then mark it offline in the same turn.
      // A queued coalesced snapshot must not later resurrect the Live label.
      acceptLatest();
      if (this.timer) clearTimeout(this.timer);
      this.timer = null;
      offline = true;
      onUnavailable();
    };
    const alive = () => {
      if (this.timer) clearTimeout(this.timer);
      this.timer = setTimeout(unavailable, 15000);
    };
    peer.on("open", () => {
      if (!current()) return;
      const c = peer.connect(id, { reliable: true });
      this.viewers.add(c);
      c.on("open", () => {
        if (current()) onStatus("Connected · waiting for a verified board");
      });
      c.on("data", (data) => {
        if (!current() || channelClosed) return;
        if ((data as { type?: unknown })?.type === "heartbeat") {
          if (hasRecord) {
            alive();
            if (offline) c.send({ type: "resync" });
          }
          return;
        }
        latest = data;
        if (this.updateTimer) return;
        this.updateTimer = setTimeout(() => {
          this.updateTimer = null;
          acceptLatest();
        }, 100);
      });
      c.on("close", () => {
        channelClosed = true;
        unavailable();
      });
      c.on("error", () => {
        channelClosed = true;
        unavailable();
      });
    });
    peer.on("error", () => {
      channelClosed = true;
      unavailable();
    });
    this.timer = setTimeout(unavailable, 20000);
  }
}
