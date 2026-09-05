import { Chess } from "chess.js";

export type GameKind =
  | "chess"
  | "checkers"
  | "connect4"
  | "tictactoe"
  | "custom";
export type Rules = {
  kind: GameKind;
  name: string;
  rows: number;
  cols: number;
  connect: number;
  gravity: boolean;
};
export type GameState = {
  rules: Rules;
  cells: string[];
  turn: 0 | 1;
  moves: string[];
  fen?: string;
  winner: number | null;
  over: boolean;
  reason: string;
  quiet: number;
  positions: string[];
};
export const RULES: Record<string, Rules> = {
  chess: {
    kind: "chess",
    name: "Chess",
    rows: 8,
    cols: 8,
    connect: 0,
    gravity: false,
  },
  checkers: {
    kind: "checkers",
    name: "Checkers",
    rows: 8,
    cols: 8,
    connect: 0,
    gravity: false,
  },
  connect4: {
    kind: "connect4",
    name: "Connect Four",
    rows: 6,
    cols: 7,
    connect: 4,
    gravity: true,
  },
  tictactoe: {
    kind: "tictactoe",
    name: "Tic-tac-toe",
    rows: 3,
    cols: 3,
    connect: 3,
    gravity: false,
  },
};
export function validateRules(raw: unknown): Rules {
  if (!raw || typeof raw !== "object" || Array.isArray(raw))
    throw Error("Invalid game rules.");
  const r = raw as Rules;
  if (Object.keys(RULES).includes(r.kind)) return { ...RULES[r.kind] };
  if (
    r.kind !== "custom" ||
    typeof r.name !== "string" ||
    r.name.length < 1 ||
    r.name.length > 48 ||
    !Number.isInteger(r.rows) ||
    r.rows < 3 ||
    r.rows > 10 ||
    !Number.isInteger(r.cols) ||
    r.cols < 3 ||
    r.cols > 10 ||
    !Number.isInteger(r.connect) ||
    r.connect < 3 ||
    r.connect > Math.min(r.rows, r.cols) ||
    typeof r.gravity !== "boolean"
  )
    throw Error("Use a 3–10 square board and a valid connect length.");
  return {
    kind: "custom",
    name: r.name,
    rows: r.rows,
    cols: r.cols,
    connect: r.connect,
    gravity: r.gravity,
  };
}
const coordinate = (i: number, cols: number) =>
  `${String.fromCharCode(97 + (i % cols))}${Math.floor(i / cols) + 1}`;
export function square(i: number, s: GameState) {
  return s.rules.kind === "chess"
    ? `${String.fromCharCode(97 + (i % 8))}${8 - Math.floor(i / 8)}`
    : coordinate(i, s.rules.cols);
}
export function createGame(rules: Rules): GameState {
  const r = validateRules(rules),
    s: GameState = {
      rules: r,
      cells: Array(r.rows * r.cols).fill(""),
      turn: 0,
      moves: [],
      winner: null,
      over: false,
      reason: "",
      quiet: 0,
      positions: [],
    };
  if (r.kind === "chess") {
    const c = new Chess();
    s.fen = c.fen();
    s.cells = chessCells(c);
  }
  if (r.kind === "checkers")
    for (let i = 0; i < 64; i++) {
      const row = Math.floor(i / 8);
      if ((row + (i % 8)) % 2 === 1 && (row < 3 || row > 4))
        s.cells[i] = row < 3 ? "b" : "w";
    }
  s.positions = [position(s)];
  return s;
}
function chessCells(c: Chess) {
  return c
    .board()
    .flat()
    .map((p) => (p ? `${p.color}${p.type}` : ""));
}
function position(s: GameState) {
  return `${s.cells.join(",")}|${s.turn}`;
}
function checkersMoves(s: GameState): string[] {
  const jumps: string[] = [],
    steps: string[] = [],
    own = s.turn === 0 ? "w" : "b",
    enemy = s.turn === 0 ? "b" : "w";
  const inside = (r: number, c: number) => r >= 0 && r < 8 && c >= 0 && c < 8;
  function jump(cells: string[], i: number, path: number[]) {
    const piece = cells[i],
      row = Math.floor(i / 8),
      col = i % 8,
      dirs = piece === piece.toUpperCase() ? [-1, 1] : [own === "w" ? -1 : 1];
    let extended = false;
    for (const dr of dirs)
      for (const dc of [-1, 1]) {
        const nr = row + dr * 2,
          nc = col + dc * 2,
          mid = (row + dr) * 8 + col + dc,
          to = nr * 8 + nc;
        if (
          inside(nr, nc) &&
          cells[mid]?.toLowerCase() === enemy &&
          !cells[to]
        ) {
          extended = true;
          const next = [...cells];
          next[i] = "";
          next[mid] = "";
          next[to] = piece;
          const nextPath = [...path, to];
          if (piece === own && (nr === 0 || nr === 7))
            jumps.push(nextPath.map((x) => coordinate(x, 8)).join("-"));
          else jump(next, to, nextPath);
        }
      }
    if (!extended && path.length > 1)
      jumps.push(path.map((x) => coordinate(x, 8)).join("-"));
  }
  s.cells.forEach((p, i) => {
    if (p.toLowerCase() !== own) return;
    jump(s.cells, i, [i]);
    const row = Math.floor(i / 8),
      col = i % 8;
    for (const dr of p === p.toUpperCase() ? [-1, 1] : [own === "w" ? -1 : 1])
      for (const dc of [-1, 1]) {
        const nr = row + dr,
          nc = col + dc,
          to = nr * 8 + nc;
        if (inside(nr, nc) && !s.cells[to])
          steps.push(`${coordinate(i, 8)}-${coordinate(to, 8)}`);
      }
  });
  return jumps.length ? jumps : steps;
}
export function legalMoves(s: GameState): string[] {
  if (s.over) return [];
  if (s.rules.kind === "chess")
    return new Chess(s.fen)
      .moves({ verbose: true })
      .map((m) => m.from + m.to + (m.promotion || ""));
  if (s.rules.kind === "checkers") return checkersMoves(s);
  if (s.rules.gravity)
    return Array.from({ length: s.rules.cols }, (_, i) => i)
      .filter((i) => !s.cells[i])
      .map(String);
  return s.cells.flatMap((p, i) => (p ? [] : [String(i)]));
}
export function moveLabel(move: string, s: GameState): string {
  if (s.rules.kind === "chess") {
    try {
      const c = new Chess(s.fen);
      return c.move({
        from: move.slice(0, 2),
        to: move.slice(2, 4),
        promotion: move[4],
      })!.san;
    } catch {
      return move;
    }
  }
  if (s.rules.kind === "checkers") return move;
  return s.rules.gravity
    ? `Column ${Number(move) + 1}`
    : coordinate(Number(move), s.rules.cols);
}
export function applyMove(state: GameState, move: string): GameState {
  if (!legalMoves(state).includes(move))
    throw Error("The agent returned an illegal move. The match is paused.");
  const s: GameState = {
      ...state,
      cells: [...state.cells],
      moves: [...state.moves, move],
      positions: [...state.positions],
    },
    player = s.turn;
  s.turn = player === 0 ? 1 : 0;
  s.quiet++;
  if (s.rules.kind === "chess") {
    const c = new Chess();
    for (const m of state.moves)
      c.move({ from: m.slice(0, 2), to: m.slice(2, 4), promotion: m[4] });
    c.move({
      from: move.slice(0, 2),
      to: move.slice(2, 4),
      promotion: move[4],
    });
    s.fen = c.fen();
    s.cells = chessCells(c);
    if (c.isGameOver()) {
      s.over = true;
      s.winner = c.isCheckmate() ? player : null;
      s.reason = c.isCheckmate()
        ? "Checkmate"
        : c.isStalemate()
          ? "Stalemate"
          : c.isThreefoldRepetition()
            ? "Threefold repetition"
            : c.isInsufficientMaterial()
              ? "Insufficient material"
              : "Fifty-move draw";
    }
  } else if (s.rules.kind === "checkers") {
    const path = move
      .split("-")
      .map((x) => (Number(x.slice(1)) - 1) * 8 + x.charCodeAt(0) - 97);
    let piece = s.cells[path[0]];
    s.cells[path[0]] = "";
    for (let j = 1; j < path.length; j++) {
      const a = path[j - 1],
        b = path[j];
      if (Math.abs(Math.floor(a / 8) - Math.floor(b / 8)) === 2) {
        s.cells[(a + b) / 2] = "";
        s.quiet = 0;
      }
    }
    const end = path.at(-1)!;
    if (piece === piece.toLowerCase()) {
      s.quiet = 0;
      if (Math.floor(end / 8) === 0 || Math.floor(end / 8) === 7)
        piece = piece.toUpperCase();
    }
    s.cells[end] = piece;
    if (!checkersMoves(s).length) {
      s.over = true;
      s.winner = player;
      s.reason = "No legal moves";
    }
    s.positions.push(position(s));
    if (
      !s.over &&
      (s.quiet >= 80 ||
        s.positions.filter((x) => x === position(s)).length >= 3)
    ) {
      s.over = true;
      s.reason = "Repetition or 40-move draw";
    }
  } else {
    let index = Number(move);
    if (s.rules.gravity)
      while (
        index + s.rules.cols < s.cells.length &&
        !s.cells[index + s.rules.cols]
      )
        index += s.rules.cols;
    s.cells[index] = player === 0 ? "w" : "b";
    const { rows, cols, connect } = s.rules,
      row = Math.floor(index / cols),
      col = index % cols;
    for (const [dr, dc] of [
      [1, 0],
      [0, 1],
      [1, 1],
      [1, -1],
    ]) {
      let count = 1;
      for (const sign of [-1, 1]) {
        let r = row + dr * sign,
          c = col + dc * sign;
        while (
          r >= 0 &&
          r < rows &&
          c >= 0 &&
          c < cols &&
          s.cells[r * cols + c] === s.cells[index]
        ) {
          count++;
          r += dr * sign;
          c += dc * sign;
        }
      }
      if (count >= connect) {
        s.over = true;
        s.winner = player;
        s.reason = `${connect} in a row`;
      }
    }
    if (!s.over && s.cells.every(Boolean)) {
      s.over = true;
      s.reason = "Board full";
    }
  }
  if (!s.over && s.moves.length >= 400) {
    s.over = true;
    s.reason = "400-ply exhibition limit";
  }
  return s;
}
export function botMove(s: GameState, style = "tactician"): string {
  const moves = legalMoves(s);
  if (!moves.length) throw Error("No legal moves.");
  if (style === "random")
    return moves[Math.floor(Math.random() * moves.length)];
  const player = s.turn;
  let best = -Infinity,
    chosen = moves[0];
  function value(next: GameState): number {
    if (next.over)
      return next.winner === player
        ? 100000
        : next.winner === null
          ? 0
          : -100000;
    const vals: Record<string, number> = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
    return next.cells.reduce((total, p, i) => {
      if (!p) return total;
      const own = p[0]?.toLowerCase() === (player === 0 ? "w" : "b");
      let v =
        next.rules.kind === "chess"
          ? (vals[p[1]] ?? 1) * 100
          : next.rules.kind === "checkers"
            ? p === p.toUpperCase()
              ? 190
              : 100
            : 0;
      v += 4 - Math.abs((i % next.rules.cols) - (next.rules.cols - 1) / 2);
      return total + (own ? 1 : -1) * v;
    }, 0);
  }
  for (const m of moves) {
    const next = applyMove(s, m);
    let score = value(next);
    if (!next.over) {
      let worst = Infinity;
      for (const reply of legalMoves(next)) {
        worst = Math.min(worst, value(applyMove(next, reply)));
      }
      score = worst;
    }
    if (score > best) {
      best = score;
      chosen = m;
    }
  }
  return chosen;
}
export function gamePrompt(s: GameState, strategy: string) {
  return `Play ${s.rules.name}. You control ${s.turn === 0 ? "white / player 1" : "black / player 2"}. Choose exactly one legal move. Reply with JSON {"move":"legal move","comment":"one short public explanation"}. Do not include private reasoning.\nRules: ${JSON.stringify(s.rules)}\nPosition: ${s.fen || JSON.stringify(s.cells)}\nRecent moves: ${s.moves.slice(-16).join(" ")}\nLegal moves: ${JSON.stringify(legalMoves(s))}\nBuilder strategy: ${strategy.slice(0, 1000)}`;
}
