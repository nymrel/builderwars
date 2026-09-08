import { botMove, type GameState } from "./games";

type SearchRequest = { state: GameState; style: string };
type SearchResponse = { move?: string; error?: string };
const scope = self as unknown as {
  onmessage: ((event: MessageEvent<SearchRequest>) => void) | null;
  postMessage: (message: SearchResponse) => void;
};

scope.onmessage = (event) => {
  try {
    scope.postMessage({ move: botMove(event.data.state, event.data.style) });
  } catch {
    scope.postMessage({ error: "Built-in tactical search failed." });
  }
};
