/* Behavioral tests for project-specific ranking; no browser required. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'frontend/app.js'),'utf8').replace(/init\(\);\s*$/,'');
const context=vm.createContext({console,URL,Map,Set});
vm.runInContext(source+'\n globalThis.__p={projectFit,projectTopicBias,conditionMatches,state};',context);
const {projectFit,projectTopicBias,conditionMatches,state}=context.__p;
const record={topics:['concrete_steel','geotech']};
const rule={mentions:{uses:['مسکونی'],structures:['بتن‌آرمه'],stages:['طراحی'],basement:true,parking:false,height:false},numeric_conditions:[
 {field:'floors',operator:'gte',value:5,unit:'طبقه',evidence:'حداقل 5 طبقه',confidence:'candidate'}
]};
const p1={city:'مشهد',use:'مسکونی',structure:'بتن‌آرمه',area:4500,floors:7,basements:2,stage:'طراحی'};
const p2={city:'تهران',use:'تجاری',structure:'فولادی',area:4500,floors:2,basements:0,stage:'بهره‌برداری'};
const a=projectFit(rule,record,p1), b=projectFit(rule,record,p2);
assert.ok(a.score>b.score,'matching project must rank higher');
assert.equal(a.level,'high');
assert.ok(a.reasons.some(x=>x.includes('کاربری')));
assert.ok(a.reasons.some(x=>x.includes('سازه')));
assert.equal(conditionMatches(rule.numeric_conditions[0],p1),true);
assert.equal(conditionMatches(rule.numeric_conditions[0],p2),false);
assert.ok(projectTopicBias('concrete_steel',p1)>projectTopicBias('concrete_steel',p2));
const p1OtherCity={...p1,city:'شیراز'};
assert.equal(projectFit(rule,record,p1OtherCity).score,a.score,'city must remain neutral until grounded city rules exist');
console.log('PASS: project engine ranks by profile, explains matches, and does not invent city filters');
