import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { Broadcast } from "../src/broadcast";
import { RULES } from "../src/games";
class Connection extends EventEmitter {
  open = true;
  send() {}
  close() {
    this.open = false;
    this.emit("close");
  }
}
class FakePeer extends EventEmitter {
  connection = new Connection();
  connect() {
    return this.connection;
  }
  destroy() {
    this.connection.close();
  }
}
const snapshot = {
  type: "snapshot",
  record: {
    schema: "builderwars.exhibition.v1",
    id: "test",
    createdAt: "2026-09-04",
    rules: RULES.tictactoe,
    agents: [0, 1].map((i) => ({
      name: `Bot ${i}`,
      kind: "bot",
      model: "random",
      effort: "default",
      strategy: "",
    })),
    events: [
      {
        ply: 1,
        seat: 0,
        move: "0",
        label: "A1",
        elapsed: 1,
        tokens: null,
        cost: 0,
        model: "random",
        comment: "",
      },
    ],
    status: "Playing",
  },
};
test("disconnect flushes the final snapshot before offline and ignores late updates", async () => {
  const peer = new FakePeer();
  const broadcast = new Broadcast(() => peer as any);
  const events: string[] = [];
  try {
    await broadcast.watch(
      "test-peer",
      () => events.push("live"),
      () => {},
      () => events.push("offline"),
    );
    peer.emit("open");
    peer.connection.emit("data", snapshot);
    peer.connection.close();
    assert.deepEqual(events, ["live", "offline"]);
    peer.connection.emit("data", snapshot);
    await new Promise((resolve) => setTimeout(resolve, 150));
    assert.deepEqual(events, ["live", "offline"]);
    assert.equal(broadcast.timer, null);
    assert.equal(broadcast.updateTimer, null);
  } finally {
    broadcast.close();
  }
});
test("cancelling a pending host clears its timers and cannot close the next watcher", async () => {
  const peers: FakePeer[] = [];
  const broadcast = new Broadcast(() => {
    const peer = new FakePeer();
    peers.push(peer);
    return peer as any;
  });
  try {
    const hosted = broadcast.host(
      () => {},
      () => {},
    );
    const cancelled = assert.rejects(hosted, /cancelled/);
    await broadcast.watch(
      "test-peer",
      () => {},
      () => {},
    );
    await cancelled;
    assert.equal(broadcast.peer, peers[1]);
    assert.equal(broadcast.heartbeat, null);
    peers[0].emit("open", "old-host");
    assert.equal(broadcast.peer, peers[1]);
  } finally {
    broadcast.close();
  }
});
