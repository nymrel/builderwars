import Peer, { type DataConnection } from "peerjs";
import { replay, type RecordData } from "./records";
export class Broadcast {
  peer: Peer | null = null;
  viewers = new Set<DataConnection>();
  timer: ReturnType<typeof setTimeout> | null = null;
  updateTimer: ReturnType<typeof setTimeout> | null = null;
  record: RecordData | null = null;
  close() {
    if (this.timer) clearTimeout(this.timer);
    if (this.updateTimer) clearTimeout(this.updateTimer);
    this.updateTimer = null;
    this.timer = null;
    this.viewers.forEach((c) => c.close());
    this.viewers.clear();
    this.peer?.destroy();
    this.peer = null;
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
    const peer = new Peer();
    this.peer = peer;
    peer.on("connection", (c) => {
      if (this.viewers.size >= 16) {
        c.close();
        return;
      }
      this.viewers.add(c);
      c.on("open", () => {
        onCount(this.viewers.size);
        if (this.record) c.send({ type: "snapshot", record: this.record });
      });
      c.on("close", () => {
        this.viewers.delete(c);
        onCount(this.viewers.size);
      });
      c.on("error", () => {
        this.viewers.delete(c);
        onCount(this.viewers.size);
      });
    });
    return await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.close();
        reject(
          Error("Broadcast connection timed out. Retry on another network."),
        );
      }, 20000);
      peer.once("open", (id) => {
        clearTimeout(timeout);
        resolve(id);
      });
      peer.on("error", (e) => {
        clearTimeout(timeout);
        onError("Live connection interrupted. Replays remain available.");
        reject(Error(e.type));
      });
    });
  }
  async watch(
    id: string,
    onRecord: (r: ReturnType<typeof replay>) => void,
    onStatus: (message: string) => void,
  ) {
    this.close();
    if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id))
      throw Error("Invalid broadcast id.");
    const peer = new Peer();
    this.peer = peer;
    let latest: unknown;
    peer.on("open", () => {
      const c = peer.connect(id, { reliable: true });
      this.viewers.add(c);
      c.on("open", () => onStatus("Watching live"));
      c.on("data", (data) => {
        latest = data;
        if (this.updateTimer) return;
        this.updateTimer = setTimeout(() => {
          this.updateTimer = null;
          try {
            const msg = latest as any;
            if (msg?.type === "snapshot") {
              onRecord(replay(msg.record));
              if (this.timer) clearTimeout(this.timer);
              this.timer = null;
            }
          } catch {
            onStatus("Invalid broadcast update rejected.");
          }
        }, 100);
      });
      c.on("close", () =>
        onStatus(
          "Host disconnected. The last received position is still available.",
        ),
      );
      c.on("error", () =>
        onStatus(
          "Unable to reach host. Ask them to keep the broadcast tab open.",
        ),
      );
    });
    peer.on("error", () =>
      onStatus(
        "Broadcast unavailable. The host may be offline or your network may block peer connections.",
      ),
    );
    this.timer = setTimeout(
      () =>
        onStatus(
          "If the board has not updated, the host may be offline or unreachable.",
        ),
      20000,
    ) as any;
  }
}
