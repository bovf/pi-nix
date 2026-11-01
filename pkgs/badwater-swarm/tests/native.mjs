// Installed SDK/resource/agent/workflow/approval lifecycle, no model or service request.
// Run only with a fresh private HOME/filesystem/network namespace.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
assert.equal(process.env.SWARM_NATIVE_FIXTURE,'1','Use the private native fixture launcher');
const swarm=process.argv[2];assert(swarm?.startsWith('/nix/store/'));
const paths=JSON.parse(fs.readFileSync(path.join(swarm,'paths.json'),'utf8'));
const sdk=await import(pathToFileURL(path.join(paths.pi,'dist/index.js')));
const {builtInExtensions}=await import(pathToFileURL(path.join(paths.pi,'dist/extensions/index.js')));
const {git,snapshot,writeJson,ROLES}=await import(pathToFileURL(path.join(swarm,'lib.mjs')));
const controller=await import(pathToFileURL(path.join(swarm,'cli.mjs')));
const {discoverAgents}=await import(pathToFileURL(path.join(paths.subagents,'src/agents/agents.js')));
const {resolveWorkflowResource}=await import(pathToFileURL(path.join(paths.subagents,'src/workflows/workflow-resources.js')));
const {validateWorkflowScript,runWorkflowScript}=await import(pathToFileURL(path.join(paths.subagents,'src/workflows/scripted-workflow.js')));
const repo=path.resolve('repo'),home=process.env.HOME,agentDir=path.join(home,'.pi/agent');fs.mkdirSync(repo,{recursive:true});fs.mkdirSync(agentDir,{recursive:true});
git(repo,['init','-b','main']);git(repo,['config','user.name','Fixture']);git(repo,['config','user.email','fixture@localhost']);fs.writeFileSync(path.join(repo,'example.mjs'),'export const value = 1;\n');git(repo,['add','.']);git(repo,['-c','commit.gpgsign=false','commit','-m','test: native fixture']);
const packages=[paths.subagents,swarm];
writeJson(path.join(agentDir,'settings.json'),{packages,defaultTools:['+codemode'],badwaterSwarm:{maxConcurrent:2,maxAgents:16,browserCommand:null},enableInstallTelemetry:false,enableAnalytics:false});
const settingsManager=sdk.SettingsManager.create(repo,agentDir);
const loader=new sdk.DefaultResourceLoader({cwd:repo,agentDir,settingsManager,noContextFiles:true,extensionFactories:builtInExtensions});await loader.reload();
const loaded=loader.getExtensions();assert.deepEqual(loaded.errors,[]);assert.deepEqual(loaded.warnings,[]);assert.deepEqual(loader.getSkills().diagnostics,[]);
assert.equal(loader.getSkills().skills.filter(x=>x.name==='swarm').length,1);
const agents=discoverAgents(repo,'both',undefined,{globalNpmRoot:null,projectTrusted:true});
for(const name of [...ROLES,'developer']){const agent=agents.agents.find(x=>x.name==='swarm.'+name);assert(agent,'missing '+name);assert.equal(agent.source,'package');assert.equal(agent.defaultContext,'fresh');assert.deepEqual(agent.extensions,[]);assert(!agent.tools.includes('subagent'));if(name!=='developer'){assert(!agent.tools.includes('bash'));assert(!agent.tools.includes('edit'));assert(!agent.tools.includes('write'));}}
assert.equal(fs.realpathSync(path.join(swarm,'node_modules/@earendil-works/pi-coding-agent')),fs.realpathSync(paths.pi));assert.equal(fs.realpathSync(path.join(swarm,'node_modules/pi-subagents')),fs.realpathSync(paths.subagents));
const runtime=await sdk.ModelRuntime.create({authPath:path.join(agentDir,'inert-auth.json'),modelsPath:null,refreshOnCreate:false,allowModelNetwork:false});
const {session}=await sdk.createAgentSession({cwd:repo,agentDir,settingsManager,resourceLoader:loader,sessionManager:sdk.SessionManager.inMemory(repo),modelRuntime:runtime,model:{id:'inert',name:'Inert',provider:'fixture',api:'openai-completions',baseUrl:'http://127.0.0.1:1',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:1}});
const errors=[];
try{
 await session.bindExtensions({mode:'print',onError:error=>errors.push(error)});assert.deepEqual(errors,[]);
 let reviewSetup;
 for(const mode of ['review','build']){
  const resource=resolveWorkflowResource('badwater-swarm.'+mode,mode==='review'?{id:'native',goal:'Review fixture'}:{id:'native'},session.sessionId);assert(resource.ok,resource.error);
  const valid=validateWorkflowScript(resource.resource.script,{agentNameError:name=>agents.agents.some(x=>x.name===name)?undefined:'missing '+name});assert(valid.ok,JSON.stringify(valid));
  if(mode==='review'){
   const setup=JSON.parse(resource.resource.script.split('\n')[0].slice('const setup = '.length,-1));reviewSetup=setup;
   const {executeWorkflowHostCommand}=await import(pathToFileURL(path.join(paths.subagents,'src/workflows/host-command.js')));
   const host=await executeWorkflowHostCommand({key:'prepare',params:setup.hosts.prepare,cwd:repo,defaultOutputPath:path.resolve('native-host.log'),signal:AbortSignal.timeout(30000)});assert(host.ok,host.error);assert.equal(JSON.parse(host.stdout).phase,'reviewing');
  }
 }
 const input={repo,id:'native',goal:'Review fixture',config:{maxConcurrent:2,maxAgents:16,browserCommand:null}};
 const run=controller.prepare(input);const plan={summary:'Large source-located review evidence. '.repeat(300),acceptance:['valid syntax'],assumptions:[],rollout:'local',tasks:[{id:'syntax',title:'Document module',paths:['example.mjs'],dependencies:[],criteria:['valid syntax'],verify:[{argv:['node','--check','example.mjs'],timeoutSeconds:30}]}]};
 controller.admit({...input,stage:'discovery'});
 for(const role of ['po','tech-lead','qa','security'])writeJson(path.join(run.runDirectory,'reports',role+'.json'),{status:'complete',summary:'fixture',coverage:['source'],applicableRoles:[],findings:[]});controller.admit({...input,stage:'specialists'});controller.admit({...input,stage:'plan'});writeJson(path.join(run.runDirectory,'reports/plan.json'),plan);controller.collect(input);
 const {executeWorkflowHostCommand}=await import(pathToFileURL(path.join(paths.subagents,'src/workflows/host-command.js')));
 const collected=await executeWorkflowHostCommand({key:'collect',params:reviewSetup.hosts.collect,cwd:repo,defaultOutputPath:path.resolve('native-collect.log'),signal:AbortSignal.timeout(30000)});assert(collected.ok,collected.error);assert(Buffer.byteLength(collected.stdout)<3500);assert(JSON.parse(collected.stdout).planPath);assert(!JSON.parse(collected.stdout).plan);
 const extension=loaded.extensions.find(x=>x.path.endsWith('/extension.mjs'));assert(extension);
 const approval=extension.commands.get('swarm-approve');assert(approval);
 await assert.rejects(()=>approval.handler(run.runDirectory,{hasUI:false}),/interactive/);
 let dialogs=0;await approval.handler(run.runDirectory,{hasUI:true,cwd:repo,sessionManager:{getSessionId:()=>session.sessionId},ui:{async confirm(title,text){dialogs++;assert(text.includes('Exact verification commands'));assert(text.includes('No push'));return false;},notify(){}}});assert.equal(controller.checkpoint(input).phase,'awaiting-approval');assert.equal(dialogs,1);
 const before=snapshot(repo);
 await assert.rejects(()=>approval.handler(run.runDirectory,{hasUI:true,cwd:repo,sessionManager:{getSessionId:()=>session.sessionId},ui:{async confirm(){writeJson(path.join(run.runDirectory,'reports/plan.json'),{...plan,summary:'Changed while confirmation is open'});controller.collect(input);return true;},notify(){}}}),/Displayed plan/);
 assert.equal(controller.checkpoint(input).phase,'awaiting-approval');
 const displayed=controller.approvalDetails(run.runDirectory);controller.approve(run.runDirectory,{confirmed:true,sessionId:session.sessionId,planHash:displayed.planHash,sourceDigest:displayed.snapshot.digest});assert.equal(controller.checkpoint(input).phase,'approved');assert.deepEqual(snapshot(repo),before);
 const buildResource=resolveWorkflowResource('badwater-swarm.build',{id:'native'},session.sessionId);assert(buildResource.ok,buildResource.error);
 const buildSetup=JSON.parse(buildResource.resource.script.split('\n')[0].slice('const setup = '.length,-1)),board=new Map();
 const integrated=await runWorkflowScript({script:buildResource.resource.script,args:{id:'native'},globalConcurrencyLimit:2,signal:AbortSignal.timeout(60000),
  state:{get:key=>board.get(key),set:(key,value)=>{board.set(key,JSON.parse(JSON.stringify(value)));}},
  host:(key,params,signal)=>{assert.equal(params.command,buildSetup.hosts[key].command);return executeWorkflowHostCommand({key,params,cwd:repo,defaultOutputPath:path.resolve(key+'.log'),signal});},
  status:()=>{throw new Error('No status polling in workflow');},
  launch:async(key,params,signal)=>{
   assert.equal(params.context,'fresh');
   if(params.agent==='swarm.developer'){
    assert.equal(params.worktree,true);const worker=path.resolve('native-worker');git(repo,['worktree','add','-b','native-writer',worker,'HEAD']);fs.writeFileSync(path.join(worker,'example.mjs'),'export const value = 1; // native bridge fixture\n');
    const gate=await executeWorkflowHostCommand({key:'task-gate',params:{kind:'command',command:params.acceptance.verify[0].command,timeoutMs:30000},cwd:worker,defaultOutputPath:path.resolve('native-task-gate.log'),signal});assert(gate.ok,gate.error);
    return {key,ok:true,agent:params.agent,output:'Fixture leaf, no model call',structuredOutput:{status:'implemented',summary:'fixture',changedFiles:['example.mjs'],limitations:[]},artifactPaths:[]};
   }
   assert(['swarm.qa','swarm.security'].includes(params.agent));const current=controller.checkpoint(input);const report={status:'complete',verdict:'ok',head:current.build.head,summary:'Fixture inspected actual source/check receipts; no model call',findings:[]};writeJson(params.output,report);return {key,ok:true,agent:params.agent,output:'fixture review',structuredOutput:report,artifactPaths:[]};
  },
 });
 assert.equal(integrated.value.phase,'complete');assert.equal(board.get('board').taskStatus.syntax.status,'completed');assert.deepEqual(snapshot(repo),before);
 assert.equal(loaded.extensions.filter(x=>x.commands.has('mcp')).length,1);assert.equal(loaded.extensions.find(x=>x.commands.has('mcp')).path,'builtin:mcp');
 console.log('PASS: installed native SDK/8 package roles/skill/zero warnings, both workflow validators, headless and declined approval, exact host peers, one builtin MCP; no model calls');
}finally{const id=session.sessionId;const {emitSessionShutdownEvent}=await import(pathToFileURL(path.join(paths.pi,'dist/core/extensions/runner.js')));await emitSessionShutdownEvent(session.extensionRunner,{type:'session_shutdown',reason:'quit'});session.dispose();assert.equal(resolveWorkflowResource('badwater-swarm.build',{id:'native'},id).ok,false,'resource survived session shutdown');}
