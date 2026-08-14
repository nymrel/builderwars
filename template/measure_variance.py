"""How many rounds and how many seeds before skill beats noise?

Deterministic sparring bots make Ten Fronts look luck-free (it is, for them).
Real entrants are stochastic -- temperature, retries, sampling -- so the honest
measurement uses at least one stochastic side.

Method: establish ground truth on a large sample, then ask how often a SMALL
block of seeds reproduces it. That block size is what the engine must schedule.
"""
from __future__ import annotations
from arena import baselines as B
from arena.runner import pairing

TF, MF = B.TEN_FRONTS_PANEL, B.MANIFEST_PANEL


def truth(game, panel, a, b, n, config=None):
    t = pairing(game, panel[a], panel[b], range(5000, 5000 + n), config)
    return t["a"] > t["b"], t


def block_accuracy(game, panel, a, b, block, blocks, expect_a, config=None):
    ok = tie = 0
    for k in range(blocks):
        lo = 9000 + k * block
        t = pairing(game, panel[a], panel[b], range(lo, lo + block), config)
        if t["a"] == t["b"]:
            tie += 1
        elif (t["a"] > t["b"]) == expect_a:
            ok += 1
    return ok / blocks, tie / blocks


print("=" * 72)
print("TEN FRONTS -- stochastic pair (jitter vs value_weighted), near-equal strength")
for r in (5, 10, 20, 30):
    cfg = {"rounds": r}
    exp, t = truth("ten_fronts", TF, "jitter", "value_weighted", 120, cfg)
    acc, tie = block_accuracy("ten_fronts", TF, "jitter", "value_weighted", 1, 60, exp, cfg)
    acc5, _ = block_accuracy("ten_fronts", TF, "jitter", "value_weighted", 5, 24, exp, cfg)
    print(f"  rounds={r:>2}  truth {t['a']:.0f}/{t['b']:.0f}"
          f"   1 seed {acc:5.1%}   5 seeds {acc5:5.1%}   (ties {tie:.0%})")

print("\nTEN FRONTS -- clearly-separated pair (counter_last vs uniform)")
for r in (5, 10, 20):
    cfg = {"rounds": r}
    exp, t = truth("ten_fronts", TF, "counter_last", "uniform", 40, cfg)
    acc, _ = block_accuracy("ten_fronts", TF, "counter_last", "uniform", 1, 40, exp, cfg)
    print(f"  rounds={r:>2}  truth {t['a']:.0f}/{t['b']:.0f}   1 seed {acc:5.1%}")

print("\n" + "=" * 72)
print("MANIFEST -- near-equal pair (shader vs honest, 5% true edge)")
exp, t = truth("manifest", MF, "shader", "honest", 200)
print(f"  ground truth over 200 seeds: shader {t['a']:.0f} / honest {t['b']:.0f}"
      f"  edge {100*(t['a']-t['b'])/(t['a']+t['b']):+.1f}%")
for block in (5, 10, 20, 40):
    acc, tie = block_accuracy("manifest", MF, "shader", "honest", block, max(6, 120 // block), exp)
    print(f"  block of {block:>2} seeds ({2*block:>3} matches): calls it right {acc:5.1%}  (ties {tie:.0%})")

print("\nMANIFEST -- clearly-separated pair (honest vs accept_first)")
exp, t = truth("manifest", MF, "honest", "accept_first", 40)
for block in (5, 10):
    acc, _ = block_accuracy("manifest", MF, "honest", "accept_first", block, 12, exp)
    print(f"  block of {block:>2} seeds: calls it right {acc:5.1%}")
