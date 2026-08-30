"""Batch 2: llama3.2:3b @ temp0 on 24 fresh positions + qwen2.5:7b @ temp0 (same set)."""
import json, sys, urllib.request

sys.path.insert(0, "C:/Users/johns/Desktop/BuilderWars/entrants")
import solver_harness as sh
from parsing import parse_move


def api(prompt, model, options):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": options}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())["response"]


RULES = "Take 1-3 objects from one heap; the player who takes the last object wins."
positions = [
    [4, 5, 6], [2, 7, 7], [9, 3], [5, 2], [6, 6, 6, 1], [1, 5, 5], [8, 8, 3], [3, 6],
    [2, 4, 4], [7, 5, 1], [10, 10, 9], [6, 1], [3, 8], [1, 6, 6], [5, 5, 2, 2], [9, 9],
    [4, 4, 4], [2, 9, 9], [7, 2], [8, 3], [1, 1, 1, 4], [6, 6, 2], [10, 6], [5, 5, 5],
]

for model in ["llama3.2:3b", "qwen2.5:7b"]:
    on = pf = off = 0
    fails = []
    for heaps in positions:
        cands = sh.candidates(heaps)
        prompt = sh.build_prompt({"rules": RULES, "heaps": heaps, "you_are": 0}, cands)
        text = api(prompt, model, {"temperature": 0})
        mv = parse_move(text)
        if mv is None:
            pf += 1
            fails.append((heaps, "PARSE-FAIL", text.strip()[:100]))
        elif mv in cands:
            on += 1
        else:
            off += 1
            fails.append((heaps, f"OFF-LIST {mv}", text.strip()[:100]))
    print(f"== {model} temp0: on-list {on}/24, parse-fail {pf}, off-list {off}")
    for heaps, kind, t in fails:
        print(f"   {kind} heaps={heaps} raw={t!r}")
