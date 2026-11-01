// Explicitly opt-in, quota-consuming synthetic CLI/RPC pilot, never a flake check.
// Requires an operator-authorized private filesystem/PID fixture; see docs/badwater-senior-swarm.md.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {pathToFileURL} from 'node:url';
assert.equal(process.env.BADWATER_SENIOR_SWARM_LIVE_FIXTURE,'1');assert.equal(process.env.HOME,'/work/home');assert.equal(process.cwd(),'/work');
assert(fs.existsSync('/bin/sh'),'Expose a managed /bin/sh for native host steps');assert(process.env.NODE_EXTRA_CA_CERTS,'Supply verified-TLS CA roots');
const swarm=process.argv[2];assert(swarm?.startsWith('/nix/store/'));
const paths=JSON.parse(fs.readFileSync(path.join(swarm,'paths.json'),'utf8'));
const {git,snapshot,runDirectory,writeJson,readJson}=await import(pathToFileURL(path.join(swarm,'lib.mjs')));
const provider=process.env.BADWATER_SENIOR_SWARM_PROVIDER||'openai',model=process.env.BADWATER_SENIOR_SWARM_MODEL||'gpt-6.1-sol';
const repo='/work/repo',agentDir='/work/home/.pi/agent',auth=path.join(agentDir,'auth.json');
fs.mkdirSync(repo,{recursive:true});fs.mkdirSync(agentDir,{recursive:true,mode:0o700});fs.mkdirSync('/work/tmp',{recursive:true,mode:0o700});assert(!fs.existsSync(auth));
let child,timer,stdout,stderr;const startedAt=new Date().toISOString();
try{
 // Copy only inside this private fixture. Never parse, print, retain or publish it.
 fs.copyFileSync('/run/pi-auth',auth,fs.constants.COPYFILE_EXCL);fs.chmodSync(auth,0o600);
 git(repo,['init','-b','main']);git(repo,['config','user.name','Fixture']);git(repo,['config','user.email','fixture@localhost']);
 fs.writeFileSync(path.join(repo,'sum.mjs'),'export function sum(a,b) { return a-b; }\n');
 fs.writeFileSync(path.join(repo,'sum.test.mjs'),"import {test} from 'node:test'; import assert from 'node:assert/strict'; import {sum} from './sum.mjs'; test('adds positive and negative values',()=>{assert.equal(sum(2,3),5);assert.equal(sum(-2,3),1);});\n");
 fs.writeFileSync(path.join(repo,'AGENTS.md'),'Synthetic project. Only authorized change: correct addition in sum.mjs. Do not change tests, docs, dependencies or other files. Check: node --test sum.test.mjs. No UI, deployment, credentials or external services. No direct parent edits: use the packaged seniorSwarm. Irrelevant scopes are not applicable.\n');
 git(repo,['add','.']);git(repo,['-c','commit.gpgsign=false','commit','-m','test: synthetic live fixture']);const before=snapshot(repo);
 writeJson(path.join(agentDir,'settings.json'),{packages:[paths.subagents,swarm],defaultProvider:provider,defaultModel:model,defaultThinkingLevel:'low',defaultTools:['read','grep','find','ls','subagent','subagents_enable','subagent_supervisor'],badwaterSeniorSwarm:{maxConcurrent:3,maxAgents:16,maxRepairCycles:1,browserCommand:null},enableInstallTelemetry:false,enableAnalytics:false,compaction:{enabled:false}});
 stdout=fs.createWriteStream('/work/rpc.jsonl',{mode:0o600});stderr=fs.createWriteStream('/work/stderr',{mode:0o600});
 child=spawn(path.join(paths.pi.split('/lib/pi/node_modules/')[0],'bin/pi'),['--mode','rpc','--approve','--provider',provider,'--model',model,'--thinking','low'],{cwd:repo,stdio:['pipe','pipe','pipe'],env:{...process.env,TMPDIR:'/work/tmp'}});
 child.stderr.pipe(stderr);const lines=createInterface({input:child.stdout});
 const runFile=path.join(runDirectory(repo,'synthetic-pilot'),'run.json'),workflowDirs=new Set(),receipts=new Map();
 let run,approvalSent=false,dialogs=0,finished=false;
 const send=message=>child.stdin.write(JSON.stringify(message)+'\n');
 await new Promise((resolve,reject)=>{
  const fail=error=>{if(!finished){finished=true;reject(error);}};
  function inspectAtSettledBoundary(){
   try{
    if(fs.existsSync(runFile))run=readJson(runFile);
    for(const directory of workflowDirs){const file=path.join(directory,'workflow-receipt.json');if(fs.existsSync(file)){const record=readJson(file);receipts.set(record.workflowRunId,record);assert(!['failed','stopped'].includes(record.workflowChildren?.workflowState),'Native workflow failed; inspect its receipt');}}
    if(run?.phase==='awaiting-approval'&&!approvalSent){
     assert.deepEqual(snapshot(repo),before,'review edited caller source');assert.equal(run.plan.tasks.length,1,'broadened pilot task count');assert.deepEqual(run.plan.tasks[0].paths,['sum.mjs']);assert(run.plan.tasks[0].verify.every(x=>JSON.stringify(x.argv)===JSON.stringify(['node','--test','sum.test.mjs'])),'broadened pilot check');
     approvalSent=true;send({id:'approve-pilot',type:'prompt',message:'/badwater-senior-swarm-approve '+path.dirname(runFile)});return;
    }
    const records=[...receipts.values()];
    if(run?.phase!=='complete'||!records.some(x=>x.workflowChildren?.children.some(c=>c.agent==='badwater-senior-swarm.developer')&&x.workflowChildren.workflowState==='completed'))return;
    assert(approvalSent&&dialogs===1,'real interactive approval missing');assert.deepEqual(snapshot(repo),before,'caller source branch changed');assert.equal(git(run.build.integration,['symbolic-ref','--quiet','HEAD']).stdout.trim(),'refs/heads/'+run.build.branch);
    assert.equal(run.build.review.head,run.build.head);assert.equal(run.build.review.verdict,'ok');assert.equal(run.build.integrated.length,1);assert(run.admissions<=16);assert.match(fs.readFileSync(path.join(run.build.integration,'sum.mjs'),'utf8'),/return\s+a\s*\+\s*b/);
    const actors=records.flatMap(x=>x.workflowChildren?.children||[]);for(const role of ['badwater-senior-swarm.po','badwater-senior-swarm.tech-lead','badwater-senior-swarm.qa','badwater-senior-swarm.security','badwater-senior-swarm.developer'])assert(actors.some(c=>c.agent===role),'missing live role '+role);assert(!actors.some(c=>['badwater-senior-swarm.ui','badwater-senior-swarm.ux'].includes(c.agent)),'irrelevant visual role spawned');
    writeJson('/work/result.json',{version:1,status:'passed',startedAt,finishedAt:new Date().toISOString(),provider,model,id:run.id,phase:run.phase,admissions:run.admissions,dialogs,sourceUnchanged:true,sourceHead:before.head,integrationHead:run.build.head,integrationBranch:run.build.branch,runFile,package:swarm,receipts:records.map(x=>({workflowRunId:x.workflowRunId,state:x.state,children:x.workflowChildren.children.map(c=>({agent:c.agent,runId:c.runId,state:c.state,model:c.model}))})),checks:run.build.integrated.flatMap(x=>x.checks),reviews:run.build.review.reports});
    finished=true;resolve();
   }catch(error){fail(error);}
  }
  lines.on('line',line=>{
   stdout.write(line+'\n');let event;try{event=JSON.parse(line);}catch{return fail(new Error('Non-JSON RPC output'));}
   if(event.type==='tool_execution_end'&&event.toolName==='subagent'&&event.result?.details?.mode==='workflow'&&event.result.details.asyncDir)workflowDirs.add(event.result.details.asyncDir);
   if(event.type==='extension_ui_request'&&event.method==='select'){
    try{assert(event.title.startsWith('Approve this exact swarm plan?\n'));assert(approvalSent);assert.deepEqual(event.options,['Cancel','Approve exact plan']);const current=readJson(runFile);assert(event.title.includes(current.planHash));assert(event.title.includes('No push'));assert(event.title.length<800);const review=readJson(path.join(path.dirname(runFile),'approval-review-'+current.planHash+'.json'));assert.deepEqual(review.plan,current.plan);assert.equal(review.source.digest,current.snapshot.digest);dialogs++;assert.equal(dialogs,1);send({type:'extension_ui_response',id:event.id,value:'Approve exact plan'});}catch(error){send({type:'extension_ui_response',id:event.id,cancelled:true});fail(error);}
   }else if(event.type==='extension_ui_request'&&['confirm','input','editor'].includes(event.method)){send({type:'extension_ui_response',id:event.id,cancelled:true});fail(new Error('Unexpected pilot decision request'));}
   if(event.type==='extension_error'||event.type==='error'||(event.type==='response'&&event.success===false)||(event.type==='auto_retry_end'&&event.success===false))fail(new Error('Actual CLI/RPC or provider retries failed; inspect private evidence'));
   // Native settled events, not filesystem polling or racy recursive watches,
   // authorize sending the next operator command while the parent is idle.
   if(event.type==='agent_settled')inspectAtSettledBoundary();
  });
  child.on('error',fail);child.on('exit',code=>{if(!finished)fail(new Error('CLI exited before delivery: '+code));});timer=setTimeout(()=>fail(new Error('Pilot deadline600s; preserve evidence, no fallback')),600000);
  send({id:'pilot',type:'prompt',message:'/skill:badwater-senior-swarm build Fix the addition bug in this synthetic repository using run id synthetic-pilot. Only sum.mjs may change; preserve all other files. Exact check: node --test sum.test.mjs. UI/deployment/DevOps are not applicable. Use the packaged badwater-senior-swarm.review named resource with a strict explicit mission; wait for the real /badwater-senior-swarm-approve command. After it confirms continue badwater-senior-swarm.build against that same native missionId. Use async:true and timeoutMs420000. No other implementation/delegation protocol or direct parent edits. This bounded synthetic pilot was explicitly authorized; the client will confirm only the exact one-file/one-check plan at an idle boundary. Missing business details may be assumptions, not blockers for elementary addition.'});
 });
 console.log('PASS actual CLI/skill/named async workflows, live specialists, real RPC approval, isolated developer gate, serial integration and fresh exact-head reviews; source unchanged');
}finally{
 clearTimeout(timer);if(child){child.stdin.end();if(child.exitCode===null)child.kill('SIGTERM');}stdout?.end();stderr?.end();fs.rmSync(auth,{force:true});
}
