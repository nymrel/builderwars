import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { RULES, replay, verifyProof, sha256, type RecordData } from '../src/runtime';
import { labBaseline, makeLabRun, validateLabPlan, validateLabImport, readLabVersion, labSource, LAB_LIMITS, arenaLabVersion, validateArenaLabVersion } from '../src/browser-lab-core';
import { createVersion } from '../src/frontier-version';
import { qualifyTicTacToeOracle } from '../src/competition-baselines';
import { circuitStandings } from '../src/public-circuit';
import { configuredAgents, encodeSetup, decodeSetup } from '../src/sharing';
const publicFile=(path:string)=>readFile(new URL(`../public/${path}`,import.meta.url));
test('the standard tic-tac-toe Oracle agrees with an independent solver on every reachable unfinished board',()=>{
 const q=qualifyTicTacToeOracle();assert.equal(q.reachableStates,5478);assert.equal(q.assessedNonterminalStates,4520);assert.equal(q.illegalOrSuboptimalMoves,0);
});
test('every published game and proof derives the full seat-swapped circuit without trusting a supplied score',async()=>{
 const c=JSON.parse((await publicFile('competition/launch-ttt-v1/manifest.json')).toString());const records:RecordData[]=[];
 for(const m of c.matches){const packet=await publicFile(m.path),proof=await publicFile(m.proof);assert.equal(createHash('sha256').update(packet).digest('hex'),m.digest);assert.equal(createHash('sha256').update(proof).digest('hex'),m.proofDigest);const r=JSON.parse(packet.toString()).record;assert.deepEqual((await verifyProof(proof.toString(),c.referee.digest)).record,replay(r).record);records.push(r);}
 const rows=circuitStandings(c,records,{replay});assert.deepEqual(rows.map(r=>[r.id,r.points]),[['perfect-ttt-v1',15.5],['tactics-v1',7],['random-v1',1.5]]);assert.ok(rows.every(r=>r.played===16&&r.firstSeat===8&&r.secondSeat===8));
 const missing=structuredClone(c);missing.matches.pop();assert.throws(()=>circuitStandings(missing,records,{replay}));
 const duplicate=structuredClone(c);duplicate.matches[1]=duplicate.matches[0];assert.throws(()=>circuitStandings(duplicate,records,{replay}));
});
test('Lab plans pin bounded execution and trial seeds before work; foreign configurations do not execute',async()=>{
 const parent=await labBaseline('connect4'),run=await makeLabRun(parent,23,16);await validateLabPlan(run);assert.equal(run.plan.seeds.length,16);assert.equal(run.blocks.length,0);assert.deepEqual(parent.config.limits,LAB_LIMITS);assert.equal(parent.config.harness.source,labSource.digest);
 const bad=structuredClone(run);bad.plan.seeds[0]++;await assert.rejects(validateLabPlan(bad));
 const config=structuredClone(parent.config);config.limits.nodes++;await assert.rejects(validateLabImport(await createVersion(config)));
 await assert.rejects(validateLabImport({...parent,endpoint:'https://invalid.example'}));
 await assert.rejects(makeLabRun(parent,NaN,16));await assert.rejects(makeLabRun(parent,1,4));
});
test('historical versions remain exportable while current execution validation refuses them',async()=>{
 const old=structuredClone(await labBaseline('tictactoe'));old.config.harness.source='1'.repeat(64);old.config.referee='2'.repeat(64);const {digest,...body}=old;old.digest=await sha256(JSON.stringify(body));assert.equal((await readLabVersion(old)).digest,old.digest);await assert.rejects(validateLabImport(old));const bad=structuredClone(old);bad.config.value!.weights[0]=4;await assert.rejects(readLabVersion(bad));
});
test('Oracle challenge setup round trips and refuses other games',()=>{
 const setup={schema:'builderwars.setup.v1',rules:RULES.tictactoe,moveLimit:9,maxTokens:512,entrants:[{kind:'bot',model:'tactician',effort:'default'},{kind:'bot',model:'perfect-ttt-v1',effort:'default'}]};const actual=decodeSetup(encodeSetup(setup));assert.equal(configuredAgents(actual)[1].name,'Tic-tac-toe Oracle');assert.throws(()=>encodeSetup({...setup,rules:RULES.connect4}),/tic-tac-toe/);
});

test('Arena derives an explicit new exhibition version without changing Lab evidence or numeric parameters',async()=>{
 const parent=await labBaseline('connect4'),arena=await arenaLabVersion(parent);assert.notEqual(arena.digest,parent.digest);assert.equal(arena.parent,parent.digest);assert.equal(arena.config.limits.milliseconds,90000);assert.equal(parent.config.limits.milliseconds,5000);assert.deepEqual(arena.config.value,parent.config.value);await validateArenaLabVersion(arena);await assert.rejects(validateLabImport(arena));
});
