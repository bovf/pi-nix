import assert from 'node:assert/strict';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
const p=JSON.parse(fs.readFileSync('/harness/paths.json','utf8'));
const root=`${p.pi}/lib/pi/node_modules/@earendil-works/pi-coding-agent`;
const sdk=await import(pathToFileURL(`${root}/dist/index.js`));
const settings=sdk.SettingsManager.inMemory({packages:[],defaultTools:[]});
const loader=new sdk.DefaultResourceLoader({cwd:'/fixture',agentDir:'/fixture/home/.pi/agent',settingsManager:settings,noContextFiles:true,additionalExtensionPaths:[`${p['badwater-video']}/extensions/model-capabilities.ts`]});
await loader.reload();const loaded=loader.getExtensions();assert.deepEqual(loaded.errors,[]);assert.deepEqual(loaded.warnings,[]);
const modelRuntime=await sdk.ModelRuntime.create({authPath:'/fixture/inert-auth.json',modelsPath:null,refreshOnCreate:false,allowModelNetwork:false});
const model=modelRuntime.getModel('openai','gpt-5.6-sol');assert(model.input.includes('image'));
const {session}=await sdk.createAgentSession({cwd:'/fixture',agentDir:'/fixture/home/.pi/agent',modelRuntime,model,settingsManager:settings,resourceLoader:loader,sessionManager:sdk.SessionManager.inMemory('/fixture')});
try {
 await session.bindExtensions({mode:'print',onError:e=>{throw new Error(JSON.stringify(e));}});
 const helper=session.agent.state.tools.find(t=>t.name==='video_model_capabilities');assert(helper);
 const image=await helper.execute('model-1',{});assert.equal(image.details.imageInput,true);assert.equal(image.details.id,model.id);
 // Synthetic session metadata changes; no authenticated model selection/lifecycle claim.
 session.agent.state.model={...model,input:['text'],secretSentinel:'MUST_NOT_ESCAPE'};
 const text=await helper.execute('model-2',{});assert.equal(text.details.imageInput,false);assert.equal(text.details.available,true);
 session.agent.state.model={...model,id:'unknown',provider:'unknown',input:[]};
 const unknown=await helper.execute('model-3',{});assert.equal(unknown.details.available,false);assert.equal(unknown.details.id,null);
 assert(!JSON.stringify([image,text,unknown]).includes('MUST_NOT_ESCAPE'));assert.equal(session.messages.length,0);
 fs.writeFileSync('/fixture/model-acceptance.json',JSON.stringify({activeImageDeclaration:true,activeTextOnlySwitch:true,unknownFailsClosed:true,noSecrets:true,providerCalls:0},null,2));
 console.log('PASS installed active-model helper, actual SDK session/synthetic model metadata changes, no credentials/prompts/provider calls');
} finally {session.dispose();}
