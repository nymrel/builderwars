"""How many rounds / seeds does it take before skill, not noise, decides?

This is the number the engine lane needs. Run it, do not guess it.
"""
from __future__ import annotations
import statistics
from arena import baselines as B
from arena.runner import pairing, run_match

TF = B.TEN_FRONTS_PANEL
MF = B.MANIFEST_PANEL


def head_to_head(game, panel, a, b, seeds, config=None):
    t = pairing(game, panel[a], panel[b], seeds, config)
    return t["a"], t["b"]


def single_seed_accuracy(game, panel, a, b, n_seeds, config=None):
    """Fraction of INDIVIDUAL mirrored seeds on which the true-stronger side wins.
    1 seed = 2 matches (seats swapped)."""
    wins = ties = 0
    for s in range(1000, 1000 + n_seeds):
        x, y = head_to_head(game, panel, a, b, [s], config)
        if x > y:
            wins += 1
        elif x == y:
            ties += 1
    return wins / n_seeds, ties / n_seeds


print("=" * 68)
print("TEN FRONTS -- deception channel works?  (liar vs gullible, 40 seeds)")
for r in (20,):
    x, y = head_to_head("ten_fronts", TF, "liar", "gullible", range(40), {"rounds": r})
    print(f"  rounds={r:>2}   liar {x:>7.0f}   gullible {y:>7.0f}   edge {100*(x-y)/(x+y):+.1f}%")

print("\nTEN FRONTS -- does the same bot beat itself? (self-play must be ~0 edge)")
for who in ("counter_last", "jitter"):
    x, y = head_to_head("ten_fronts", TF, who, who, range(40))
    gap = f"{abs(x-y)/(x+y)*100:.2f}%" if (x + y) else "n/a (0-0: identical deterministic bots tie every front)"
    print(f"  {who} vs itself: {x:.0f} / {y:.0f}   seat gap {gap}")

print("\nTEN FRONTS -- rounds needed before ONE seed calls it right")
print("  (pair: concentrate > counter_last, established over 40 seeds)")
for r in (5, 10, 20, 30):
    acc, tie = single_seed_accuracy("ten_fronts", TF, "concentrate", "counter_last", 60, {"rounds": r})
    print(f"  rounds={r:>2}   single-seed accuracy {acc:5.1%}   ties {tie:4.1%}")

print("\n" + "=" * 68)
print("MANIFEST -- shading beats honesty?  (shader vs honest, 40 seeds)")
x, y = head_to_head("manifest", MF, "shader", "honest", range(40))
print(f"  shader {x:>7.0f}   honest {y:>7.0f}")

print("\nMANIFEST -- does the stonewaller escape?  (aggregate score is the answer)")
for opp in ("honest", "shader", "even_split", "accept_first"):
    x, y = head_to_head("manifest", MF, "stonewall", opp, range(40))
    print(f"  stonewall {x:>7.0f}  vs  {opp:<12} {y:>7.0f}")

print("\nMANIFEST -- seeds needed before ONE seed calls it right (shader > honest)")
acc, tie = single_seed_accuracy("manifest", MF, "shader", "honest", 60)
print(f"  single-seed accuracy {acc:5.1%}   ties {tie:4.1%}")

print("\nMANIFEST -- no-deal rate across the panel (a game nobody closes is not a game)")
deals = total = 0
for a in MF:
    for b in MF:
        if a == b:
            continue
        for s in range(12):
            r = run_match("manifest", {"A": MF[a](), "B": MF[b]()}, s)
            total += 1
            deals += 1 if r["deal"] else 0
print(f"  deals closed: {deals}/{total} = {deals/total:.0%}")

print("\nMANIFEST -- efficiency of closed deals vs the pareto frontier")
eff = []
for a in MF:
    for b in MF:
        if a == b:
            continue
        for s in range(12):
            r = run_match("manifest", {"A": MF[a](), "B": MF[b]()}, s)
            if r["deal"]:
                v, d = r["values"], r["deal"]
                joint = sum(v[w][i] for i, w in enumerate(d))
                eff.append(joint / r["efficient_joint"])
print(f"  median joint value captured: {statistics.median(eff):.1%} of the frontier")
