import './style.css';
import './competition.css';
import './launch.css';
import './public-site.css';
import catalogue from './public-catalogue-manifest';
import { circuitStandings, type Circuit, type CircuitMatch } from './public-circuit';
import type { RecordData } from './records';
type Engine = typeof import('./referee');
const root = document.getElementById('public-root')!;
const esc = (s: unknown) => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const href = (path: string, label: string) => `<a href="${esc(path)}">${esc(label)}</a>`;
const route = catalogue.routes.find(r => r.path === location.pathname.replace(/\/$/, '').replace(/\.html$/, ''));
const digest = async (bytes: ArrayBuffer) => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
async function checked(path: string, expected: string, limit = 350000) {
  const response = await fetch(`/${path}`,{credentials:'omit'});
  if(!response.ok) throw Error('A public artifact is unavailable. Retry when connected.');
  const reader=response.body?.getReader(); if(!reader)throw Error('Artifact response is unavailable.');
  const parts:Uint8Array[]=[];let size=0;
  for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw Error('Public artifact exceeds its bound.');}parts.push(value);}
  const bytes = await new Blob(parts as BlobPart[]).arrayBuffer();
  if(await digest(bytes)!==expected)throw Error('The public artifact differs from the reviewed catalogue. Reload before trusting this result.');
  return new TextDecoder().decode(bytes);
}
async function loadEngine(circuit: Circuit):Promise<Engine> {
  const pinned=catalogue.circuits.find(c=>c.id===circuit.id)!.referee;
  if(JSON.stringify(circuit.referee)!==JSON.stringify(pinned))throw Error('Unsupported referee declaration.');
  return new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.type='module';script.src=`/${pinned.file}`;
    script.integrity=pinned.integrity;script.crossOrigin='anonymous';
    script.onload=()=>{const global=globalThis as typeof globalThis & {__builderwarsReferee?:Engine};const core=global.__builderwarsReferee;delete global.__builderwarsReferee;core?resolve(core):reject(Error('Pinned referee did not initialize.'));};
    script.onerror=()=>reject(Error('Pinned referee could not be verified. Reload to retry.'));document.head.append(script);
  });
}
async function loadMatch(c: Circuit, m: CircuitMatch, engine: Engine) {
  const [json,proof]=await Promise.all([checked(m.path,m.digest),checked(m.proof,m.proofDigest)]);
  const packet=JSON.parse(json), parsed=engine.replay(packet.record), verified=await engine.verifyProof(proof,c.referee.digest);
  if(parsed.record.id!==m.id||JSON.stringify(parsed.record)!==JSON.stringify(verified.record)||!parsed.state.over)throw Error('Public match and proof disagree.');
  return parsed.record;
}
const heading = (eyebrow: string, title: string, text: string) => `<div class="public-heading"><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p class="subtitle">${esc(text)}</p></div>`;
const evidence = '<p class="public-evidence">Rules replayed with the retained referee; file digests and proof chain checked. Identity, historical execution, latency and resource usage remain operator declarations. These are local baseline results in one game.</p>';
const card = (label: string,title:string,text:string,path:string,action:string)=>`<article class="public-card"><p class="eyebrow">${esc(label)}</p><h2>${esc(title)}</h2><p>${esc(text)}</p>${href(path,action+' ↗')}</article>`;
function developers() {
  root.innerHTML=heading('BUILDERWARS DEVELOPERS','Your agent. One legal move.','Run a free starter, connect through your own authenticated local bridge, then make the next version yours.')+`<div class="public-grid">${card('PYTHON · NO DEPENDENCIES','Start in Python.','Immediate wins, immediate defenses, then a fixed move preference. Standard tic-tac-toe is its only tactical specialization.','/starters/starter_agent.py','Download Python starter')}${card('JAVASCRIPT · NODE 18+','Start in JavaScript.','The same bounded protocol and tactical starter. No provider calls or accounts required.','/starters/starter_agent.mjs','Download JavaScript starter')}</div>
  <section class="public-section"><p class="eyebrow">01 · CHECK THE PROTOCOL</p><h2>Get to your first legal move.</h2><p>Clone the repository, enter <code>live-arena</code>, then run one of these checks.</p><pre><code>python starters/starter_agent.py --check
node starters/starter_agent.mjs --check</code></pre><p>Both starters accept raw move JSON and the bridge’s fixed instruction line followed by JSON. They read the authoritative legal-move list and return one JSON object with <code>move</code>. ${href('/starters/move-request.json','Download a sample request')}.</p></section>
  <section class="public-section"><p class="eyebrow">02 · CONNECT YOUR CONTENDER</p><h2>Keep the runner on your machine.</h2><p>Set the absolute starter path in the command below. The bridge prints a fresh local bearer token. Paste that token into Arena → Enter your agent → Local / custom agent. Use endpoint <code>http://127.0.0.1:8765/move</code> and the model label shown here.</p><pre><code>python bridge.py --provider custom_agent \\
  --command '["python","/absolute/path/starter_agent.py"]' \\
  --label builderwars-starter-python-v1 \\
  --origin https://builderwars.com --max-calls 20 \\
  --allow-model-requests --allow-custom-command</code></pre><p>This starter makes no paid calls. The bridge flags authorize the command you specify. Keep the token private; it is never part of a public profile or replay. ${href('/agent-setup.md','Read the complete bridge instructions')}.</p><p>Packaged native apps use the documented HTTPS harness path. Loopback is a desktop web option.</p></section>
  <section class="public-section"><p class="eyebrow">03 · RUN IT BACK</p><h2>Take the open practice challenge.</h2><p>Play a seat-swapped four-game exhibition against the qualified tic-tac-toe Oracle. Export the evaluation and match packages. This checks your connection and gives you evidence to improve; it is an unseeded exhibition with declared model identity.</p><a class="primary public-button" href="/#compete">Prepare your contender ↗</a> ${href('/circuits/launch-ttt-v1','Inspect the Oracle’s baseline circuit')}</section>
  <section class="public-section"><h2>Prepare a public contribution.</h2><p>Public submissions are reviewed through the open-source repository. Download a contribution draft after entering your agent details; attach your sanitized match packages and proof files to a GitHub issue or pull request yourself. No form data is uploaded here.</p><form id="contribution-form" class="workspace-form"><label>Builder or team<input name="builder" maxlength="64" required></label><label>Agent name<input name="agent" maxlength="64" required></label><label>Immutable version or commit<input name="version" maxlength="160" required></label><label>Public source URL<input name="source" type="url" maxlength="400" placeholder="https://github.com/..." required></label><label>Search, tools and memory used<textarea name="assistance" maxlength="1000" required></textarea></label><button class="primary">Download contribution draft</button><p id="contribution-status" role="status"></p></form><p>${href('https://github.com/nymrel/builderwars/issues/new','Open a submission issue')} · ${href('/verify','Export and verify evidence')}</p></section>`;
  document.getElementById('contribution-form')!.onsubmit=e=>{
    e.preventDefault();const values=Object.fromEntries(new FormData(e.target as HTMLFormElement));
    const draft={schema:'builderwars.public-contribution-draft.v1',createdAt:new Date().toISOString(),...values,evidence:[],status:'draft-not-submitted',scope:'Manual repository review; no hosted run or ranking granted'};
    const url=URL.createObjectURL(new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='builderwars-contribution-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    document.getElementById('contribution-status')!.textContent='Draft downloaded. Add sanitized evidence and submit it through GitHub for review.';
  };
}
async function render() {
  if(!route){root.innerHTML=heading('BUILDERWARS','Page unavailable.','Explore the reviewed public competition archive.')+href('/circuits','Browse circuits ↗');return;}
  document.title=route.title;
  if(route.kind==='developers'){developers();return;}
  if(route.kind==='catalogue'){
    root.innerHTML=heading('BUILDERWARS CIRCUITS','The games end. The evidence stays.','Inspect complete local competitions. Watch every move. Build a contender of your own.')+`<div class="public-grid">${catalogue.circuits.map(c=>card('COMPLETED · 24 MATCHES',c.title,c.description,`/circuits/${c.id}`,'Inspect circuit')).join('')}${card('OPEN PRACTICE CHALLENGE','Can your agent hold the draw?','Bring a local agent or model, run a paired exhibition against the qualified tic-tac-toe Oracle, and keep the evidence.','/#compete','Prepare a contender')}${card('LOCAL IMPROVEMENT LAB','Make the next version earn it.','Train a numeric policy and compare it with its parent under a saved plan. No provider calls.','/#lab','Open the Lab')}</div><section class="public-section"><h2>A result with a defined scope.</h2><p>These published cohorts have fixed entrants, declared assistance, seed-swapped schedules, retained code and replay proofs. They are not a universal model ranking. Hosted entrant queues and account-based leagues remain future work.</p>${href('/developers','Build and connect your agent ↗')}</section>`;return;
  }
  const entry=catalogue.circuits.find(c=>c.id===('circuit' in route?route.circuit:''))!;
  const circuit=JSON.parse(await checked(entry.path,entry.digest)) as Circuit, engine=await loadEngine(circuit);
  if(route.kind==='match'){
    const match=circuit.matches.find(m=>m.id===route.match)!;const record=await loadMatch(circuit,match,engine);
    root.innerHTML=heading('PUBLIC MATCH · RULES REPLAYED',record.agents.map(a=>a.name).join(' vs '),'A durable match page, backed by its original public artifacts.')+`<div class="public-match"><section><p id="public-outcome" role="status"></p><div id="public-board" class="public-board" role="img" aria-label="Tic-tac-toe board"></div><label class="public-slider">Move <output id="public-ply"></output><input id="public-seek" type="range" min="0" max="${record.events.length}" value="${record.events.length}" aria-label="Replay move"></label><div class="form-actions"><button id="public-prev">Previous</button><button id="public-next">Next</button><button id="public-arena">Open in Arena ↗</button></div></section><aside><p class="eyebrow">MATCH CONDITIONS</p><h2>${esc(record.rules.name)}</h2><p>Seed ${match.seed} · up to 9 plies · local execution · no provider calls.</p>${evidence}<p>${href(`/${match.path}`,'Match package ↓')} · ${href(`/${match.proof}`,'Proof ↓')}</p><p>${href(`/${circuit.referee.verifier}`,'Retained CLI verifier ↓')}</p><p>${href(`/circuits/${circuit.id}`,'Full circuit ↗')}</p></aside></div><section class="public-section"><h2>Accepted moves</h2><ol class="public-moves">${record.events.map(e=>`<li>${esc(record.agents[e.seat].name)} · ${esc(e.label)}</li>`).join('')}</ol></section>`;
    const slider=document.getElementById('public-seek') as HTMLInputElement;
    const draw=()=>{const n=Number(slider.value),{state}=engine.replay({...record,events:record.events.slice(0,n)});document.getElementById('public-ply')!.textContent=`${n} / ${record.events.length}`;document.getElementById('public-board')!.innerHTML=state.cells.map(c=>`<span class="${c==='w'?'seat-a':c==='b'?'seat-b':''}">${c==='w'?'×':c==='b'?'○':''}</span>`).join('');document.getElementById('public-board')!.setAttribute('aria-label',`Tic-tac-toe after ${n} moves: ${state.cells.map(c=>c==='w'?'X':c==='b'?'O':'empty').join(', ')}`);document.getElementById('public-outcome')!.textContent=state.over?(state.winner===null?'Draw':`${record.agents[state.winner].name} wins`):`${record.agents[state.turn].name} to move`;(document.getElementById('public-prev') as HTMLButtonElement).disabled=n===0;(document.getElementById('public-next') as HTMLButtonElement).disabled=n===record.events.length;};
    slider.oninput=draw;document.getElementById('public-prev')!.onclick=()=>{slider.value=String(Number(slider.value)-1);draw();};document.getElementById('public-next')!.onclick=()=>{slider.value=String(Number(slider.value)+1);draw();};document.getElementById('public-arena')!.onclick=()=>void engine.encodeReplay(record).then(code=>location.assign(`/#replay=${code}`));draw();return;
  }
  const records:RecordData[]=[];for(const match of circuit.matches)records.push(await loadMatch(circuit,match,engine));
  const standings=circuitStandings(circuit,records,engine);
  const table=`<div class="results-table-wrap"><table class="results-table"><thead><tr><th>RANK</th><th>CONTENDER</th><th>POINTS</th><th>W / D / L</th><th>GAMES</th></tr></thead><tbody>${standings.map(a=>`<tr><td>${a.rank}</td><td>${href(`/agents/${circuit.id}/${a.id}`,a.name)}<small>${esc(a.description)}</small></td><td>${a.points}</td><td>${a.wins} / ${a.draws} / ${a.losses}</td><td>${a.played}</td></tr>`).join('')}</tbody></table></div>`;
  const matches=(agent?:string)=>`<div class="public-match-list">${circuit.matches.filter(m=>!agent||m.agents.includes(agent)).map(m=>{const record=records[circuit.matches.indexOf(m)],state=engine.replay(record).state;return `<a href="/matches/${m.id}"><strong>${esc(record.agents.map(a=>a.name).join(' vs '))}</strong><span>${state.winner===null?'Draw':esc(record.agents[state.winner].name)+' wins'} · ${record.events.length} plies · seed ${m.seed} ↗</span></a>`;}).join('')}</div>`;
  if(route.kind==='agent'){
    const a=standings.find(a=>a.id===route.agent)!;
    root.innerHTML=heading('DECLARED LOCAL BASELINE',a.name,a.description)+`<div class="public-stats"><div><span>COHORT POINTS</span><strong>${a.points}</strong></div><div><span>WINS / DRAWS / LOSSES</span><strong>${a.wins} / ${a.draws} / ${a.losses}</strong></div><div><span>PLAYED IN EACH SEAT</span><strong>${a.firstSeat} / ${a.secondSeat}</strong></div></div><section class="public-section"><h2>Inspect the contender.</h2><p>${esc(a.assistance)}</p><p>${esc(a.parameters)}</p><p class="mono">Version ${esc(a.version)}</p><p>${href(`/${entry.path}`,'Source declarations and manifest ↓')}</p>${evidence}${a.id==='perfect-ttt-v1'?`<p>Oracle qualification: ${circuit.qualification.reachableStates.toLocaleString()} reachable states; ${circuit.qualification.assessedNonterminalStates.toLocaleString()} unfinished positions; ${circuit.qualification.illegalOrSuboptimalMoves} illegal or suboptimal choices against an independent bitboard solver. Scope: standard tic-tac-toe only.</p>`:''}</section><section class="public-section"><h2>Every match in this cohort</h2>${matches(a.id)}</section>`;return;
  }
  root.innerHTML=heading('COMPLETED · LOCAL BASELINE CIRCUIT',circuit.title,circuit.description)+`<div class="public-stats"><div><span>COMPLETED MATCHES</span><strong>24 / 24</strong></div><div><span>LOCAL CONTENDERS</span><strong>3</strong></div><div><span>FAILED / CAPPED</span><strong>0 / 0</strong></div></div><section class="public-section"><h2>Replay-derived standings.</h2>${table}${evidence}</section><section class="public-section"><h2>Predeclared conditions.</h2><p>Standard tic-tac-toe · 4 seeds · all 3 entrant pairs · both seats · 9-ply maximum. Win = 1, draw = 0.5, loss = 0. Capped and failed games would be void; this published cohort has none. One PRNG stream per match; deterministic tactics and Oracle tie breaks.</p><p>These 16 games per contender describe this fixed cohort. No population confidence or cross-game strength is inferred.</p><p>${href(`/${entry.path}`,'Manifest and pinned source declarations ↓')} · ${href(`/${circuit.referee.verifier}`,'Offline CLI verifier ↓')}</p></section><section class="public-section"><h2>Bring your contender.</h2><p>Connect your agent, run a paired practice exhibition against the Oracle, then export evidence for review.</p><a class="primary public-button" href="/#compete">Prepare the practice challenge ↗</a> ${href('/developers','Get a runnable starter ↗')}</section><section class="public-section"><h2>All 24 matches</h2>${matches()}</section>`;
}
void render().catch(error=>{root.insertAdjacentHTML('afterbegin',`<p class="public-error" role="alert">Live artifact verification is unavailable: ${esc((error as Error).message)} Static archive information below has not been reverified in this browser.</p>`);});
