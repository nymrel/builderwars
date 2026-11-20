/* A local, offline view over the replayable AgentWorld agency policy. */
(function () {
  'use strict';
  const E = globalThis.Agentworld, A = globalThis.AgentworldAgency, R = globalThis.AgentworldReturn;
  const $ = (id) => document.getElementById(id);
  const notice = (message, error = false) => { $('notice').textContent = message; $('notice').className = 'notice' + (error ? ' error' : ''); $('notice').hidden = false; };
  if (!E || !A || !R) { notice('The world could not start. Open this page with its companion files together.', true); return; }
  const GOALS = { help: 'Bring supplies home', explore: 'Explore', rest: 'Recover' };
  const COLORS = ['#ad613b', '#43898a', '#8b773c', '#637ba2'];
  const profiles = A.PROFILES;
  let session = A.create({ seed: 481516, mode: 'cooperative' });
  let selected = profiles[0].id, timer = null, playing = false, revision = 0, pending = null, showAll = false, importToken = 0;
  const checkpoint = R.createStore(() => globalThis.localStorage);
  let saved = checkpoint.load(), saving = false;
  const profile = (id) => profiles.find((p) => p.id === id) || { id, name: id, role: 'Companion', description: '' };
  const color = (id) => COLORS[Math.max(0, E.ORDER.indexOf(id)) % COLORS.length];
  const goal = (value) => GOALS[value] || 'Finding a direction';
  function renderReturn() {
    $('save-visit').checked = saving;
    $('forget-visit').disabled = saved.raw === null || saved.raw === undefined;
    $('return-banner').hidden = !saved.session || saving;
    if (saved.session) {
      const world = saved.session.world, last = saved.session.history.at(-1);
      $('return-recap').textContent = `Your last visit ended after ${world.turn} choices, with ${world.scores.amber + world.scores.tide} of 16 supplies home.` +
        (last ? ` ${profile(last.actor).name}'s last plan: ${goal(last.goal)}. Last choice: ${actionText(last.action).toLowerCase()}.` : ' The companions have not taken their first step yet.');
    }
    $('save-status').textContent = saved.error || (saving && saved.session
      ? `Saved through choice ${saved.session.world.turn} in this browser. Export for a separate backup.`
      : saved.session ? `Saving is off. The earlier visit at choice ${saved.session.world.turn} is kept; your current progress is not being saved.`
      : 'Device saving is off. Export a file to keep this visit.');
  }
  function saveCurrentVisit() {
    if (!saving) return;
    try {
      const raw = checkpoint.save(session, saved.raw);
      saved = { raw, session: A.verify(raw), error: null };
    } catch {
      saving = false;
      saved = checkpoint.load();
      notice('This progress could not be saved or confirmed. Export this visit to keep your current progress.', true);
    }
    renderReturn();
  }
  const position = (a) => `${String.fromCharCode(65 + a.x)}${a.y + 1}`;
  const svgNode = (tag, attrs = {}, text) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const htmlNode = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
  function initials(name) { return name.slice(0, 1).toUpperCase(); }
  function pause() { const restoreFocus = document.activeElement === $('stop'); playing = false; if (timer !== null) clearTimeout(timer); timer = null; renderControls(); if (restoreFocus && !document.hidden) (session.world.status === 'running' ? $('autoplay') : $('export-visit')).focus({preventScroll:true}); }
  function renderControls() {
    const done = session.world.status !== 'running';
    $('autoplay').hidden = playing;
    $('stop').hidden = !playing;
    $('autoplay').disabled = done;
    $('next-choice').disabled = done;
    $('suggest-step').disabled = done;
    $('suggestion').disabled = done;
    $('world-status').className = 'status' + (playing ? ' running' : '');
    $('status-label').textContent = done ? (session.world.status === 'complete' ? 'All supplies home' : 'Turn limit reached') : playing ? 'Unfolding' : session.world.turn ? 'Paused' : 'Ready';
    const name = profile(E.active(session.world)).name;
    const next = $('next-actor'); next.replaceChildren();
    if (done) next.textContent = session.world.status === 'complete' ? 'Every supply is home. A shared story, complete.' : `240 choices made; ${E.remaining(session.world)} supplies still to bring home. Export this visit or begin another.`;
    else { const actor = session.actors.find((a) => a.id === E.active(session.world)); next.append('Next: ', htmlNode('strong', '', name), ` · Current plan: ${goal(actor.goal)} · Energy ${actor.energy}/${A.MAX_ENERGY || 6}`); }
    $('suggestion-label').textContent = done ? 'This visit has finished' : `A suggestion for ${name}`;
  }
  function actionText(action) {
    if (!action) return 'Considering the world';
    if (action.type === 'move') return `Moved ${action.direction}`;
    if (action.type === 'collect') return 'Picked up a supply';
    if (action.type === 'deliver') return 'Brought a supply home';
    return 'Waited in place';
  }
  function renderMap() {
    const svg = $('world-map'), world = session.world;
    const focusedId = svg.contains(document.activeElement) ? document.activeElement.id : null;
    svg.querySelectorAll(':scope > :not(title):not(desc)').forEach((n) => n.remove());
    const originX = 84, originY = 34, cell = 54;
    const center = (x, y) => [originX + x * cell + cell / 2, originY + y * cell + cell / 2];
    const visited = new Set(session.actors.flatMap((a) => a.visited));
    svg.append(svgNode('rect', { x: 0, y: 0, width: 600, height: 500, fill: '#e5ebd8' }));
    // A decorative forest edge sits outside the fully walkable clearing.
    const tree = (x, y, scale, fill) => {
      const g = svgNode('g', { transform: `translate(${x} ${y}) scale(${scale})`, 'aria-hidden': 'true' });
      g.append(svgNode('path', { d: 'M0 20V32', stroke: '#8d9873', 'stroke-width': 2 }), svgNode('path', { d: 'M0 -9L-13 13H-8L-17 27H17L8 13H13Z', fill })); svg.append(g);
    };
    [[22,35,1.2],[54,72,.8],[19,124,1],[48,166,.65],[18,221,1.1],[48,275,.8],[20,328,1],[50,381,.8],[17,438,1.25],[558,39,1],[585,88,.8],[553,140,1.1],[579,199,.75],[554,246,1],[585,302,.8],[557,359,1.2],[583,415,.75],[553,453,.9]].forEach(([x,y,s],i)=>tree(x,y,s,i%2 ? '#b6c4a0' : '#a4b793'));
    svg.append(svgNode('rect', { x: originX - 4, y: originY - 4, width: cell * 8 + 8, height: cell * 8 + 8, rx: 12, fill: '#c6d5b0' }));
    for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
      const [cx, cy] = center(x, y), seen = visited.has(`${x},${y}`), k = (x * 31 + y * 19 + world.config.seed) % 7;
      svg.append(svgNode('rect', { x: originX + x * cell + .6, y: originY + y * cell + .6, width: cell - 1.2, height: cell - 1.2, rx: 3, fill: seen ? '#dce6c5' : k < 2 ? '#cddbb8' : '#d3dfbf' }));
      if (seen) svg.append(svgNode('circle', { cx, cy, r: 1.6, fill: '#a0b28d' }));
      else if (k < 3) svg.append(svgNode('path', { d: `M${cx - 12} ${cy + 9}l-2 -5m2 5l3 -3M${cx + 14} ${cy - 8}l-2 -4m2 4l3 -2`, stroke: '#b7c9a0', 'stroke-width': 1.4, 'stroke-linecap': 'round', fill: 'none' }));
    }
    for (let i = 0; i < 8; i++) {
      svg.append(svgNode('text', { x: originX + i * cell + cell / 2, y: 20, fill: '#7b8e6c', 'font-size': 9, 'font-family': 'Arial,sans-serif', 'text-anchor': 'middle' }, String.fromCharCode(65 + i)));
      svg.append(svgNode('text', { x: originX - 15, y: originY + i * cell + cell / 2 + 3, fill: '#7b8e6c', 'font-size': 9, 'font-family': 'Arial,sans-serif', 'text-anchor': 'middle' }, i + 1));
    }
    for (const base of world.bases) {
      const [x,y] = center(base.x, base.y), fill = base.team === 'amber' ? '#b7794c' : '#5b9290';
      const g = svgNode('g', { 'aria-hidden': 'true' });
      g.append(svgNode('ellipse', { cx: x, cy: y + 16, rx: 19, ry: 7, fill: '#b1c39a' }),svgNode('path', { d: `M${x-15} ${y-3}L${x} ${y-18}L${x+15} ${y-3}V${y+14}H${x-15}Z`, fill: '#f2edd8', stroke: '#657857', 'stroke-width': 1.4 }),svgNode('path', { d: `M${x-19} ${y-2}L${x} ${y-22}L${x+19} ${y-2}`, fill, stroke: fill, 'stroke-width': 3, 'stroke-linejoin': 'round' }),svgNode('rect', { x: x-4, y:y+2, width:8, height:12, rx:1, fill:'#627653' })); svg.append(g);
    }
    for (const supply of world.supplies.filter((s) => s.amount > 0)) {
      const [x,y] = center(supply.x, supply.y), g = svgNode('g', { 'aria-hidden': 'true' });
      g.append(svgNode('ellipse', { cx:x, cy:y+11, rx:13, ry:5, fill:'#b8c89d' }),svgNode('path', { d:`M${x} ${y-11}L${x+11} ${y-5}V${y+8}L${x} ${y+14}L${x-11} ${y+8}V${y-5}Z`, fill:'#c7914c',stroke:'#9f713e','stroke-width':1.1 }),svgNode('path',{d:`M${x-11} ${y-5}L${x} ${y+1}L${x+11} ${y-5}M${x} ${y+1}V${y+14}`,fill:'none',stroke:'#f3dfab','stroke-width':1.2}));
      if (supply.amount > 1) g.append(svgNode('circle',{cx:x+12,cy:y-11,r:7,fill:'#f9f4e0'}),svgNode('text',{x:x+12,y:y-8,'text-anchor':'middle','font-size':9,'font-family':'Arial,sans-serif',fill:'#80552f'},supply.amount));
      svg.append(g);
    }
    for (const agent of world.agents) {
      const peers = world.agents.filter((a) => a.x === agent.x && a.y === agent.y), index = peers.findIndex((a) => a.id === agent.id);
      let [x,y] = center(agent.x,agent.y);
      if (peers.length > 1) { x += index % 2 ? 12 : -12; y += peers.length > 2 ? (index < 2 ? -11 : 11) : 0; }
      const radius = peers.length > 1 ? 11 : 15, p = profile(agent.id), active = world.status === 'running' && E.active(world) === agent.id;
      const g = svgNode('g', { id:`map-${agent.id}`,class:'map-agent',role:'button',tabindex:0,'aria-label':`${p.name}, ${position(agent)}, ${agent.carry ? 'carrying a supply' : 'not carrying supplies'}. Show point of view.`,'aria-pressed':selected === agent.id,'data-agent-id':agent.id });
      g.append(svgNode('circle',{cx:x,cy:y,r:22,fill:'transparent'}));
      if (active) g.append(svgNode('circle', { cx:x,cy:y,r:radius+6,fill:'none',stroke:color(agent.id),'stroke-width':1.3,'stroke-dasharray':'2 3' }));
      g.append(svgNode('ellipse',{cx:x,cy:y+radius,rx:radius,ry:5,fill:'#849870',opacity:.45}),svgNode('circle',{class:'agent-ring',cx:x,cy:y,r:radius,fill:color(agent.id),stroke:selected===agent.id?'#fffbec':'#f0eddb','stroke-width':selected===agent.id?3:2}),svgNode('text',{x,y:y+4.5,'text-anchor':'middle','font-size':radius+1,'font-family':'Georgia,serif',fill:'#fff9e6','pointer-events':'none'},initials(p.name)));
      if (agent.carry) g.append(svgNode('path',{d:`M${x+radius-1} ${y+radius-9}l5 5 -5 5 -5 -5Z`,fill:'#d6a04b',stroke:'#fff5d5','stroke-width':1.2}));
      const choose = () => { selected = agent.id; renderSelection(); };
      g.addEventListener('click', choose); g.addEventListener('keydown',(event)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();choose();}});
      svg.append(g);
    }
    if (focusedId && $(focusedId)) $(focusedId).focus({ preventScroll:true });
    $('map-text-summary').textContent = `World seed ${world.config.seed}. ${world.scores.amber + world.scores.tide} of 16 supplies delivered. Columns A–H, rows 1–8. Amber home is A4; Tide home is H5.`;
    $('map-text').replaceChildren(...world.agents.map((agent)=>htmlNode('li','',`${profile(agent.id).name}: ${position(agent)}, ${agent.carry ? 'carrying one supply' : 'empty-handed'}. Goal: ${goal(session.actors.find((a)=>a.id===agent.id).goal)}.`)),htmlNode('li','',`Supplies on the ground: ${world.supplies.filter((s)=>s.amount).map((s)=>`${position(s)} (${s.amount})`).join(', ') || 'none'}.`));
  }
  function createCards() {
    const cards = profiles.map((p) => {
      const card = htmlNode('button','agent-card'); card.type='button'; card.id=`card-${p.id}`; card.dataset.agentId=p.id;
      const top = htmlNode('span','agent-top'), avatar=htmlNode('span','avatar',initials(p.name)), identity=htmlNode('span',''); avatar.style.backgroundColor=color(p.id); avatar.setAttribute('aria-hidden','true');
      identity.append(htmlNode('span','agent-name',p.name),document.createElement('br'),htmlNode('span','agent-role',p.role));
      const next=htmlNode('span','agent-next','Next');next.id=`next-${p.id}`;next.setAttribute('aria-hidden','true');top.append(avatar,identity,next);
      const currentGoal=htmlNode('span','agent-goal');currentGoal.id=`goal-${p.id}`;
      const energy=htmlNode('span','energy-label');energy.append(htmlNode('span','','Energy'));const value=htmlNode('span','');value.id=`energy-${p.id}`;energy.append(value);
      const track=htmlNode('span','energy-track');track.id=`track-${p.id}`;track.setAttribute('aria-hidden','true');
      for(let i=0;i<(A.MAX_ENERGY || 6);i++)track.append(htmlNode('span','energy-unit'));
      card.append(top,currentGoal,energy,track);card.addEventListener('click',()=>{selected=p.id;renderSelection();});return card;
    });
    $('agent-cards').replaceChildren(...cards);
  }
  function renderCards() {
    for(const actor of session.actors){
      const p=profile(actor.id), card=$(`card-${actor.id}`), next=session.world.status==='running'&&E.active(session.world)===actor.id;
      card.classList.toggle('selected',actor.id===selected);card.setAttribute('aria-pressed',String(actor.id===selected));card.setAttribute('aria-label',`${p.name}, ${p.role}. ${goal(actor.goal)}. Energy ${actor.energy} of ${A.MAX_ENERGY || 6}.${next?' Next to choose.':''} Show point of view.`);
      $(`next-${actor.id}`).hidden=!next;$(`goal-${actor.id}`).textContent=goal(actor.goal);$(`energy-${actor.id}`).textContent=`${actor.energy} / ${A.MAX_ENERGY || 6}`;
      [...$(`track-${actor.id}`).children].forEach((unit,i)=>unit.classList.toggle('filled',i<actor.energy));
    }
    const p=profile(selected), actor=session.actors.find((a)=>a.id===selected), body=session.world.agents.find((a)=>a.id===selected), last=[...session.history].reverse().find((h)=>h.actor===selected);
    $('detail-title').textContent=`${p.name}'s point of view`;$('detail-description').textContent=p.description;
    $('detail-reason').textContent=last?last.reason:'A new place. A chance to choose what comes next.';
    $('detail-memory').textContent=`${new Set(actor.visited).size} places remembered`;$('detail-carry').textContent=body.carry?'Carrying a supply':'Hands free';
  }
  function renderLog() {
    const history=session.history, choices=showAll?history:[...history].slice(-12);
    const latest=history[history.length-1];
    $('latest-choice').hidden=!latest;
    if(latest){
      $('latest-title').textContent=`${profile(latest.actor).name} ${latest.request?(latest.response==='declined'?'declined your suggestion':'accepted your suggestion'):latest.commitment==='suggestion'?'continued your earlier suggestion':'made a choice'}.`;
      $('latest-reason').textContent=latest.reason;
      $('latest-action').textContent=`${actionText(latest.action)} · Energy ${latest.energyBefore} → ${latest.energyAfter}`;
    }
    $('log-empty').hidden=history.length>0;$('log-count').textContent=history.length?`${history.length} ${history.length===1?'choice':'choices'}`:'No choices yet';$('log-more-wrap').hidden=history.length<=12;$('log-more').textContent=showAll?'Show the latest 12 choices':`Show all ${history.length} choices`;
    $('decision-log').start=history.length;
    $('decision-log').replaceChildren(...[...choices].reverse().map((entry)=>{
      const item=htmlNode('li','decision'), number=htmlNode('span','decision-number',String(entry.turn+1).padStart(2,'0'));number.setAttribute('aria-hidden','true');const content=htmlNode('div',''), heading=htmlNode('div','decision-heading');
      heading.append(htmlNode('strong','',`${profile(entry.actor).name} · ${goal(entry.goal)}`));
      if(entry.request)heading.append(htmlNode('span',`decision-response ${entry.response==='declined'?'declined':''}`,entry.response==='declined'?'Declined suggestion':'Accepted suggestion'));
      else heading.append(htmlNode('span','decision-response',entry.commitment==='suggestion'?'Following suggestion':entry.commitment==='delivery'?'Delivery commitment':entry.commitment==='recovery'?'Recovery':'Own choice'));
      content.append(heading);
      if(entry.request)content.append(htmlNode('p','decision-request',`You suggested: ${goal(entry.request)}.`));
      content.append(htmlNode('p','decision-reason',entry.reason),htmlNode('p','decision-consequence',`${actionText(entry.action)} · Energy ${entry.energyBefore} → ${entry.energyAfter}`));item.append(number,content);return item;
    }));
  }
  function renderSelection() { renderMap();renderCards(); }
  function render() {
    const world=session.world, visited=new Set(session.actors.flatMap((a)=>a.visited));
    $('deliveries').replaceChildren(String(world.scores.amber+world.scores.tide)+' ',htmlNode('small','','/ 16'));$('turn-count').replaceChildren(String(world.turn)+' ',htmlNode('small','','/ 240'));$('explored-count').replaceChildren(String(visited.size)+' ',htmlNode('small','','/ 64'));
    $('seed-label').textContent=`Seed ${world.config.seed}`;$('visit-seed').textContent=`World seed ${world.config.seed}`;
    renderControls();renderMap();renderCards();renderLog();renderReturn();
  }
  function step(request=null) {
    if(session.world.status!=='running')return;
    try{session=A.advance(session,request);revision++;saveCurrentVisit();render();if(session.world.status!=='running')pause();}
    catch(error){pause();notice(error.message||'This choice could not be completed.',true);}
  }
  function schedule() {
    if(!playing||document.hidden)return;
    timer=setTimeout(()=>{timer=null;if(!playing||document.hidden)return;step();if(playing)schedule();},1100);
  }
  function exportVisit() {
    try{
      const text=JSON.stringify(A.pack(session),null,2);A.verify(text);
      if(new TextEncoder().encode(text).length>E.MAX_BYTES)throw new Error('This visit is too large to export.');
      const url=URL.createObjectURL(new Blob([text],{type:'application/json'}));const anchor=document.createElement('a');anchor.href=url;anchor.download=`builderwars-agentworld-${session.world.config.seed}-turn-${session.world.turn}.json`;document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      notice(`Visit exported at choice ${session.world.turn}. Keep the file to return later.`);
    }catch(error){notice(error.message||'This visit could not be exported.',true);}
  }
  function openDialog(kind, imported=null) {
    if(kind==='new'||kind==='resume')importToken++;
    pause();pending={kind,imported,revision};$('dialog-error').hidden=true;$('seed-field').hidden=kind!=='new';
    $('dialog-title').textContent=kind==='new'?'Begin a new world?':'Open this saved visit?';$('dialog-confirm').textContent=kind==='new'?'Begin new world':'Open saved visit';
    $('dialog-description').textContent=kind==='new'?'Export this visit first if you want to return. A new world replaces the current visit in this page.':`This visit was checked and is ready: seed ${imported.world.config.seed}, ${imported.world.turn} choices. Export your current visit first if you want to keep it.`;
    if (saving || kind === 'resume') $('dialog-description').textContent += ' The opened visit will be saved in this browser, replacing its one device checkpoint.';
    if (kind === 'resume') pending.savedRaw = saved.raw;
    if(kind==='new') {const value=new Uint32Array(1);if(globalThis.crypto&&crypto.getRandomValues)crypto.getRandomValues(value);else value[0]=Date.now()>>>0;$('new-seed').value=String(value[0]||1);}
    $('replace-dialog').showModal();
  }
  $('autoplay').addEventListener('click',()=>{if(session.world.status!=='running'||document.hidden)return;playing=true;renderControls();$('stop').focus({preventScroll:true});schedule();});
  $('stop').addEventListener('click',pause);
  $('next-choice').addEventListener('click',()=>{pause();step();});
  $('suggestion-form').addEventListener('submit',(event)=>{event.preventDefault();pause();step($('suggestion').value);});
  $('log-more').addEventListener('click',()=>{showAll=!showAll;renderLog();});
  $('export-visit').addEventListener('click',exportVisit);$('dialog-export').addEventListener('click',exportVisit);
  $('new-world').addEventListener('click',()=>openDialog('new'));
  $('save-visit').addEventListener('change', () => {
    if (!$('save-visit').checked) { saving = false; renderReturn(); return; }
    const current = checkpoint.load();
    if (current.error) {
      saved = current; saving = false; renderReturn();
      notice('Device saving is unavailable or the saved visit could not be verified. Export your current visit to keep it.', true);
      return;
    }
    const different = saved.session && JSON.stringify(A.pack(session)) !== JSON.stringify(A.pack(saved.session));
    if (current.raw !== saved.raw || (!saving && different)) {
      saved = current; saving = false; renderReturn();
      notice('Resume or forget the saved visit before saving a different visit here. Export your current visit if you want to keep it.', true);
      return;
    }
    saving = true; saveCurrentVisit();
  });
  $('forget-visit').addEventListener('click', () => {
    pause();
    try { checkpoint.forget(saved.raw); saving = false; saved = checkpoint.load(); renderReturn(); notice('Saved visit removed. This page stays open; future choices will not be saved unless you enable saving.'); }
    catch { saving = false; saved = checkpoint.load(); renderReturn(); notice('The saved visit changed or could not be removed. Your current visit is still here.', true); }
  });
  $('resume-visit').addEventListener('click', () => {
    pause(); saved = checkpoint.load(); renderReturn();
    if (!saved.session) return;
    openDialog('resume', saved.session);
  });
  $('import-visit').addEventListener('click',()=>{importToken++;pause();$('import-file').click();});
  $('import-file').addEventListener('change',async(event)=>{
    const file=event.target.files[0];event.target.value='';if(!file)return;pause();const startedRevision=revision, token=++importToken;
    try{
      if(file.size>E.MAX_BYTES)throw new Error('Choose a visit file smaller than 128 KiB.');
      const text=await file.text();if(token!==importToken)return;const imported=A.verify(text);
      if(startedRevision!==revision)throw new Error('Your world changed while the visit was opening. Open the file again when you are ready to replace it.');
      if($('replace-dialog').open)throw new Error('Finish the open world dialog, then open your visit again.');
      openDialog('import',imported);
    }catch(error){if(token===importToken)notice(`Could not open this visit. ${error.message||'The file is not a valid visit.'}`,true);}
  });
  $('dialog-cancel').addEventListener('click',()=>{$('replace-dialog').close();pending=null;});
  $('replace-dialog').addEventListener('cancel',()=>{pending=null;});
  $('dialog-confirm').addEventListener('click',()=>{
    try{
      if(!pending)return;if(pending.revision!==revision)throw new Error('The current world changed. Close this dialog and try again.');
      if(pending.kind==='resume' && checkpoint.load().raw !== pending.savedRaw)throw new Error('The saved visit changed. Close this dialog and choose Resume again.');
      let replacement;
      if(pending.kind==='new'){
        const raw=$('new-seed').value, seed=Number(raw);if(!/^\d+$/.test(raw)||!Number.isSafeInteger(seed)||seed<1||seed>4294967295)throw new Error('Choose a whole-number seed from 1 to 4294967295.');
        replacement=A.create({seed,mode:'cooperative'});
      }else replacement=pending.imported;
      if(pending.kind==='resume')saving=true;
      session=replacement;revision++;selected=profiles[0].id;showAll=false;pending=null;$('replace-dialog').close();$('notice').hidden=true;saveCurrentVisit();render();$('next-choice').focus();
    }catch(error){$('dialog-error').textContent=error.message;$('dialog-error').hidden=false;}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden){const wasPlaying=playing;pause();if(wasPlaying)notice('The world paused while you were away. Let them choose when you are ready.');}});
  globalThis.addEventListener('pagehide',pause);
  globalThis.addEventListener('storage', (event) => {
    if (event.key !== R.KEY && event.key !== null) return;
    pause(); saving = false; saved = checkpoint.load(); renderReturn();
    notice('Device history changed in another tab. This visit is paused and still here; export it before replacing anything.');
  });
  createCards();render();
})();
