import test from 'node:test';
import assert from 'node:assert/strict';
import {people,initial,calculate,distribute,reconcile,paidFor,tornLink,unitRates,changeCalculationMode,chains,chainReport,warPhase,wars} from '../src/model.js';
test('spreadsheet totals and exact whole-dollar allocation',()=>{
 const r=calculate(people,initial().settlements.aug28.rules);
 assert.equal(r.valid,true);assert.equal(r.fund,145828616);assert.equal(r.totalPoints,261.952);assert.equal(r.total,145828616);
 assert.equal(r.lines.find(p=>p.id===4202486).amount,11899457);
 assert.deepEqual(distribute(100n,[2n,1n],[10,20]),[67n,33n]);
 assert.deepEqual(distribute(10n,[1n,1n,1n],[10,20,30]),[4n,3n,3n]);
});
test('fixed rates expose a funding deficit and bad inputs are rejected',()=>{
 const rules=initial().settlements.aug28.rules;
 assert(calculate(people,{...rules,mode:'fixed',weights:['10000000','0','0','0']}).deficit>0);
 assert.equal(calculate(people,{...rules,income:'-1'}).valid,false);
 assert.equal(calculate(people,{...rules,weights:['0','0','0','0']}).valid,false);
});
test('only unique actual transfer evidence confirms once',()=>{
 const state=initial();state.settlements.aug28.approved={revision:1,calculation:calculate(people,state.settlements.aug28.rules)};
 state.intents=[{id:'intent',warId:'aug28',playerId:4202486,amount:100,at:1000,revision:1,status:'pending'}];
 state.news=[{id:'news',kind:'balance_credit',faction:'bonfire',playerId:4202486,amount:100,at:2000}];
 assert.equal(reconcile(state).confirmed,0);
 state.news[0].kind='cash_transfer';const r=reconcile(state);assert.equal(r.confirmed,1);assert.equal(paidFor(r.state,'aug28',4202486),100);assert.equal(reconcile(r.state).confirmed,0);
 state.intents.push({...state.intents[0],id:'other-intent'});assert.equal(reconcile(state).confirmed,0);
});
test('prefill validates recipient and whole amount; Pay Day is a separate route',()=>{
 assert(tornLink(4202486,100).endsWith('giveMoneyTo=4202486&money=100'));
 assert(!tornLink(4202486,100,'payday').includes('giveMoneyTo'));
 assert.throws(()=>tornLink(4202486,0));assert.throws(()=>tornLink(4202486,1.5));
});
test('point weights expose dollar prices without becoming fixed dollar rates',()=>{
 const rules=initial().settlements.aug28.rules,calc=calculate(people,rules),rates=unitRates(rules,calc);
 assert.equal(rates[0].toFixed(2),'556699.76');assert.equal(rates[3].toFixed(2),'55669.98');
 const fixed=changeCalculationMode(rules,'fixed');assert.deepEqual(fixed.weights,['0','0','0','0']);
 fixed.weights=['500000','0','100000','0'];
 const pool=changeCalculationMode(fixed,'pool');assert.deepEqual(pool.weights,rules.weights);
 assert.deepEqual(changeCalculationMode(pool,'fixed').weights,['500000','0','100000','0']);
});
test('internal chain report preserves totals and bonus counts without inventing times',()=>{
 for(const chain of chains){const r=chainReport(chain);
  assert.equal(r.rows.reduce((a,p)=>a+p.hits,0),chain.hits);
  assert.equal(Math.round(r.rows.reduce((a,p)=>a+p.respect,0)*100),chain.respect*100);
  assert.equal(r.rows.reduce((a,p)=>a+p.bonusHits,0),chain.bonuses);
  assert(r.milestones.every(m=>m.at===null));
 }
});
test('official war timestamps determine lifecycle; readiness is independent',()=>{
 const now=Date.parse('2026-11-01T16:00:00Z');
 assert.equal(warPhase(wars[0],now),'Finished · data ready');
 assert.equal(warPhase(wars[2],now),'In progress');
 assert.equal(warPhase({...wars[0],complete:false},now),'Finished · importing records');
 assert.equal(warPhase({...wars[2],start:'2026-11-02T12:00:00Z'},now),'Scheduled');
});
