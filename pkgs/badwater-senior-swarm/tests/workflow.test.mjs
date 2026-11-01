import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {ROOT, settings, ROLES} from '../lib.mjs';
import {resolveResource} from '../extension.mjs';
const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
const scripts = Object.fromEntries(['review','build'].map(mode=>[mode,fs.readFileSync(path.join(ROOT,'workflows',mode+'.js'),'utf8')]));
function context(config={}) {return {repo:'/fixture/repo',stateRoot:'/fixture/state',paths:{node:process.execPath},config:settings(config),scripts};}
const assessment = {status:'complete',summary:'Observed fixture',coverage:['source'],applicableRoles:['qa','security'],findings:[]};
const plan = {summary:'Bounded fixture',acceptance:['works'],assumptions:[],rollout:'Local only',tasks:[{id:'fix',title:'Fix fixture',paths:['source.mjs'],dependencies:[],criteria:['works'],verify:[{argv:['node','--test','source.test.mjs'],timeoutSeconds:30}]}]};
function admission(key,roles=['qa','security']) { return {ok:true,stdout:JSON.stringify({slots:({'admit-discovery':['po','tech-lead'],'admit-specialists':roles,'admit-plan':['plan']}[key]||[]).map(name=>({name,reportPath:'/fixture/run/reports/'+name+'.json'}))})}; }
function jsonValue(value) {assert(value===null||['string','boolean','number','object'].includes(typeof value),'native state cannot contain undefined');if(value&&typeof value==='object')Object.values(value).forEach(jsonValue);}
function evaluate(resource,runs) {return new AsyncFunction('runs','state',resource.script)(runs,{async set(key,value){assert.equal(key,'board');jsonValue(value);assert(Buffer.byteLength(JSON.stringify(value))<256*1024);},async get(){}});}

test('named resources validate data only, bind exact commands and reject authority in args',()=>{
  for(const args of [{id:'../escape',goal:'x'},{id:'fine',goal:'x',approved:true},{id:'fine',goal:'x',command:'rm -rf'}]) assert.throws(()=>resolveResource('review',args,context()));
  assert.throws(()=>resolveResource('build',{id:'fine',goal:'extra'},context()));
  const resource=resolveResource('review',{id:'fine',goal:"Review '; touch /not-authorized #"},context());
  assert.equal(resource.hostCommands.length,5);assert(resource.hostCommands.every(x=>x.command.includes('cli.mjs')));
  assert(!resource.script.includes('createAgentSession'));assert(!resource.script.includes('runs.host("ci"'));
  const build=resolveResource('build',{id:'fine'},context());assert.equal(build.hostCommands.length,32);
});
test('review respects concurrency1, requires specialists and returns awaiting approval',async()=>{
  const resource=resolveResource('review',{id:'fixture',goal:'Review fixture'},context({maxConcurrent:1}));
  const calls=[], batches=[];
  const source={repo:'/fixture/repo',head:'head',digest:'digest',clean:true};
  const value=await evaluate(resource,{
    async host(key){if(key.startsWith('admit-'))return admission(key);return {ok:true,stdout:JSON.stringify(key==='prepare'?{id:'fixture',phase:'reviewing',source,runDirectory:'/fixture/state/run'}:{id:'fixture',source,runDirectory:'/fixture/state/run',admissions:5,taskIds:['fix'],planPath:'/fixture/state/run/plan.json',planHash:'hash',next:'approve',phase:'awaiting-approval'})};},
    async all(items){batches.push(items.length);return items.map(item=>{calls.push(item);return {ok:true,structuredOutput:assessment};});},
    async run(key,item){assert.equal(key,'plan');assert(!('key' in item));calls.push(item);return {ok:true,structuredOutput:plan};},
  });
  assert(batches.every(n=>n<=1));assert.deepEqual(calls.map(x=>x.agent),['badwater-senior-swarm.po','badwater-senior-swarm.tech-lead','badwater-senior-swarm.qa','badwater-senior-swarm.security','badwater-senior-swarm.tech-lead']);
  assert(calls.every(x=>x.context==='fresh'&&!x.worktree));assert(calls.every(x=>x.output.startsWith('/fixture/state/run/reports/')));
  assert.equal(value.phase,'awaiting-approval');assert.match(value.coverage,/not attempted/);
});
test('review applies only explicit role-model mappings and selects interface roles when relevant',async()=>{
  const resource=resolveResource('review',{id:'fixture',goal:'Review interface'},context({roleModels:{security:'provider/reviewer'}}));
  const calls=[];
  await evaluate(resource,{
    async host(key){if(key.startsWith('admit-'))return admission(key,['qa','security','ui','ux','devops']);return {ok:true,stdout:JSON.stringify(key==='prepare'?{id:'fixture',phase:'reviewing',source:{repo:'/fixture/repo',head:'head'},runDirectory:'/fixture/run'}:{id:'fixture',source:{},runDirectory:'/fixture/run',admissions:8,taskIds:['fix'],planPath:'/fixture/run/plan.json',planHash:'x',phase:'awaiting-approval'})};},
    async all(items){calls.push(...items);return items.map(item=>({ok:true,structuredOutput:{...assessment,applicableRoles:item.agent==='badwater-senior-swarm.tech-lead'?['ui','ux','devops']:[]}}));},
    async run(){return {ok:true,structuredOutput:plan};},
  });
  assert(calls.some(x=>x.agent==='badwater-senior-swarm.ui'));assert(calls.some(x=>x.agent==='badwater-senior-swarm.ux'));assert(calls.some(x=>x.agent==='badwater-senior-swarm.devops'));
  assert.equal(calls.find(x=>x.agent==='badwater-senior-swarm.security').model,'provider/reviewer');assert(!calls.find(x=>x.agent==='badwater-senior-swarm.qa').model);
});
test('a normally completed but blocked child cannot become a successful review',async()=>{
  const resource=resolveResource('review',{id:'fixture',goal:'Review'},context());
  await assert.rejects(()=>evaluate(resource,{async host(key){if(key.startsWith('admit-'))return admission(key);return{ok:true,stdout:JSON.stringify({id:'fixture',phase:'reviewing',source:{repo:'/fixture'},runDirectory:'/fixture/run'})};},async all(){return [{ok:true,structuredOutput:{...assessment,status:'blocked'}},{ok:true,structuredOutput:assessment}];}}),/incomplete/);
});
test('build isolates developers, gates actual commands and freshly reviews integrated result',async()=>{
  const config=settings(), source={repo:'/fixture/repo',head:'base'};
  const steps=[{action:'develop',phase:'building',id:'fixture',source,admissions:6,config,runDirectory:'/fixture/run',integration:'/fixture/integration',planPath:'/fixture/run/plan.json',pending:[{key:'fix-r0-base',taskId:'fix',title:'Fix fixture',base:'base'}]},{action:'review',phase:'verifying',id:'fixture',source,admissions:8,config,runDirectory:'/fixture/run',integration:'/fixture/integration',head:'integrated',cycle:0,planPath:'/fixture/run/plan.json',checksPath:'/fixture/checks.json',reviewRoles:['qa','security']},{action:'complete',phase:'complete',id:'fixture',source,admissions:8,config,runDirectory:'/fixture/run',integration:'/fixture/integration',branch:'badwater-senior-swarm/fixture/integration',head:'integrated',resultPath:'/fixture/run/result.json',completed:['fix']}];
  const calls=[];let index=0;
  const resource=resolveResource('build',{id:'fixture'},context());
  const result=await evaluate(resource,{async host(key){assert.equal(key,'step-'+index);return {ok:true,stdout:JSON.stringify(steps[index++])};},async all(items){calls.push(...items);return items.map(item=>({ok:true,structuredOutput:{status:item.agent==='badwater-senior-swarm.developer'?'implemented':'complete'}}));}});
  const dev=calls[0];assert(dev.worktree);assert.equal(dev.cwd,'/fixture/integration');assert.equal(dev.baseRef,'HEAD');assert.match(dev.acceptance.verify[0].command,/task-check/);assert.equal(dev.acceptance.review.required,false);assert.equal(dev.acceptance.report,'on');
  assert.deepEqual(calls.slice(1).map(x=>x.agent),['badwater-senior-swarm.qa','badwater-senior-swarm.security']);assert(calls.slice(1).every(x=>x.context==='fresh'&&x.key.includes('integrated')));
  assert.equal(result.phase,'complete');assert.match(result.authority,/No push/);
});
test('all packaged analysts have explicit read-only tools and no ambient extensions or nesting',()=>{
  for(const role of ROLES){const source=fs.readFileSync(path.join(ROOT,'agents',role+'.md'),'utf8');const tools=source.match(/^tools: (.+)$/m)[1].split(/,\s*/);assert.deepEqual(tools,['read','grep','find','ls','contact_supervisor']);assert.match(source,/^extensions:\s*$/m);assert.match(source,/^defaultContext: fresh$/m);assert(!tools.includes('subagent'));assert.match(source,/^package: badwater-senior-swarm$/m);}
});
