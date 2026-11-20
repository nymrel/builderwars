import {RULES,validateRules,type Rules} from './runtime';
import {competitionChallenges} from './competition-formats';
export type ChallengeId=typeof competitionChallenges[number]['id'];
export function dailyRules(day=new Date().toISOString().slice(0,10)):Rules {
  if(!/^\d{4}-\d{2}-\d{2}$/.test(day)||new Date(day+'T00:00:00Z').toISOString().slice(0,10)!==day)throw Error('Choose a real UTC date.');
  const seed=[...day].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,0),size=5+seed%2;
  return validateRules({kind:'custom',name:'Daily board · '+day,rows:size,cols:size,connect:3+(seed>>>2)%2,gravity:!!((seed>>>4)%2)});
}
export function challengeSetup(id:string,day?:string) {
  if(!competitionChallenges.some(c=>c.id===id))throw Error('Unknown challenge.');
  const rules=id==='daily-board'?dailyRules(day):{...RULES[id==='nim-duel'?'nim':id==='oracle-duel'?'tictactoe':'connect4']};
  return {id:id as ChallengeId,rules,moveLimit:rules.kind==='nim'?15:rules.rows*rules.cols,maxTokens:2048,pace:100,human:id!=='mirror-match',oracle:id==='oracle-duel',seriesLength:id==='mirror-match'?4:2};
}
