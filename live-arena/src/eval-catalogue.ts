import directory from '../data/evals/catalogue.json';
import snapshots from '../data/evals/rankings.json';

export interface EvalEntry {
  id: string; name: string; category: string; kind: 'benchmark'|'framework';
  summary: string; codeUrl: string; leaderboardUrl: string|null; runUrl: string;
  metric: string; notes: string; access: string; status: string;
}
export interface RankingRow {
  name: string; score: number; detail: string; date: string|null;
  rank: number|null; sourceRowId: string;
}
export interface RankingBoard {
  id: string; evalId: string; title: string; metric: string; unit: string;
  higherIsBetter: boolean; protocol: string; coverage: string; rankMethod: string;
  capturedAt: string; sourceUpdatedAt: string|null; sourceUrl: string; sourceSha256: string;
  artifact: string; artifactSha256: string; rows: RankingRow[];
}
export const evalEntries = directory.entries as EvalEntry[];
export const categories = directory.categories as Record<string,string>;
export const featuredEvals = directory.featured;
export const evalReviewedAt = directory.reviewedAt;
export const rankingBoards = snapshots.boards as RankingBoard[];
export const rankingAttribution = snapshots.attribution;
export function findEvals(query='', category='all', kind='all'): EvalEntry[] {
  const terms=query.toLocaleLowerCase().trim().slice(0,100).split(/\s+/).filter(Boolean);
  return evalEntries.filter(e=>(category==='all'||e.category===category)&&(kind==='all'||e.kind===kind)&&terms.every(t=>`${e.name} ${e.summary} ${e.metric} ${e.notes} ${categories[e.category]}`.toLocaleLowerCase().includes(t)))
    .sort((a,b)=>Number(featuredEvals.includes(b.id))-Number(featuredEvals.includes(a.id))||a.name.localeCompare(b.name));
}
export function rankingRows(board:RankingBoard,query=''):RankingRow[] {
  const needle=query.toLocaleLowerCase().trim().slice(0,100);
  return board.rows.filter(r=>`${r.name} ${r.detail}`.toLocaleLowerCase().includes(needle));
}
export function readShortlist(raw:string|null):string[] {
  if(!raw)return [];
  try {
    if(raw.length>2000)return [];
    const value=JSON.parse(raw);
    if(!Array.isArray(value)||value.length>12||value.some(v=>typeof v!=='string'||!evalEntries.some(e=>e.id===v)))return [];
    return [...new Set(value)];
  } catch{return [];}
}
export function makeEvalPlan(ids:string[]) {
  const chosen=readShortlist(JSON.stringify(ids));
  if(!chosen.length)throw Error('Choose at least one evaluation.');
  return {schema:'builderwars.external-eval-plan.v1',createdAt:new Date().toISOString(),directoryReviewedAt:evalReviewedAt,
    execution:'Not executed; configure and run locally following the upstream project instructions',
    model:{revision:null,provider:null},controls:{datasetRevision:null,prompt:null,seed:null,resourceBudget:null},
    evaluations:chosen.map(id=>{const e=evalEntries.find(x=>x.id===id)!;return {id:e.id,name:e.name,category:e.category,kind:e.kind,sourceUrl:e.codeUrl,runInstructions:e.runUrl,leaderboard:e.leaderboardUrl,metric:e.metric,conditions:e.notes};})};
}
