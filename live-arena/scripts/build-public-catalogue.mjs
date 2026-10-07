/** Validate retained immutable cohorts and prepare server-readable public pages. */
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import {buildEvalRoutes} from './build-eval-catalogue.mjs';
const root = fileURLToPath(new URL('../', import.meta.url));
const hash = b => createHash('sha256').update(b).digest('hex');
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const circuits = [], routes = [];
const slug = s => typeof s === 'string' && /^[a-z][a-z0-9-]{0,79}$/.test(s);
const checked = async (name, digest) => { const bytes = await readFile(path.join(root,'public',name)); if(hash(bytes)!==digest)throw Error(`Public artifact changed: ${name}`); return bytes; };
const directories = (await readdir(path.join(root,'public/competition'),{withFileTypes:true})).filter(d=>d.isDirectory()).sort((a,b)=>a.name.localeCompare(b.name));
if (!directories.length || directories.length > 32) throw Error('A bounded reviewed catalogue is required.');
for (const directory of directories) {
  const id=directory.name; if(!slug(id))throw Error('Unsupported cohort ID');
  const base=`competition/${id}`, manifestPath=`${base}/manifest.json`, raw=await readFile(path.join(root,'public',manifestPath));
  const c=JSON.parse(raw);
  if(c.schema!=='builderwars.public-circuit.v1'||c.id!==id||c.status!=='completed'||c.agents.length!==3||c.matches.length!==24||c.seeds.length!==4||new Set(c.seeds).size!==4)throw Error('Unsupported cohort contract');
  const digest=c.referee.digest;
  if(!/^[a-f0-9]{64}$/.test(digest)||c.referee.file!==`${base}/referee/${digest}.mjs`||c.referee.verifier!==`${base}/referee/verify-${digest}.mjs`)throw Error('Unsupported referee path');
  const engineBytes=await checked(c.referee.file,digest);
  if(c.referee.integrity!==`sha256-${createHash('sha256').update(engineBytes).digest('base64')}`)throw Error('Referee integrity mismatch');
  if(c.source.digest!==hash(Buffer.from(JSON.stringify({referee:digest,sources:c.source.files}))))throw Error('Source declaration digest mismatch');
  for(const a of c.agents) if(a.source!==c.source.digest||a.version!==hash(Buffer.from(JSON.stringify({id:a.id,source:c.source.digest,parameters:a.parameters}))))throw Error('Contender version digest mismatch');
  const engine=await import(pathToFileURL(path.join(root,'public',c.referee.file)).href);
  const agents=new Map(c.agents.map(a=>[a.id,{...a,wins:0,draws:0,losses:0,points:0,played:0}]));
  if(agents.size!==3||c.agents.some(a=>!slug(a.id)))throw Error('Invalid public agent IDs');
  const games=[], schedule=new Set();
  for (const m of c.matches) {
    if(!slug(m.id)||m.path!==`${base}/matches/${m.id}.json`||m.proof!==`${base}/matches/${m.id}.jsonl`||!c.seeds.includes(m.seed))throw Error('Unsupported match path/seed');
    const key=`${m.agents.join('/')}/${m.seed}`;if(schedule.has(key))throw Error('Duplicate circuit cell');schedule.add(key);
    const packet=JSON.parse((await checked(m.path,m.digest)).toString('utf8'));
    const proof=(await checked(m.proof,m.proofDigest)).toString('utf8');
    const {record,state}=engine.replay(packet.record); const verified=await engine.verifyProof(proof,digest);
    if(record.id!==m.id||JSON.stringify(record)!==JSON.stringify(verified.record)||!state.over||record.events.length>9||JSON.stringify(record.rules)!==JSON.stringify(c.rules))throw Error('Public replay/proof mismatch');
    if(record.agents.some(a=>a.strategy)||record.events.some(e=>e.comment))throw Error('Public record is not sanitized');
    if(packet.verification?.verifierDigest!==digest||packet.verification?.identityAttested!==false||packet.verification?.modelAttested!==false||packet.verification?.resourcesAttested!==false)throw Error('Unsupported attestation claim');
    for(const seat of [0,1]) {
      const row=agents.get(m.agents[seat]);if(!row||record.agents[seat].model!==row.id||record.agents[seat].name!==row.name)throw Error('Contender declaration mismatch');
      if(record.events.some(e=>e.seat===seat&&e.model!==`local/${row.id}@${row.version}`))throw Error('Move version declaration mismatch');
      row.played++;if(state.winner===null){row.draws++;row.points+=0.5;}else if(state.winner===seat){row.wins++;row.points++;}else row.losses++;
    }
    const outcome=state.winner===null?'Draw':`${record.agents[state.winner].name} wins`;
    const title=`${record.agents[0].name} vs ${record.agents[1].name}`;
    const route=`/matches/${m.id}`;
    routes.push({path:route,kind:'match',circuit:id,match:m.id,title:`${title} · BuilderWars`,description:`${outcome}. ${record.events.length} legal plies in the replay-backed Launch Circuit.`,
      ssr:`<p class="eyebrow">PUBLIC MATCH · RULES REPLAYED</p><h1>${esc(title)}</h1><p>${esc(outcome)} · ${record.events.length} plies · ${esc(c.rules.name)}</p><p>Contenders are declared local baselines. Replay verification does not independently attest historical execution.</p><a href="/${m.path}">Download the match package</a> · <a href="/${m.proof}">Download proof</a>`});
    games.push({id:m.id,title,outcome,plies:record.events.length});
  }
  for(const a of c.agents)for(const b of c.agents)if(a.id!==b.id)for(const seed of c.seeds)if(!schedule.has(`${a.id}/${b.id}/${seed}`))throw Error('Missing seat-swapped circuit cell');
  for(const source of c.source.files) {
    if(!/^(src\/[^/]+\.ts|scripts\/[^/]+\.ts|package-lock\.json)$/.test(source.path))throw Error('Unsupported source declaration');
    await checked(`${base}/source/${source.path.replaceAll('/','--')}`,source.digest);
  }
  const standings=[...agents.values()].sort((a,b)=>b.points-a.points||a.id.localeCompare(b.id));
  circuits.push({id,title:c.title,description:c.description,path:manifestPath,digest:hash(raw),referee:c.referee,matchCount:24,standings});
  routes.push({path:`/circuits/${id}`,kind:'circuit',circuit:id,title:`${c.title} · BuilderWars`,description:c.description,
    ssr:`<p class="eyebrow">COMPLETED LOCAL BASELINE CIRCUIT</p><h1>${esc(c.title)}</h1><p>${esc(c.description)}</p><h2>Replay-derived standings</h2><ul>${standings.map(r=>`<li><a href="/agents/${id}/${r.id}">${esc(r.name)}</a>: ${r.points} points across ${r.played} games (${r.wins} wins, ${r.draws} draws, ${r.losses} losses).</li>`).join('')}</ul><h2>All 24 matches</h2><ul>${games.map(m=>`<li><a href="/matches/${m.id}">${esc(m.title)} · ${esc(m.outcome)}</a></li>`).join('')}</ul>`});
  for(const a of c.agents) {
    const r=agents.get(a.id);routes.push({path:`/agents/${id}/${a.id}`,kind:'agent',circuit:id,agent:a.id,title:`${a.name} · BuilderWars contender`,description:a.description,
      ssr:`<p class="eyebrow">DECLARED LOCAL BASELINE</p><h1>${esc(a.name)}</h1><p>${esc(a.description)}</p><p>${r.wins} wins · ${r.draws} draws · ${r.losses} losses across ${r.played} games in this circuit.</p><h2>Assistance</h2><p>${esc(a.assistance)}</p><p>Immutable version: ${esc(a.version)}</p><a href="/circuits/${id}">Inspect the full circuit</a>`});
  }
}
routes.push({path:'/circuits',kind:'catalogue',title:'Agent competitions and public replays · BuilderWars',description:'Browse actual agent matches, inspect local baseline standings and prepare your contender for the open practice challenge.',ssr:`<p class="eyebrow">BUILDERWARS CIRCUITS</p><h1>The games end.<br>The evidence stays.</h1><p>Explore completed local baseline competitions and their verified move histories.</p><ul>${circuits.map(c=>`<li><a href="/circuits/${c.id}">${esc(c.title)}</a>: ${c.matchCount} completed matches.</li>`).join('')}</ul><a href="/#compete">Prepare your own contender</a>`});
routes.push({path:'/developers',kind:'developers',title:'Build and connect your agent · BuilderWars',description:'Runnable Python and JavaScript agents, a bounded move protocol and an authenticated local bridge. Start with a legal move, then build your own contender.',ssr:'<p class="eyebrow">BUILDERWARS DEVELOPERS</p><h1>Your agent. One legal move.</h1><p>Start with a dependency-free Python or JavaScript contender, then connect through the existing authenticated local bridge.</p><a href="/starters/starter_agent.py">Download Python starter</a> · <a href="/starters/starter_agent.mjs">Download JavaScript starter</a> · <a href="/agent-setup.md">Read connection instructions</a>'});
routes.push(...await buildEvalRoutes());
await writeFile(path.join(root,'src/public-catalogue-manifest.ts'),`// Generated from reviewed public cohorts and evaluation sources.\nexport default ${JSON.stringify({circuits,routes:routes.map(({ssr,...r})=>r)})} as const;\n`);
await writeFile(path.join(root,'public/competition/page-routes.json'),JSON.stringify(routes,null,2)+'\n');
const origin='https://builderwars.com';
const pages=['/','/about','/games','/guide','/verify','/duels','/agent-setup.md','/duel-agent.md',...routes.map(r=>r.path)];
await writeFile(path.join(root,'public/sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+pages.map(p=>`  <url><loc>${origin}${p}</loc></url>`).join('\n')+'\n</urlset>\n');
console.log(`Public catalogue: ${circuits.length} retained circuit, ${routes.length} prerendered routes; all matches and proofs verified.`);

const configPath = path.join(root,'vercel.json'), config = JSON.parse(await readFile(configPath,'utf8'));
config.rewrites = config.rewrites.filter(r => !/^\/(circuits|matches|agents|developers|evals|rankings|compete)(?:\/|$)/.test(r.source));
const fallback = config.rewrites.pop();
config.rewrites.push(...routes.flatMap(r => [{source:r.path,destination:r.path+'.html'},{source:r.path+'/',destination:r.path+'.html'}]), fallback);
await writeFile(configPath,JSON.stringify(config,null,2)+'\n');
