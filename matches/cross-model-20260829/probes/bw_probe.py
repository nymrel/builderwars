"""Probe llama3.2:3b with the exact solver-harness prompt to measure off-list answers."""
import json, subprocess, sys

sys.path.insert(0, "C:/Users/johns/Desktop/BuilderWars/entrants")
import solver_harness as sh
from parsing import parse_move


def ollama(prompt, model, timeout=300):
    p = subprocess.run(["ollama", "run", model], input=prompt.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode != 0:
        return f"<<ERR {p.returncode}: {p.stderr.decode('utf-8','replace')[:200]}>>"
    return p.stdout.decode("utf-8", "replace")


positions = [
    [3, 4, 5], [1, 4, 6], [2, 2, 5], [7, 1], [3, 3, 2], [5, 6, 1], [4, 4, 4, 2], [1, 2, 3],
]

n_model = n_onlist = n_offlist = 0
for heaps in positions:
    cands = sh.candidates(heaps)
    prompt = sh.build_prompt({"rules": "Take 1-3 objects from one heap; the player who takes the last object wins.",
                              "heaps": heaps, "you_are": 0}, cands)
    text = ollama(prompt, "llama3.2:3b")
    mv = parse_move(text)
    n_model += 1
    if mv in cands:
        n_onlist += 1
        tag = "ON-LIST"
    else:
        n_offlist += 1
        tag = "OFF-LIST"
    print(f"heaps={heaps} -> {tag} parsed={mv} cands={cands} reply={text.strip()[:120]!r}")

print(f"\nsummary: {n_onlist}/{n_model} on-list, {n_offlist} off-list")
