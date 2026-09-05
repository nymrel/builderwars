#!/usr/bin/env python3
"""Adversarial checks for the browser-memory Ten Fronts Blitz exhibition."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile-arena"
MODULE = MOBILE / "ten-fronts-blitz.js"
RULES_DIGEST = "e61c1f1c173adfc0de8d754955386e57598efcbf018a1ba974baed9e7de72cfd"
FIXTURE_ID = "d454877ad65651deae5fe1be5e09fb0340a2fda189c5df0ca5223e91767392a7"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def main() -> int:
    node = shutil.which("node")
    require(node is not None, "Node.js is required for the local game contract")
    for relative in ("ten-fronts.html", "ten-fronts-blitz.css", "ten-fronts-blitz.js"):
        require((MOBILE / relative).is_file(), f"missing Ten Fronts Blitz asset: {relative}")

    script = r"""
const api=require(process.argv[1]);
const assert=(ok,label)=>{if(!ok)throw new Error(label)};
const clone=value=>JSON.parse(JSON.stringify(value));
const fails=async(fn,label)=>{let refused=false;try{await fn()}catch{refused=true}assert(refused,label)};
const authorityFalse=value=>Object.values(value).every(item=>item===false);
const independentReference=values=>{
  const weights=values.map(value=>value*value), total=weights.reduce((a,b)=>a+b,0);
  const out=weights.map(value=>Math.floor(value*100/total));
  let remainder=100-out.reduce((a,b)=>a+b,0);
  for(const index of [...values.keys()].sort((a,b)=>weights[b]-weights[a]||a-b)){if(!remainder)break;out[index]+=1;remainder-=1}
  return out;
};
(async()=>{
  assert(api.RULES_DIGEST===process.argv[2],'rules digest constant drift');
  assert(api.FIXTURE_ID===process.argv[3],'fixture digest constant drift');
  assert(api.RESOURCE_CLASS==='browser-memory-human-vs-deterministic-no-model-v1','resource class drift');
  assert(api.RULES.rounds===3&&api.RULES.fronts===10&&api.RULES.troops===100,'Blitz bounds drift');
  assert(api.RULES.exactTiesPayZero===true&&api.RULES.maxHumanSubmissions===6,'scoring or submission bounds drift');
  for(const values of api.RULES.frontValues){
    const observed=api.referenceAllocation(values), expected=independentReference(values);
    assert(JSON.stringify(observed)===JSON.stringify(expected),'deterministic reference drift');
    assert(observed.reduce((a,b)=>a+b,0)===100,'reference must allocate exactly 100');
  }
  assert(JSON.stringify(api.scoreRound([5,4],[10,5],[9,6]))==='[5,4]','higher allocation scoring drift');
  assert(JSON.stringify(api.scoreRound([5,4],[10,5],[10,5]))==='[0,0]','exact ties must pay nobody');
  await fails(()=>api.qualify('bounded_demo'),'fallback source must hold qualification');
  const qualification=await api.qualify('verified_corpus');
  assert(qualification.fixture.fixtureId===process.argv[3]&&qualification.fixture.rulesDigest===process.argv[2],'qualification binding drift');
  assert(authorityFalse(qualification.attestations)&&qualification.seats.humanIdentityAttested===false,'qualification grants identity or authority');
  const rounds=[
    {signalId:'steady',allocation:[10,10,10,10,10,10,10,10,10,10]},
    {signalId:'pressure',allocation:[20,0,20,0,10,20,0,20,0,10]},
    {signalId:'feint',allocation:[0,15,20,5,10,0,15,20,5,10]},
  ];
  const receipt=await api.createReceipt(qualification,rounds);
  const verification=await api.verifyReceipt(receipt);
  assert(verification.replayVerdict==='PASS'&&verification.candidateDigest===receipt.candidateDigest,'independent replay failed');
  assert(verification.replayedRoundCount===3&&verification.humanSubmissionCount===6,'replay count drift');
  assert(verification.modelMoveCount===0&&verification.providerCallCount===0&&authorityFalse(verification.authority),'replay grants execution authority');
  const learning=await api.createLearning(receipt,verification);
  assert(learning.hiddenReasoningInferred===false&&learning.parentCandidateDigest===receipt.candidateDigest&&authorityFalse(learning.authority),'learning boundary drift');
  const runback=await api.createRunback(receipt,verification,learning);
  assert(runback.runbackVersion===1&&runback.executionStatus==='not_run'&&runback.ranked===false&&authorityFalse(runback.attestations),'runback must remain unplayed');
  const invalidAllocations=[
    [10,10,10,10,10,10,10,10,10],
    [10,10,10,10,10,10,10,10,10,9],
    [10,10,10,10,10,10,10,10,10,10.5],
    [-1,11,10,10,10,10,10,10,10,10],
    [101,0,0,0,0,0,0,0,0,-1],
  ];
  for(const allocation of invalidAllocations)await fails(()=>api.createReceipt(qualification,[{...rounds[0],allocation},rounds[1],rounds[2]]),'malformed allocation was accepted');
  await fails(()=>api.createReceipt(qualification,[{...rounds[0],signalId:'free-text'},rounds[1],rounds[2]]),'non-allowlisted signal was accepted');
  await fails(()=>api.createReceipt(qualification,[{...rounds[0],extra:true},rounds[1],rounds[2]]),'unknown human-round field was accepted');
  for(const mutate of [
    value=>{value.candidateDigest='00'.repeat(32)},
    value=>{value.result.scores[0]+=1},
    value=>{value.rounds[0].allocations[1][0]+=1},
    value=>{value.qualification.fixture.rulesDigest='00'.repeat(32)},
    value=>{value.attestations.publication=true},
    value=>{value.unknown=true},
  ]){const tampered=clone(receipt);mutate(tampered);await fails(()=>api.verifyReceipt(tampered),'tampered receipt was accepted')}
  const dangerous=clone(receipt);Object.defineProperty(dangerous.result,'__proto__',{value:{polluted:true},enumerable:true});
  await fails(()=>api.verifyReceipt(dangerous),'dangerous key was accepted');
  const badLearning=clone(learning);badLearning.parentCandidateDigest='00'.repeat(32);
  await fails(()=>api.createRunback(receipt,verification,badLearning),'runback accepted broken learning lineage');
  console.log(JSON.stringify({status:'PASS',checks:35,candidateDigest:receipt.candidateDigest,score:receipt.result.scores,learningRound:learning.observation.round}));
})().catch(error=>{console.error(error.stack||error);process.exit(1)});
"""
    completed = subprocess.run(
        [node, "-e", script, str(MODULE), RULES_DIGEST, FIXTURE_ID],
        cwd=MOBILE,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0, f"Ten Fronts Blitz contract failed: {completed.stderr.strip()}")
    result = json.loads(completed.stdout)
    require(result["status"] == "PASS" and result["checks"] == 35, "focused checker did not report its exact pass contract")

    html = (MOBILE / "ten-fronts.html").read_text(encoding="utf-8")
    css = (MOBILE / "ten-fronts-blitz.css").read_text(encoding="utf-8")
    source = MODULE.read_text(encoding="utf-8")
    require('data-source-mode="loading"' in html and 'id="ten-fronts-blitz-root"' in html, "page lacks fail-closed source state")
    require('name="blitz-signal"' not in html and "free-form" not in html.lower(), "static page must not expose a free-text signal")
    require("localStorage" not in source and "sessionStorage" not in source, "game must remain browser-memory only")
    require("fetch(" not in source and "XMLHttpRequest" not in source and "WebSocket" not in source, "game module must not add a network transport")
    require("prefers-reduced-motion" in css and "forced-colors" in css, "accessibility modes are not covered")
    require("noindex,nofollow" in html, "local exhibition page must remain non-indexable")
    print(f"BuilderWars Ten Fronts Blitz: PASS (41 checks; receipt {result['candidateDigest'][:16]}...)")
    print("human-controlled local allocations / independent replay / no identity, model, provider, registry, ranking, or publication authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"BuilderWars Ten Fronts Blitz: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
