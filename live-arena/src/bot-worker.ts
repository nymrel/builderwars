import { botMove, type GameState } from "./runtime";

import { perfectTicTacToeMove } from "./competition-baselines";

type SearchRequest = { state: GameState; style: string };
type SearchResponse = { move?: string; error?: string; ready?: boolean };
const scope = self as unknown as {
  onmessage: ((event: MessageEvent<SearchRequest>) => void) | null;
  postMessage: (message: SearchResponse) => void;
};

scope.onmessage = (event) => {
  try {
    scope.postMessage({ move: event.data.style === "perfect-ttt-v1" ? perfectTicTacToeMove(event.data.state) : botMove(event.data.state, event.data.style) });
  } catch {
    scope.postMessage({ error: "Built-in tactical search failed." });
  }
};
scope.postMessage({ ready: true });
