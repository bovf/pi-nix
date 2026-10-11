import hashlib,json,subprocess,time
from pathlib import Path
from mcp_client import MCP
P=json.loads(Path('/harness/paths.json').read_text());R=Path('/fixture/raw');R.mkdir();D=Path('/fixture/projects');D.mkdir();config=Path('/fixture/video.json');config.write_text(json.dumps({'readRoots':[str(R)],'writeRoot':str(D),'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli','timeoutSeconds':600}))
B=P['badwater-video']+'/bin/badwater-video'
subprocess.run([P['espeak-ng']+'/bin/espeak-ng','-v','en-us','-s','135','-w',str(R/'speech.wav'),'Welcome to this tutorial. First we create the project. Then we import the video. Finally we save the result.'],check=True)
subprocess.run([P['ffmpeg']+'/bin/ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=red:s=160x96:r=12:d=9','-i',str(R/'speech.wav'),'-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(R/'camera.mp4')],check=True)
before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir()}
m=MCP([B,'--config',str(config),'mcp'],'engine-mcp')
def tool(name,args):
 r=m.tool(name,args)
 if 'structuredContent' in r:return r['structuredContent']
 return json.loads('\n'.join(c['text'] for c in r['content'] if c['type']=='text'))
def wait(job):
 deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  r=tool('job_status',{'job':job})
  if r['state']=='done':return r['result']
  assert r['state'] not in ['failed','interrupted','cancelled'],r
  time.sleep(0.05)
 raise AssertionError('job deadline')
try:
 tools=m.call('tools/list',{})['tools'];assert len({t['name'] for t in tools})==len(tools);assert all(t.get('inputSchema') for t in tools);assert Path(f'/proc/{m.p.pid}/task/{m.p.pid}/children').read_text().strip()==''
 tool('project_create',{'project':'mcpdemo'});started=time.monotonic();ingest=tool('asset_ingest',{'project':'mcpdemo','paths':[str(p) for p in R.iterdir()]});assert time.monotonic()-started<5;assets=wait(ingest['job'])['assets'];camera=next(v['asset'] for v in assets if v['path'].endswith('.mp4'));speech=next(v['asset'] for v in assets if v['path'].endswith('.wav'))
 started=time.monotonic();analysis=tool('analysis_start',{'project':'mcpdemo','asset':camera});assert time.monotonic()-started<5;result=wait(analysis['job']);assert result['summary']['transcriptSegments']>0;cached=wait(tool('analysis_start',{'project':'mcpdemo','asset':camera})['job']);assert cached['cached']
 search=tool('transcript_search',{'project':'mcpdemo','query':'project'});assert search['matches'];assert search['transcriptTextWithheldUntilConsent'];assert all('text' not in r for r in search['matches'])
 local=tool('frame_inspect',{'project':'mcpdemo','asset':camera,'seconds':'1/2'});assert not local['shareWithModel'];assert Path(local['path']).is_file()
 # Synthetic-fixture consent, not a live profile/provider call.
 for name,args in [('project_privacy',{'project':'mcpdemo','allow_remote':1}),('frame_inspect',{'project':'mcpdemo','asset':camera,'seconds':'1/2','share_with_model':'false'}),('job_retry',{'job':ingest['job'],'automatic':1}),('preview',{'project':'mcpdemo','replace':'true'}),('export',{'project':'mcpdemo','replace':1})]:
  rejected=m.call('tools/call',{'name':name,'arguments':args});assert rejected.get('isError') and 'boolean' in json.dumps(rejected).lower(),rejected
 tool('project_privacy',{'project':'mcpdemo','allow_remote':True});image=m.tool('frame_inspect',{'project':'mcpdemo','asset':camera,'seconds':'1/2','share_with_model':True});assert any(c['type']=='image' and c['mimeType']=='image/png' and len(c['data'])<1_500_000 for c in image['content']);search=tool('transcript_search',{'project':'mcpdemo','query':'project'});assert any('project' in r['text'].lower() for r in search['matches'])
 observations=tool('observation_query',{'project':'mcpdemo','asset':camera,'cache_key':result['cacheKey'],'start':'0','end':'9','limit':10});assert observations['transcript'];assert observations['frames']
 plan={'version':1,'output':{'width':160,'height':96,'fps':'12'},'clips':[{'asset':camera,'in':'1/2','out':'2','reason':'Requested introduction'},{'asset':camera,'in':'5','out':'13/2','reason':'Requested conclusion'}],'constraints':{'targetDuration':'3','tolerance':'0'}}
 validation=tool('timeline_validate',{'project':'mcpdemo','plan':plan});assert validation['valid'];revision=wait(tool('timeline_apply',{'project':'mcpdemo','plan':plan})['job']);assert revision['revision']==1
 preview=wait(tool('preview',{'project':'mcpdemo','output':'preview.mp4','seconds':'1'})['job']);assert preview['qc']['passed']
 plan['clips'][1]['in']='6';plan['clips'][1]['out']='15/2';plan['clips'][1]['reason']='Explicit synthetic requested revision';plan['audio']={'microphone':speech,'offset':'0','normalize':True};revised=wait(tool('timeline_apply',{'project':'mcpdemo','plan':plan})['job']);assert revised['revision']==2 and revised['parent']==1
 final=wait(tool('export',{'project':'mcpdemo','output':'final.mp4'})['job']);assert final['qc']['passed'];assert len(tool('revision_history',{'project':'mcpdemo'})['revisions'])==2
 # CLI and MCP query the same durable index/revision/job state.
 for args,remote in [(['project','open','mcpdemo'],tool('project_open',{'project':'mcpdemo'})),(['history','mcpdemo'],tool('revision_history',{'project':'mcpdemo'}))]:
  r=subprocess.run([B,'--config',str(config),*args],capture_output=True,check=True);assert not r.stderr;assert json.loads(r.stdout)==remote
 assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir()}
 Path('/fixture/acceptance.json').write_text(json.dumps({'installedRuntime':P['badwater-video'],'nativeMcpEditingPreviewRevisionExport':True,'CLIQueryParity':True,'nativeSoundProcessing':True,'ASRRealSpeech':True,'cacheReuse':True,'consentBoundary':True,'boundedPiImageContent':True,'lazyStartupNoChild':True,'originalsUnchanged':True,'analysis':result,'revision':revision,'revised':revised,'final':final},indent=2)+'\n');print('PASS shared-engine MCP: lazy startup, real speech/index/cache/queries/images, native edit-preview-revise/Sound/final, CLI parity and immutable originals')
finally:m.close()
