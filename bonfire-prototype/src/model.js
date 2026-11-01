export const people = [
 [4202486,'OZONE03',13,83.75,16],[4222722,'BellyButnPirate',13,81.22,14],[2011686,'Populus',11,80.70,11],
 [3878480,'Drippycheeze',10,81.92,12],[4227674,'Shymansky',10,75.04,10],[4215870,'CheekiCreepy',10,74.64,10],
 [4370095,'Mansie77',10,74.38,11],[4048951,'Prometheus76',10,70.87,10],[4308671,'Phoebe_the_Dogo',10,59.24,10],
 [4240377,'Bravowoman',9,54.52,9],[2882789,'xeven',10,37.48,10],[4514775,'MakeAWishAlex',8,39.78,9],
 [4135741,'Grabz00r',7,48.32,9],[4143216,'LigmaBauls',6,33.28,6],[4122131,'SaintSeraphin',6,19.66,10],
 [4119589,'Guzzy_Guzz',5,26.35,5],[4157129,'MonsieurShelby',3,25.61,4],[4529803,'Skizlit',3,18.94,3],
 [4522234,'RedVic',3,18.15,6],[4502003,'tacotastegood',3,15.67,5],[1977774,'FLHarleyGuy',0,0,0],
 [4132910,'Abysshole',0,0,0],[4140383,'Zwetschgenman',0,0,0],[3645924,'RichieM87',0,0,0]
].map(([id,name,w,r,attacks],i)=>({id,name,w,r,attacks,n:i===11?1:0,a:0,warR:r,bonusR:0,quota:10,current:i!==23}));
export const presets = [
 {id:'bonfire',name:'Bonfire 10/10/80',hint:'War hits + respect · your standard allocation',weights:['1','0','0','0.1'],mode:'pool'},
 {id:'hits',name:'War hits only',hint:'Every successful war hit has equal weight',weights:['1','0','0','0'],mode:'pool'},
 {id:'support',name:'War + support',hint:'War 1 · outside 0.25 · assist 0.5',weights:['1','0.25','0.5','0'],mode:'pool'},
 {id:'respect',name:'Respect performance',hint:'War respect · verified chain bonuses excluded',weights:['0','0','0','1'],mode:'pool',scope:'war',bonusExcluded:true},
 {id:'chain',name:'Chain contribution',hint:'Manual event budget · successful hits',weights:['1','1','0','0'],mode:'pool',manual:true},
 {id:'fixed',name:'Fixed rates',hint:'Set guaranteed dollar rates per action',weights:['0','0','0','0'],mode:'fixed'}
];
export const wars = [
 {id:'aug28',title:'28 Aug 2026',opponent:'Ranked war · spreadsheet example',income:182285770,complete:true,ended:true,period:'28–29 Aug 2026',rows:people},
 {id:'oct25',title:'25 Oct 2026',opponent:'Ranked war · demo event',income:125000000,complete:true,ended:true,period:'25–27 Oct 2026',rows:people.map((p,i)=>({...p,w:Math.max(0,12-i),n:i%4,a:i%3,r:Number((Math.max(0,12-i)*3.42).toFixed(2)),warR:Number((Math.max(0,12-i)*3.2).toFixed(2)),bonusR:0,attacks:Math.max(0,12-i)+i%4+i%3+1}))},
 {id:'collecting',title:'1 Nov 2026',opponent:'Active war · incomplete demo',income:0,complete:false,ended:false,period:'1 Nov 2026 · ongoing',rows:people.map((p,i)=>({...p,w:i<6?2:0,r:i<6?5.2:0,warR:i<6?5.2:0,n:0,a:0,attacks:i<6?2:0}))}
];
export function rulesFor(w){return {preset:w.id==='oct25'?'hits':'bonfire',mode:'pool',weights:w.id==='oct25'?['1','0','0','0']:['1','0','0','0.1'],income:String(w.income),supply:'10',reserve:'10',manual:false,budget:'10000000',topup:'0',scope:'all',bonusExcluded:false,bonuses:[]};}
Object.assign(wars[0],{start:'2026-08-28T18:00:00Z',end:'2026-08-29T02:30:00Z',warId:'DEMO-AUG28',lastSynced:'2026-11-01T12:00:00Z'});
Object.assign(wars[1],{start:'2026-10-25T12:00:00Z',end:'2026-10-27T10:00:00Z',warId:'DEMO-OCT25',lastSynced:'2026-11-01T12:00:00Z'});
Object.assign(wars[2],{start:'2026-11-01T12:00:00Z',end:null,warId:'DEMO-NOV01',lastSynced:'2026-11-01T12:30:00Z'});
export function unitRates(rules,result){return rules.weights.map(x=>Number(x)*(rules.mode==='pool'?result.rate:1));}
export function changeCalculationMode(rules,mode){
 if(mode===rules.mode)return rules;
 return {...rules,mode,poolWeights:rules.mode==='pool'?[...rules.weights]:rules.poolWeights,
 fixedRates:rules.mode==='fixed'?[...rules.weights]:rules.fixedRates,
 weights:[...(mode==='pool'?(rules.poolWeights||['1','0','0','0.1']):(rules.fixedRates||['0','0','0','0']))]};
}
export function warPhase(w,now=Date.now()){
 if(now<Date.parse(w.start))return 'Scheduled';
 if(!w.end)return 'In progress';
 return w.complete?'Finished · data ready':'Finished · importing records';
}
export const chains=[
 {id:72499932,period:'29–31 Oct 2026',hits:5000,respect:21512,bonuses:9},
 {id:72482830,period:'29 Oct 2026',hits:331,respect:1206,bonuses:5},
 {id:72296011,period:'27–29 Oct 2026',hits:3492,respect:13418,bonuses:8},
 {id:72072228,period:'25–27 Oct 2026',hits:5000,respect:20937,bonuses:9}
];
export function chainReport(chain){
 const members=people.filter(p=>p.w>0),ids=members.map(p=>p.id),weights=members.map(p=>BigInt(p.w));
 const milestones=[10,25,50,100,250,500,1000,2500,5000].filter(n=>n<=chain.hits).map((n,i)=>({hit:n,respect:10*2**i,player:members[i%members.length],at:null}));
 const bonusRespect=milestones.reduce((a,m)=>a+m.respect,0);
 const regularHits=distribute(BigInt(chain.hits-milestones.length),weights,ids);
 const regularCents=distribute(BigInt(Math.round((chain.respect-bonusRespect)*100)),weights,ids);
 const rows=members.map((p,i)=>{const bs=milestones.filter(m=>m.player.id===p.id);const bonus=bs.reduce((a,m)=>a+m.respect,0);return {id:p.id,name:p.name,hits:Number(regularHits[i])+bs.length,regularHits:Number(regularHits[i]),bonusHits:bs.length,bonusRespect:bonus,regularRespect:Number(regularCents[i])/100,respect:Number(regularCents[i])/100+bonus};});
 return {chain,rows,milestones,bonusRespect,regularRespect:chain.respect-bonusRespect};
}
export function initial(){return {version:2,selected:'aug28',settlements:Object.fromEntries(wars.map(w=>[w.id,{rules:rulesFor(w),approved:null,revision:1}])),payments:[],intents:[],news:[],audit:[],customPresets:[],expenses:8300000};}
export function money(n){return '$'+Number(n||0).toLocaleString('en-US',{maximumFractionDigits:0});}
export function number(n,d=0){return Number(n||0).toLocaleString('en-US',{maximumFractionDigits:d});}
function scaled(s,places=4){if(!/^\d+(\.\d{1,4})?$/.test(String(s)))throw Error('Enter a non-negative number with up to 4 decimals.'); const [a,b='']=String(s).split('.');return BigInt(a)*10n**BigInt(places)+BigInt(b.padEnd(places,'0'));}
function whole(s){if(!/^\d+$/.test(String(s))||Number(s)>1000000000000)throw Error('Amounts must be whole dollars, from 0 to 1 trillion.');return BigInt(s);}
export function distribute(pool,weights,ids){
 const total=weights.reduce((a,b)=>a+b,0n); if(!total){if(pool)throw Error('No payable points. Choose a positive weight or change the fund.');return weights.map(()=>0n);}
 const values=weights.map(x=>pool*x/total);let left=Number(pool-values.reduce((a,b)=>a+b,0n));
 const order=weights.map((x,i)=>({i,rem:pool*x%total})).sort((a,b)=>a.rem===b.rem?ids[a.i]-ids[b.i]:a.rem>b.rem?-1:1);
 for(let i=0;i<left;i++)values[order[i].i]++;return values;
}
export function calculate(rows,rules){
 try{
 const income=whole(rules.income),s=scaled(rules.supply),o=scaled(rules.reserve);if(s+o>1000000n)throw Error('Reserve allocations cannot exceed 100%.');
 const supplies=income*s/1000000n,reserve=income*o/1000000n,budget=rules.manual?whole(rules.budget):income-supplies-reserve, fund=budget+whole(rules.topup);
 const ws=rules.weights.map(x=>scaled(x)); const bonuses=rules.bonuses||[];let inside=0n,extra=0n;
 for(const b of bonuses){if(!rows.some(p=>p.id===b.id))throw Error('Bonus recipient is not in this settlement.');const value=whole(String(b.amount));if(b.source==='inside')inside+=value;else extra+=value;}
 if(inside>fund)throw Error('Bonuses exceed the available player fund.');
 const points=rows.map(p=>{let respect=rules.scope==='war'?p.warR:p.r;if(rules.bonusExcluded)respect=Math.max(0,respect-p.bonusR);return BigInt(p.w)*100n*ws[0]+BigInt(p.n)*100n*ws[1]+BigInt(p.a)*100n*ws[2]+scaled(String(respect),4)*ws[3]/100n;});
 const totalPoints=points.reduce((a,b)=>a+b,0n),variable=fund-inside;
 const shares=rules.mode==='pool'?distribute(variable,points,rows.map(p=>p.id)):points.map(x=>(x+500000n)/1000000n);
 const lines=rows.map((p,i)=>({...p,points:Number(points[i])/1000000,base:Number(shares[i]),bonus:bonuses.filter(b=>b.id===p.id).reduce((a,b)=>a+Number(b.amount),0),amount:Number(shares[i])+bonuses.filter(b=>b.id===p.id).reduce((a,b)=>a+Number(b.amount),0)}));
 const total=lines.reduce((a,p)=>a+p.amount,0),available=Number(fund+extra),deficit=Math.max(0,total-available);
 return {valid:true,lines,income:Number(income),supplies:rules.manual?0:Number(supplies),reserve:rules.manual?0:Number(reserve),fund:Number(fund),extra:Number(extra),variable:Number(variable),totalPoints:Number(totalPoints)/1000000,rate:totalPoints?Number(variable)*1000000/Number(totalPoints):0,total,available,deficit,remaining:available-total};
 }catch(e){return {valid:false,error:e.message,lines:[]};}
}
export function paidFor(state,warId,id){return state.payments.filter(p=>p.warId===warId&&p.playerId===id&&!p.reversed).reduce((a,b)=>a+b.amount,0);}
export function tornLink(playerId,amount,method='give'){
 if(!Number.isSafeInteger(playerId)||playerId<=0||!Number.isSafeInteger(amount)||amount<=0)throw Error('Invalid payment destination or amount.');
 return method==='give'?`https://www.torn.com/factions.php?step=your#/tab=controls&giveMoneyTo=${playerId}&money=${amount}`:'https://www.torn.com/factions.php?step=your&type=3#/tab=controls&option=pay-day';
}
export function reconcile(state){
 const next=structuredClone(state);let confirmed=0;
 for(const event of next.news){
  if(event.kind!=='cash_transfer'||event.faction!=='bonfire'||next.payments.some(p=>p.sourceId===event.id))continue;
  const possible=next.intents.filter(i=>i.status==='pending'&&i.playerId===event.playerId&&i.amount===event.amount&&event.at>=i.at&&event.at-i.at<=600000);
  if(possible.length!==1)continue;
  const intent=possible[0],s=next.settlements[intent.warId];
  if(!s.approved||s.approved.revision!==intent.revision)continue;
  const line=s.approved.calculation.lines.find(p=>p.id===intent.playerId),due=line.amount-paidFor(next,intent.warId,line.id);
  if(event.amount>due){intent.status='review';continue;}
  next.payments.push({id:'payment-'+event.id,sourceId:event.id,warId:intent.warId,playerId:event.playerId,amount:event.amount,at:event.at,reversed:false,method:intent.method});intent.status='confirmed';confirmed++;
 }
 return {state:next,confirmed};
}
