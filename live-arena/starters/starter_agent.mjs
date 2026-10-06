#!/usr/bin/env node
// Dependency-free BuilderWars starter: raw move JSON or the local bridge prompt.
import assert from 'node:assert/strict';
const MODEL = 'builderwars-starter-javascript-v1';
const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
export function readRequest(text) {
  if (Buffer.byteLength(text) > 64000) throw Error('Move request exceeds 64KB');
  const payload = text.trimStart().startsWith('{') ? text.trim() : text.trimEnd().slice(text.trimEnd().lastIndexOf('\n') + 1).trim();
  const request = JSON.parse(payload), legal = request.legalMoves;
  if (!Array.isArray(legal) || !legal.length || legal.length > 256 || legal.some(m => typeof m !== 'string' || m.length > 100) || ![0,1].includes(request.turn)) throw Error('A bounded legalMoves list and turn are required');
  return request;
}
export function chooseMove(request) {
  const legal = request.legalMoves;
  if (request.game?.kind === 'tictactoe') {
    const cells = request.position, own = request.turn === 0 ? 'w' : 'b';
    if (!Array.isArray(cells) || cells.length !== 9 || cells.some(c => !['','w','b'].includes(c))) throw Error('Expected the standard tic-tac-toe board');
    for (const mark of [own, own === 'w' ? 'b' : 'w']) for (const move of legal) {
      if (!/^\d$/.test(move) || Number(move) > 8 || cells[Number(move)]) throw Error('Legal move contradicts the board');
      const next = [...cells]; next[Number(move)] = mark;
      if (lines.some(line => line.every(i => next[i] === mark))) return move;
    }
    for (const move of ['4','0','2','6','8','1','3','5','7']) if (legal.includes(move)) return move;
  }
  return legal[0];
}
export function answer(request) {
  const move = chooseMove(request); if (!request.legalMoves.includes(move)) throw Error('Illegal starter move');
  return { move, comment:'Starter: immediate win, immediate defense, then a fixed preference.', model:MODEL, tokens:null };
}
if (process.argv[2] === '--check' && process.argv.length === 3) {
  const request = { game:{kind:'tictactoe'},position:['w','w','','b','b','','','',''],turn:0,legalMoves:['2','5','6','7','8'] };
  assert.equal(answer(readRequest(JSON.stringify(request))).move,'2');
  assert.equal(answer(readRequest('Play the supplied game. Data follows.\n'+JSON.stringify(request))).move,'2');
  assert.throws(() => readRequest('{"turn":0,"legalMoves":[]}'));
  console.log(JSON.stringify({checked:true,model:MODEL,providerCalls:0,protocol:'raw JSON and local bridge prompt'}));
} else if (process.argv.length === 2) {
  let text=''; for await (const chunk of process.stdin) {text+=chunk;if(Buffer.byteLength(text)>64000)throw Error('Move request exceeds 64KB');}
  console.log(JSON.stringify(answer(readRequest(text))));
} else { throw Error('Usage: node starter_agent.mjs [--check]'); }
