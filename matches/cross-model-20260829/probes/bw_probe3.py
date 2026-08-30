"""Probe llama3.2:3b via the Ollama HTTP API (pure transport) at temp 0 vs default.

Measures: parse rate + on-list rate with the exact solver prompt. No content munging.
"""
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
# 24 positions: mix where winning moves exist and lost positions (candidates = all legal)
positions = [
    [3, 4, 5], [1, 4, 6], [2, 2, 5], [7, 1], [3, 3, 2], [5, 6, 1], [4, 4, 4, 2], [1, 2, 3],
    [2, 5, 7], [6, 6, 3], [8, 1], [4, 9], [1, 1, 4], [5, 5, 5, 3], [2, 2], [9, 2, 6],
    [3, 3], [4, 4, 1], [7, 7, 2], [5, 8], [1, 3, 5, 7], [6, 2, 2], [10, 4], [2, 3, 6],
]

for label, opts in [("temp0", {"temperature": 0}), ("default", {})]:
    on = parse_fail = off_list = 0
    fails = []
    for heaps in positions:
        cands = sh.candidates(heaps)
        prompt = sh.build_prompt({"rules": RULES, "heaps": heaps, "you_are": 0}, cands)
        text = api(prompt, "llama3.2:3b", opts)
        mv = parse_move(text)
        if mv is None:
            parse_fail += 1
            fails.append((heaps, "PARSE-FAIL", text.strip()[:110]))
        elif mv in cands:
            on += 1
        else:
            off_list += 1
            fails.append((heaps, f"OFF-LIST {mv}", text.strip()[:110]))
    print(f"== {label}: on-list {on}/24, parse-fail {parse_fail}, off-list {off_list}")
    for heaps, kind, t in fails:
        print(f"   {kind} heaps={heaps} raw={t!r}")
