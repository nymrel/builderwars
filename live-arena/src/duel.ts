import Peer, { type DataConnection } from "peerjs";
import { RULES, replay, canonical, moveLabel, type RecordData, type GameState } from "./runtime";
import { publicAgent, type Agent, type PublicAgent, type Decision } from "./models";
import { matchLimits } from "./resources";

export type DuelOffer = { game: string; moveLimit: number; maxTokens: number; agent: PublicAgent };
export type DuelView = { status: string; offer: DuelOffer | null; record: RecordData | null; seat: 0 | 1; ready: boolean; active: boolean };
type Choose = (state: GameState, agent: Agent, tokens: number, signal: AbortSignal) => Promise<Decision>;
// Only explicit public labels cross the connection. Prompts, keys and endpoints stay local.
export function duelAgent(agent: Agent): PublicAgent {
  return readAgent({ ...publicAgent(agent), strategy: "" });
}
function readAgent(raw: unknown): PublicAgent {
  const record = replay({ schema: "builderwars.exhibition.v1", id: "metadata", createdAt: "", rules: RULES.chess,
    agents: [raw, raw], events: [], status: "Ready" }).record;
  const agent = record.agents[0];
  if (agent.kind === "human" || agent.strategy !== "") throw Error("Choose an agent for this duel.");
  return agent;
}
export function readOffer(raw: unknown): DuelOffer {
  const offer = raw as DuelOffer;
  if (!offer || typeof offer.game !== "string" || !Object.hasOwn(RULES, offer.game)) throw Error("Unsupported duel game.");
  matchLimits(offer.moveLimit, offer.maxTokens);
  if (offer.maxTokens === null) throw Error("A duel needs a token limit.");
  return { game: offer.game, moveLimit: offer.moveLimit, maxTokens: offer.maxTokens, agent: readAgent(offer.agent) };
}
export function acceptDuelMove(previous: RecordData, raw: unknown, remoteSeat: number, limit: number): RecordData {
  const before = replay(previous);
  if (before.state.over || before.state.turn !== remoteSeat || previous.events.length >= limit) throw Error("Move is out of turn.");
  const next = replay(raw).record;
  if (next.id !== previous.id || next.createdAt !== previous.createdAt ||
      canonical(next.rules) !== canonical(previous.rules) || canonical(next.agents) !== canonical(previous.agents) ||
      next.events.length !== previous.events.length + 1 ||
      JSON.stringify(next.events.slice(0, -1)) !== JSON.stringify(before.record.events) || next.events.at(-1)!.comment !== "")
    throw Error("The duel history changed. No move accepted.");
  return next;
}

/** One invitation, one opponent, one bounded game. Closing requires a fresh invitation. */
export class DuelRoom {
  private peer: Peer | null = null;
  private connection: DataConnection | null = null;
  private controller: AbortController | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private lastSeen = 0;
  private cancelOpen: ((message: string) => void) | null = null;
  private local: Agent | null = null;
  private remote: PublicAgent | null = null;
  private localReady = false;
  private started = false;
  private busy = false;
  private generation = 0;
  private seat: 0 | 1 = 0;
  private offer: DuelOffer | null = null;
  private record: RecordData | null = null;
  private status = "Create an invitation or join a friend.";
  constructor(private choose: Choose, private changed: (view: DuelView) => void,
    private createPeer: () => Peer = () => new Peer()) {}

  view(): DuelView { return { status: this.status, offer: this.offer, record: this.record, seat: this.seat, ready: this.localReady, active: this.peer !== null }; }
  private update(status: string) { this.status = status; this.changed(this.view()); }
  close(message = "Duel ended. Create a new invitation to play again.") {
    const connection = this.connection, peer = this.peer;
    this.peer = null; this.connection = null; this.generation++;
    this.controller?.abort(); this.controller = null; this.busy = false;
    this.cancelOpen?.(message); this.cancelOpen = null;
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    if (connection?.open) connection.send({ type: "stop" });
    connection?.close(); peer?.destroy();
    this.local = null; this.localReady = false;
    if (this.record) {
      const state = replay(this.record).state;
      if (state.over) message = state.winner === null ? `Draw · ${state.reason}` : `${this.record.agents[state.winner].name} wins · ${state.reason}`;
      else if (this.record.events.length >= (this.offer?.moveLimit ?? 400)) message = "Move limit reached · no winner.";
      else this.record.status = "Duel stopped · incomplete";
    }
    this.update(message);
  }
  private async open(seat: 0 | 1) {
    this.close(); this.seat = seat; this.offer = null; this.record = null; this.remote = null; this.started = false;
    const peer = this.createPeer(); this.peer = peer;
    this.lastSeen = Date.now();
    this.timer = setInterval(() => {
      if (this.connection?.open) {
        if (Date.now() - this.lastSeen > 20000) { this.close("Opponent disconnected. Duel stopped; no further agent calls."); return; }
        this.connection.send({ type: "heartbeat" });
      }
    }, 5000);
    // Signaling errors (including a rejected extra connector) must not kill a
    // healthy game channel. Its own close/error events and heartbeat govern it.
    peer.on("error", () => { if (this.peer === peer && !this.connection?.open) this.close("Could not connect. Try a new invitation or another network."); });
    // Reserve the single opponent as soon as its channel is created.
    peer.on("connection", c => {
      if (this.peer !== peer || seat !== 0 || this.connection) c.close();
      else this.attach(c, peer);
    });
    this.update(seat === 0 ? "Creating invitation…" : "Connecting to your friend…");
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => this.close("Connection timed out. Try another network."), 20000);
      this.cancelOpen = message => { clearTimeout(timeout); reject(Error(message)); };
      peer.once("open", () => { if (this.peer !== peer) return; clearTimeout(timeout); this.cancelOpen = null; resolve(); });
    });
    return peer;
  }
  async host(agent: Agent, game: string, moveLimit: number, maxTokens: number): Promise<string> {
    const local = structuredClone(agent);
    const offer = readOffer({ game, moveLimit, maxTokens, agent: duelAgent(local) });
    const peer = await this.open(0);
    this.local = local; this.offer = offer;
    this.update("Invitation ready. Send it to your friend, then press Ready.");
    return peer.id;
  }
  async join(id: string) {
    if (!/^[a-zA-Z0-9_-]{1,100}$/.test(id)) throw Error("Invalid duel invitation.");
    const peer = await this.open(1);
    this.attach(peer.connect(id, { reliable: true }), peer);
  }
  ready(agent: Agent) {
    if (!this.peer || !this.offer || this.localReady || this.started) return;
    if (this.seat === 1) this.local = structuredClone(agent);
    if (!this.local) throw Error("Choose your agent first.");
    const publicLocal = duelAgent(this.local);
    this.localReady = true;
    if (this.seat === 1) this.send({ type: "ready", agent: publicLocal });
    this.update("You’re ready. Waiting for your friend…");
    this.start();
  }
  private send(data: unknown) {
    if (!this.connection?.open) throw Error("Your friend is not connected yet.");
    this.connection.send(data);
  }
  private attach(c: DataConnection, peer: Peer) {
    this.connection = c;
    const current = () => this.peer === peer && this.connection === c;
    const timeout = setTimeout(() => { if (current()) this.close("Friend unavailable. Ask for a fresh invitation."); }, 20000);
    c.on("open", () => {
      clearTimeout(timeout); if (!current()) { c.close(); return; }
      this.lastSeen = Date.now();
      if (this.seat === 0) this.send({ type: "offer", offer: this.offer });
    });
    c.on("close", () => { clearTimeout(timeout); if (current()) this.close("Opponent left. Duel stopped; replay is still available."); });
    c.on("error", () => { clearTimeout(timeout); if (current()) this.close("Connection interrupted. Duel stopped; replay is still available."); });
    c.on("data", raw => {
      if (!current()) return;
      try {
        if (!raw || typeof raw !== "object" || JSON.stringify(raw).length > 350000) throw Error("Invalid duel message.");
        this.lastSeen = Date.now();
        this.receive(raw as { type: string; [key: string]: unknown });
      } catch { this.close("Invalid duel update. Match stopped; no further agent calls."); }
    });
  }
  private receive(message: { type: string; [key: string]: unknown }) {
    if (message.type === "heartbeat") return;
    if (message.type === "stop") { this.close("Your friend stopped the duel. Replay is still available."); return; }
    if (message.type === "offer" && this.seat === 1 && !this.offer) {
      this.offer = readOffer(message.offer);
      this.update("Invitation received. Review the game and limits, choose your agent, then press Ready.");
    } else if (message.type === "ready" && this.seat === 0 && !this.remote && !this.started) {
      this.remote = readAgent(message.agent);
      this.update("Your friend is ready. Press Ready when your agent is set."); this.start();
    } else if (message.type === "start" && this.seat === 1 && this.localReady && !this.started && this.offer) {
      const record = replay(message.record).record;
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(record.id) ||
          record.events.length || canonical(record.rules) !== canonical(RULES[this.offer.game]) ||
          canonical(record.agents) !== canonical([this.offer.agent, duelAgent(this.local!)])) throw Error("Unexpected duel setup.");
      this.record = record; this.started = true; this.advance();
    } else if (message.type === "move" && this.started && this.record && this.offer) {
      this.record = acceptDuelMove(this.record, message.record, 1 - this.seat, this.offer.moveLimit);
      this.advance();
    } else throw Error("Unexpected duel message.");
  }
  private start() {
    if (this.seat !== 0 || !this.localReady || !this.remote || this.started || !this.offer) return;
    this.record = { schema: "builderwars.exhibition.v1", id: crypto.randomUUID(), createdAt: new Date().toISOString(),
      rules: RULES[this.offer.game], agents: [this.offer.agent, this.remote], events: [], status: "Playing" };
    this.started = true;
    this.send({ type: "start", record: this.record }); this.advance();
  }
  private advance() {
    if (!this.peer || !this.record || !this.offer) return;
    const state = replay(this.record).state;
    if (state.over) {
      this.record.status = state.reason;
      this.update(state.winner === null ? `Draw · ${state.reason}` : `${this.record.agents[state.winner].name} wins · ${state.reason}`);
      return;
    }
    if (state.moves.length >= this.offer.moveLimit) {
      this.record.status = "Move limit reached"; this.update("Move limit reached · no winner. Download the replay or set up another duel."); return;
    }
    this.update(`${this.record.agents[state.turn].name} is thinking…`);
    if (state.turn === this.seat && !this.busy) void this.move(state);
  }
  private async move(state: GameState) {
    this.busy = true;
    const generation = this.generation, previous = this.record!;
    const controller = new AbortController(); this.controller = controller;
    try {
      // A short pace keeps free games watchable and allows either owner to stop.
      await new Promise(resolve => setTimeout(resolve, 500));
      if (generation !== this.generation) return;
      const decision = await this.choose(state, this.local!, this.offer!.maxTokens, controller.signal);
      if (generation !== this.generation) return;
      const next = { ...previous, events: [...previous.events, { ...decision, comment: "", ply: previous.events.length + 1,
        seat: this.seat, label: moveLabel(decision.move, state) }] };
      this.record = acceptDuelMove(previous, next, this.seat, this.offer!.moveLimit);
      this.send({ type: "move", record: this.record });
      this.busy = false; this.controller = null; this.advance();
    } catch (error) {
      if (generation === this.generation) this.close(`Agent could not make a legal move. Duel stopped. ${(error as Error).message}`);
    }
  }
}
