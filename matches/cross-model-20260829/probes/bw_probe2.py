"""Compare ollama run flag variants for output cleanliness and parse rate."""
import json, subprocess, sys

sys.path.insert(0, "C:/Users/johns/Desktop/BuilderWars/entrants")
import solver_harness as sh
from parsing import parse_move


def ollama(prompt, model, flags, timeout=300):
    p = subprocess.run(["ollama", "run", model] + flags, input=prompt.encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode != 0:
        return f"<<ERR {p.returncode}: {p.stderr.decode('utf-8','replace')[:200]}>>"
    return p.stdout.decode("utf-8", "replace")


# include the two failure positions from the plain probe
positions = [[3, 4, 5], [1, 4, 6], [2, 2, 5], [7, 1], [3, 3, 2], [5, 6, 1], [4, 4, 4, 2], [1, 2, 3]]

for label, flags in [("plain", []), ("json", ["--format", "json"]),
                     ("json+nowrap", ["--format", "json", "--nowordwrap"])]:
    on = off = 0
    samples = []
    for heaps in positions:
        cands = sh.candidates(heaps)
        prompt = sh.build_prompt({"rules": "Take 1-3 objects from one heap; the player who takes the last object wins.",
                                  "heaps": heaps, "you_are": 0}, cands)
        text = ollama(prompt, "llama3.2:3b", flags)
        mv = parse_move(text)
        if mv in cands:
            on += 1
        else:
            off += 1
            samples.append((heaps, text.strip()[:150], mv))
    print(f"== {label}: {on}/8 on-list, {off} off-list")
    for heaps, t, mv in samples:
        print(f"   OFF heaps={heaps} parsed={mv} raw={t!r}")
