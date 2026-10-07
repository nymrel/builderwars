import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {evalEntries,rankingBoards,findEvals,rankingRows,readShortlist,makeEvalPlan} from '../src/eval-catalogue';
import {dailyRules,challengeSetup} from '../src/competition-challenges';
import {validateRules,createGame,legalMoves} from '../src/runtime';
const root=new URL('../',import.meta.url);
test('directory searches capability and metric terms without mixing framework and benchmark filters',()=>{
 assert.equal(evalEntries.length,50);
 assert.ok(findEvals('function','tools','benchmark').some(e=>e.id==='bfcl'));
 assert.deepEqual(findEvals('function','coding'),[]);
 assert.ok(findEvals('retrieval','rag','framework').some(e=>e.id==='ragas'));
 assert.equal(findEvals('impossible-unlisted-benchmark').length,0);
});
test('ranking model filters retain source position, ties and evaluation track boundaries',()=>{
 const bfcl=rankingBoards.find(b=>b.id==='bfcl-v4')!;
 const row=bfcl.rows[2];assert.deepEqual(rankingRows(bfcl,row.name),[row]);assert.equal(row.rank,3);
 const evalplus=rankingBoards.find(b=>b.id==='humaneval-plus')!;
 assert.equal(evalplus.rows[0].rank,1);assert.equal(evalplus.rows[1].rank,1);assert.equal(evalplus.rows[2].rank,3);
 assert.notEqual(rankingBoards.find(b=>b.id==='tau3-banking')!.protocol,rankingBoards.find(b=>b.id==='tau3-voice')!.protocol);
 assert.match(rankingBoards.find(b=>b.id==='livecodebench')!.protocol,/not a current frontier ranking/);
});
test('eval plan admits only reviewed IDs and retains scope without executing a benchmark',()=>{
 assert.deepEqual(readShortlist('{broken'),[]);assert.deepEqual(readShortlist('["__proto__"]'),[]);
 assert.deepEqual(readShortlist(JSON.stringify(Array(13).fill('bfcl'))),[]);
 assert.deepEqual(readShortlist('["bfcl","bfcl","mmlu-pro"]'),['bfcl','mmlu-pro']);
 const plan=makeEvalPlan(['bfcl','mmlu-pro']);assert.equal(plan.evaluations.length,2);assert.match(plan.execution,/Not executed/);assert.equal(plan.model.provider,null);assert.match(plan.evaluations[0].sourceUrl,/github.com/);
 assert.throws(()=>makeEvalPlan(['not-reviewed']));
});
test('daily UTC boards stay stable, legal and bounded across dates; challenge setup never starts a game',()=>{
 assert.deepEqual(dailyRules('2026-10-07'),dailyRules('2026-10-07'));
 assert.throws(()=>dailyRules('2026-02-30'));assert.throws(()=>challengeSetup('untrusted'));
 const variants=new Set();for(let i=0;i<120;i++){const day=new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10);const rules=dailyRules(day);assert.deepEqual(validateRules(rules),rules);assert.ok(rules.rows*rules.cols<=36);const game=createGame(rules);assert.ok(legalMoves(game).length>0);assert.equal(game.moves.length,0);variants.add(JSON.stringify({...rules,name:''}));}assert.ok(variants.size>=4);
 assert.equal(challengeSetup('mirror-match').human,false);assert.equal(challengeSetup('mirror-match').seriesLength,4);assert.equal(challengeSetup('oracle-duel').oracle,true);
});
test('build gate rejects impossible scores, row substitution, duplicate sources and false tied ranks',async()=>{
 const {validateEvalCatalogue}=await import(new URL('../scripts/build-eval-catalogue.mjs',import.meta.url).href);
 const directory=JSON.parse(await readFile(new URL('data/evals/catalogue.json',root),'utf8'));
 const original=JSON.parse(await readFile(new URL('data/evals/rankings.json',root),'utf8'));
 assert.equal(validateEvalCatalogue(directory,original).boards,14);
 for(const mutate of [
  (b:any)=>{b.rows[0].score=101;},
  (b:any)=>{b.rows[1].sourceRowId=b.rows[0].sourceRowId;},
  (b:any)=>{b.rows[0].rank=2;},
  (b:any)=>{b.artifact='../../index.html';},
  (b:any)=>{b.sourceUrl='https://username:password@example.com/';},
 ]){const snapshots=structuredClone(original);mutate(snapshots.boards[0]);assert.throws(()=>validateEvalCatalogue(directory,snapshots));}
});
