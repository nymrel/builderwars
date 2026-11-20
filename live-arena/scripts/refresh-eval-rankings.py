"""Refresh dated score snapshots from fixed public primary sources; never runs evals.

Default fetches are bounded and credential-free. --from-dir uses previously captured
source files for an offline reproduction. No network fetch occurs during app builds.
"""
import argparse,csv,hashlib,html,json,math,re,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'swe':('https://www.swebench.com/','swe.html'),
 'bfcl':('https://gorilla.cs.berkeley.edu/data_overall.csv','bfcl-data.txt'),
 'bfcl-page':('https://gorilla.cs.berkeley.edu/leaderboard.html','bfcl.html'),
 'evalplus':('https://evalplus.github.io/results.json','evalplus-data.txt'),
 'mmlu':('https://huggingface.co/datasets/TIGER-Lab/mmlu_pro_leaderboard_submission/resolve/main/results.csv','mmlu-data.txt'),
 'mmmu':('https://mmmu-benchmark.github.io/leaderboard_data.json','mmmu-data.json'),
 'hle':('https://lastexam.ai/','hle.html'),
 'tau':('https://taubench.com/','tau.html'),
 'lcb':('https://livecodebench.github.io/performances_generation.json','lcb-data.txt'),
 'matharena':('https://matharena.ai/','matharena.html'),
}

def text(s):return html.unescape(re.sub(r'<[^>]+>',' ',s)).strip()
def clean(s):return ' '.join(text(str(s)).split())
def percentage(s):
 n=float(str(s).rstrip('%'))
 if not math.isfinite(n) or not 0<=n<=100:raise ValueError('Invalid percentage')
 return round(n,4)
def rows_of_table(s):
 return [[clean(x) for x in re.findall(r'<td\b[^>]*>(.*?)</td>',tr,re.S)] for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',s,re.S) if '<td' in tr]
def rank_rows(rows):
 rows.sort(key=lambda x:(-x['score'],x['name'].casefold(),x.get('detail','')))
 prior=None;rank=0
 for i,row in enumerate(rows):
  if row['score']!=prior:rank=i+1;prior=row['score']
  row['rank']=rank
 return rows
def make_row(name,score,detail='',date=None,rank=None):
 row={'name':clean(name),'score':percentage(score),'detail':clean(detail),'date':date,'rank':rank}
 if not row['name'] or len(row['name'])>240:raise ValueError('Invalid contender name')
 return row

def swe_detail(row):
 parts=[row.get('agent','Agent unspecified'),'Organizer-checked' if row.get('checked') is True else 'Submission']
 if row.get('mini-swe-agent_version'):parts.append('Harness version '+str(row['mini-swe-agent_version']))
 if row.get('reasoning_effort'):parts.append('Reasoning '+str(row['reasoning_effort']))
 parts.extend(str(x) for x in row.get('tags',[]) if str(x).startswith('System:'))
 if row.get('warning'):parts.append(str(row['warning']))
 return ' · '.join(parts)

def capture_time(value):
 if not isinstance(value,str):raise ValueError('Missing original capture timestamp')
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',value):raise ValueError('Expected original UTC capture timestamp')
 parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
 if parsed>datetime.now(timezone.utc):raise ValueError('Capture timestamp is in the future')
 return value

def read_capture_metadata(directory):
 metadata=json.loads((directory/'capture-metadata.json').read_text())
 if not isinstance(metadata,dict) or not isinstance(metadata.get('sources'),dict) or set(metadata['sources'])!=set(SOURCES):raise ValueError('Missing original source metadata')
 capture_time(metadata.get('capturedAt'))
 for key,(url,file) in SOURCES.items():
  source=metadata['sources'][key]
  if not isinstance(source,dict) or source.get('url')!=url or source.get('file')!=file or not isinstance(source.get('sha256'),str) or not re.fullmatch('[a-f0-9]{64}',source['sha256']):raise ValueError('Invalid original source metadata: '+key)
 return metadata

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--from-dir',type=Path);parser.add_argument('--save-sources',type=Path,help='Retain fetched bytes and original capture metadata');args=parser.parse_args()
 if args.from_dir and args.save_sources:parser.error('Use --from-dir or --save-sources, not both')
 metadata=read_capture_metadata(args.from_dir) if args.from_dir is not None else None
 captured=capture_time(metadata['capturedAt']) if args.from_dir is not None else datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
 data={};digests={}
 for key,(url,file) in SOURCES.items():
  if args.from_dir:raw=(args.from_dir/file).read_bytes()
  else:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BuilderWars-EvalSnapshots/1.0 (+https://builderwars.com/evals)'}),timeout=30) as r:raw=r.read(8_000_001)
  if len(raw)>8_000_000:raise ValueError('Source exceeds size bound')
  data[key]=raw.decode('utf-8-sig');digests[key]=hashlib.sha256(raw).hexdigest()
  if metadata:
   original=metadata['sources'][key]
   if original['url']!=url or original['sha256']!=digests[key] or original['file']!=file:raise ValueError('Captured source metadata mismatch: '+key)
  elif args.save_sources:
   args.save_sources.mkdir(parents=True,exist_ok=True);(args.save_sources/file).write_bytes(raw)
 if args.save_sources:
  (args.save_sources/'capture-metadata.json').write_text(json.dumps({'capturedAt':captured,'sources':{k:{'url':v[0],'file':v[1],'sha256':digests[k]} for k,v in SOURCES.items()}},indent=2)+'\n')
 boards=[];artifacts={}
 def board(id,evalId,title,key,metric,protocol,rows,updated=None,sort=True,rankMethod='score-ties',coverage='All source rows with this metric'):
  if not 1<=len(rows)<=500:raise ValueError('Unsupported row count: '+id)
  for index,row in enumerate(rows):row['sourceRowId']=row.get('sourceRowId',str(index+1))
  if sort:rank_rows(rows)
  if len({x['sourceRowId'] for x in rows})!=len(rows):raise ValueError('Duplicate source row ID: '+id)
  source={'schema':'builderwars.eval-source-extract.v1','id':id,'sourceUrl':SOURCES[key][0],'sourceSha256':digests[key],'capturedAt':captured,'extraction':'Retained reported score columns; not complete source page or execution evidence','rows':rows}
  raw=(json.dumps(source,ensure_ascii=False,indent=2)+'\n').encode();file=f'evals/sources/{id}.json';artifacts[file]=raw
  boards.append({'id':id,'evalId':evalId,'title':title,'metric':metric,'unit':'%','higherIsBetter':True,'protocol':protocol,'coverage':coverage,'rankMethod':rankMethod,'capturedAt':captured,'sourceUpdatedAt':updated,'sourceUrl':SOURCES[key][0],'sourceSha256':digests[key],'artifact':file,'artifactSha256':hashlib.sha256(raw).hexdigest(),'rows':rows})
 swe=json.loads(re.search(r'<script[^>]*id="leaderboard-data"[^>]*>(.*?)</script>',data['swe'],re.S)[1])
 verified=next(x['results'] for x in swe if x['name']=='Verified')
 for mini in [False,True]:
  selected=[x for x in verified if not mini or x.get('agent')=='mini-SWE-agent']
  rows=[{**make_row(x['name'],x['resolved'],swe_detail(x),x.get('date')),'sourceRowId':x['folder']} for x in selected]
  board('swe-mini' if mini else 'swe-verified','swe-bench-verified','SWE-bench Verified · mini-SWE-agent' if mini else 'SWE-bench Verified · agent systems','swe','Resolved tasks','500 Verified tasks; '+('mini-SWE-agent submissions only, including declared agent versions and settings.' if mini else 'Different submitted agent systems and model configurations; this is a system ranking.'),rows,coverage='mini-SWE-agent subset of official Verified data' if mini else 'All official Verified submissions with a reported score')
 bfcl=list(csv.DictReader(data['bfcl'].splitlines()))
 updated=re.search(r'Last Updated:\s*(\d{4}-\d{2}-\d{2})',clean(data['bfcl-page']))
 board('bfcl-v4','bfcl','BFCL V4 · overall','bfcl','Overall accuracy','V4 overall score; FC and Prompt calling modes remain in model names. Estimated benchmark cost/latency are not independent billing evidence.',[make_row(x['Model'],x['Overall Acc'],x['Organization']+' · '+x['License'],rank=int(x['Rank'])) for x in bfcl],updated=updated[1] if updated else None,sort=False,rankMethod='source')
 ep=json.loads(data['evalplus'])
 for key,id,title in [('humaneval+','humaneval-plus','EvalPlus · HumanEval+'),('mbpp+','mbpp-plus','EvalPlus · MBPP+')]:
  board(id,'evalplus',title,'evalplus','Pass@1','Greedy decoding; HumanEval+ 0.1.10 and MBPP+ 0.2.0 (399 hand-verified MBPP tasks). Chat and completion modes are explicitly noted.',[make_row(k,x['pass@1'][key],'Chat prompting' if x['prompted'] else 'Code completion') for k,x in ep.items() if x['pass@1'][key] is not None])
 mmlu=list(csv.DictReader(data['mmlu'].splitlines()))
 board('mmlu-pro','mmlu-pro','MMLU-Pro · overall','mmlu','Accuracy','Official TIGER-Lab submission table. Source fractions are converted to percentages; source-provided evaluator or Self-Reported labels are retained.',[make_row(x['Models'],float(x['Overall'])*100,x['Data Source']) for x in mmlu])
 mmmu=json.loads(data['mmmu'])['leaderboardData']
 for key,id,title,evalId in [('pro','mmmu-pro','MMMU-Pro · overall','mmmu-pro'),('validation','mmmu-val','MMMU · validation','mmmu')]:
  rows=[]
  for x in mmmu:
   if x['info']['type']=='human_expert' or x.get(key,{}).get('overall') in [None,'-','']:continue
   metric=x[key];rows.append(make_row(x['info']['name'],metric['overall'],x['info']['type']+' · '+metric.get('source','Source-listed'),x['info'].get('date')))
  board(id,evalId,title,'mmmu','Overall accuracy' if key=='pro' else 'Validation accuracy','Official '+title+' column; human expert baselines excluded. Original, Pro, Vision and test scores are not merged.',rows,coverage='All non-human source rows with this metric')
 hle_table=re.search(r'<tbody[^>]*>(.*?)</tbody>',data['hle'],re.S)[1]
 hle_rows=[make_row(x[0],x[1],f'Calibration error {x[2]}% (lower is better)') for x in rows_of_table(hle_table)]
 board('hle','humanitys-last-exam','Humanity’s Last Exam · accuracy','hle','Accuracy','Official homepage model table; underlying prompting and tool settings must be checked at the source. Calibration error is displayed separately.',hle_rows)
 tables=re.findall(r'<table\b[^>]*class="preview-table"[^>]*>(.*?)</table>',data['tau'],re.S)
 if len(tables)!=3:raise ValueError('τ homepage track count changed; review before publishing')
 for table,(id,title,protocol) in zip(tables,[('tau3-banking','τ³-bench · banking text','Banking text with knowledge retrieval.'),('tau3-voice','τ³-bench · voice','Voice across retail, airline, telecom and banking.'),('tau2-text','τ²-bench · text','Legacy τ² text across retail, airline and telecom; separate from the updated τ³ tasks.')]):
  rows=[]
  for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S):
   if 'preview-model-name' not in tr:continue
   name=re.search(r'class="preview-model-name"[^>]*>(.*?)</span>',tr,re.S)[1];org=re.search(r'class="preview-model-org"[^>]*>(.*?)</span>',tr,re.S)[1];score=re.search(r'class="preview-score"[^>]*>(.*?)</td>',tr,re.S)[1];rows.append(make_row(name,score,org))
  board(id,'tau-bench',title,'tau','Pass^1',protocol+' Official homepage top-three preview only; this is not the full leaderboard.',rows,coverage='Official homepage top three only')
 lcb=json.loads(data['lcb']);marks=sorted(lcb['date_marks']);start,end=marks[15],marks[-1]
 def day(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).strftime('%Y-%m-%d')
 rows=[]
 for m in lcb['models']:
  if not m.get('release_date'):continue
  values=[x['pass@1'] for x in lcb['performances'] if x['model']==m['model_repr'] and start<=x['date']<=end]
  if not values:continue
  if m['release_date']>=start:continue
  rows.append(make_row(m['model_repr'],round(sum(values)/len(values),1),f'{len(values)} problems · source eligibility date {day(m["release_date"])} (unverified release date)'))
 board('livecodebench','livecodebench','LiveCodeBench · '+day(start)+' to '+day(end),'lcb','Pass@1','Default official problem window '+day(start)+' through '+day(end)+'. Scores averaged and rounded as in upstream; its eligibility-date filter is retained. Source dates include placeholders and are not independently verified model release dates or contamination evidence. This dated window is not a current frontier ranking.',rows,coverage='Source models passing the upstream eligibility-date filter with scored problems in this window')
 math_table=next(t for t in re.findall(r'<table\b[^>]*>(.*?)</table>',data['matharena'],re.S) if 'Expected performance' in t)
 rows=[]
 for cells in rows_of_table(math_table):
  if len(cells)!=6:raise ValueError('MathArena recommendation schema changed')
  label,name,provider,date,score,cost=cells
  match=re.fullmatch(r'([\d.]+)%\s*±\s*([\d.]+)%',score)
  if not match:raise ValueError('MathArena expected performance format changed')
  rows.append(make_row(name,match[1],f'{label} · {provider} · source uncertainty ±{match[2]} percentage points · expected cost {cost}',date,rank=int(label.split()[0][1:]) if label.startswith('#') else None))
 board('matharena-expected','matharena','MathArena · expected performance','matharena','Expected normalized performance','Organizer’s aggregate across non-deprecated competitions, with questions equally weighted. Source uncertainty and expected costs are retained. This is a four-row recommendation excerpt, not all models or a BuilderWars composite.',rows,sort=False,rankMethod='source',coverage='Official homepage recommendations only')
 result={'schema':'builderwars.eval-rankings.v1','capturedAt':captured,'boards':boards,'attribution':'Scores are reported by the linked benchmark organizers. BuilderWars republishes dated source extracts and does not independently run or certify these evaluations.'}
 # Prepare everything before replacing any reviewed snapshot.
 target=ROOT/'data/evals/rankings.json';target.parent.mkdir(parents=True,exist_ok=True)
 for name,raw in artifacts.items():
  p=ROOT/'public'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':'prepared for review','boards':len(boards),'rows':sum(len(x['rows']) for x in boards),'capturedAt':captured}))
if __name__=='__main__':main()
