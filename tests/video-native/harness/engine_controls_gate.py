"""Real packaged cache/child limits and production queue with a deterministic inert worker.
Queue control fixture is NOT native media/model-quality evidence; other gates cover those.
"""
import json,os,sqlite3,subprocess,sys,time,uuid
from pathlib import Path
P=json.loads(Path('/harness/paths.json').read_text());D=json.loads(Path('/harness/video-runtime.json').read_text());sys.path.insert(0,P['badwater-video']+'/lib/badwater-video');from main import configuration;from store import Policy;from jobs import Jobs
raw=Path('/fixture/raw');raw.mkdir();derived=Path('/fixture/derived');cfg=Path('/fixture/config.json');cfg.write_text(json.dumps({'readRoots':[str(raw)],'writeRoot':str(derived),'timeoutSeconds':600,'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli'}));base=P['badwater-video']+'/bin/badwater-video'
def cli(*args):
 r=subprocess.run([base,'--config',str(cfg),*args],capture_output=True,text=True,timeout=700);assert not r.stderr,r.stderr;assert r.returncode==0,r.stdout;return json.loads(r.stdout)
subprocess.run([P['espeak-ng']+'/bin/espeak-ng','-w',str(raw/'speech.wav'),'We create the project and then we save the project.'],check=True,capture_output=True);cli('project','create','cache');cli('--wait','ingest','cache',str(raw/'speech.wav'));asset=cli('assets','cache')['assets'][0]['id'];r=cli('--wait','analyze','cache',asset);key=r['cacheKey'];r2=cli('--wait','analyze','cache',asset);assert r2['cached'];assert cli('search','cache','project')['matches'];body=derived/'cache/analysis'/asset/key/'observations.json';original=body.read_bytes();body.write_text('{corrupt');assert not cli('search','cache','project')['matches'];r3=cli('--wait','analyze','cache',asset);assert not r3['cached'];assert cli('search','cache','project')['matches'];body.unlink();assert not cli('search','cache','project')['matches'];assert not cli('--wait','analyze','cache',asset)['cached']
# Model/pipeline invalidation is a source-bound cached-read control, not a new ASR accuracy claim.
from engine import Engine
os.environ['BADWATER_VIDEO_DEFAULTS']=D['defaults']['storePath'];os.environ['BADWATER_VIDEO_ENGINE']=base;c,_=configuration(cfg);e=Engine(c,cfg);p=e.project('cache')
for field in ['pipelineHash','modelHash']:
 changed={**c,field:'0'*64};other=Engine(changed,cfg);assert other.cache_key(e.analysis_options({}))!=key;assert not other.search('cache','project',local=True)['matches']
assert any(x.read_bytes()==b'{corrupt' for x in body.parent.glob('observations.json.invalid-*'))
# Actual frame-cache identities/digests; recover while retaining invalid evidence and reusing valid peers.
video=raw/'frames.mp4';subprocess.run([P['ffmpeg']+'/bin/ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=red:s=160x96:r=12:d=1','-c:v','libx264','-threads','3','-pix_fmt','yuv420p',str(video)],check=True);vid=cli('--wait','ingest','cache',str(video))['assets'][0]['asset'];opts='{"transcribe":false,"maxFrames":2}';vresult=cli('--wait','analyze','cache',vid,'--options',opts);vbody=derived/'cache/analysis'/vid/vresult['cacheKey']/'observations.json';frames=json.loads(vbody.read_text())['frames'];assert len(frames)==2;good=Path(frames[1]['path']);stamp=good.stat().st_mtime_ns;bad=Path(frames[0]['path']);record=bad.with_suffix('.json');raw_record=record.read_text();meta=json.loads(raw_record);meta['requestedSeconds']='99';record.write_text(json.dumps(meta))
try:e.inspect('cache',vid,frames[0]['requestedSeconds'],local=True);raise AssertionError('frame identity accepted')
except ValueError as exc:assert 'identity' in str(exc)
assert not cli('--wait','analyze','cache',vid,'--options',opts)['cached'];assert good.stat().st_mtime_ns==stamp;assert any(x.read_text()==json.dumps(meta) for x in record.parent.glob(record.name+'.invalid-*'))
bad.write_bytes(b'corrupt frame bytes');assert not cli('--wait','analyze','cache',vid,'--options',opts)['cached'];assert any(x.read_bytes()==b'corrupt frame bytes' for x in bad.parent.glob(bad.name+'.invalid-*'));assert good.stat().st_mtime_ns==stamp
pol=Policy(c);start=time.monotonic()
try:pol.run([c['bash'],'-c','sleep 20'],timeout=1);raise AssertionError('deadline accepted')
except RuntimeError as exc:assert 'deadline' in str(exc)
assert time.monotonic()-start<7
for fd in ['1','2']:
 try:pol.run([c['bash'],'-c',f'head -c 9000000 /dev/zero >&{fd}']);raise AssertionError('unbounded output accepted')
 except RuntimeError as exc:assert '8 MiB' in str(exc)
# Production queue/supervisor with an explicitly labeled deterministic fixture worker.
worker=Path('/fixture/queue-worker');worker.write_text('#!'+D['python']['storePath']+'/bin/python3\nimport sys,time,sqlite3,json\nfrom pathlib import Path\nc=json.loads(Path(sys.argv[2]).read_text());db=sqlite3.connect(c["writeRoot"]+"/jobs.sqlite",timeout=5);a=json.loads(db.execute("SELECT args FROM jobs WHERE id=?",(sys.argv[4],)).fetchone()[0]);db.execute("UPDATE jobs SET progress=.5 WHERE id=?",(sys.argv[4],));db.commit()\nif a.get("noise"):sys.stdout.write("x"*20000000);sys.stdout.flush()\ntime.sleep(65)\n');worker.chmod(0o700);qroot=Path('/fixture/queue');qcfg=Path('/fixture/queue.json');qcfg.write_text(json.dumps({'readRoots':[str(raw)],'writeRoot':str(qroot),'concurrency':2,'timeoutSeconds':30}));qc={**c,'writeRoot':str(qroot),'concurrency':2,'timeoutSeconds':30,'engine':str(worker)};jobs=Jobs(Policy(qc),qcfg);aids=[];bid=uuid.uuid4().hex
with jobs.db() as db:
 for i in range(102):
  aid=uuid.uuid4().hex;aids.append(aid);db.execute("INSERT INTO jobs(id,project,operation,args,state,created,updated)VALUES(?,'a','inert-control','{}','queued',?,?)",(aid,i,i))
 db.execute("INSERT INTO jobs(id,project,operation,args,state,created,updated)VALUES(?,'b','inert-control','{}','queued',103,103)",(bid,))
jobs.pump();deadline=time.monotonic()+5
while time.monotonic()<deadline:
 with jobs.db() as db:running=[dict(r) for r in db.execute("SELECT * FROM jobs WHERE state='running'")]
 if all(r['progress']==.5 for r in running):break
 time.sleep(.05)
assert len(running)==2 and {r['project'] for r in running}=={'a','b'} and all(r['progress']==.5 for r in running)
with jobs.db() as db:db.execute("UPDATE jobs SET state='cancelled' WHERE state='queued'")
for r in running:jobs.cancel(r['id'])
# True GNU worker supervisor deadline and capped disk log; not a simulated clock.
x=jobs.submit('deadline','inert-control',{});n=jobs.submit('noise','inert-control',{'noise':True});start=time.monotonic()
while time.monotonic()-start<40:
 states=[jobs.status(i['job']) for i in [x,n]]
 if all(s['state']=='interrupted' for s in states):break
 time.sleep(.1)
assert all(s['state']=='interrupted' for s in states),states;assert 29<=time.monotonic()-start<38
log=qroot/'noise/.work'/n['job']/'worker.log';assert log.stat().st_size==8388608
Path('/fixture/acceptance.json').write_text(json.dumps({'runtime':P['badwater-video'],'cacheReuseCorruptionMissingRecovery':True,'staleModelPipelineQueryFiltered':True,'frameIdentityAndDigestRepairRetainsInvalidEvidence':True,'validFramesReusedWithoutRewrite':True,'boundedChildOutputAndDeadline':True,'queueControlFixture':{'globalConcurrency':2,'projectSerialization':True,'fairnessBeyond100SameProjectRows':True,'progressObserved':True,'actualWorkerDeadlineSeconds':30,'diskLogMaximumBytes':8388608},'noModelQualityClaim':True},indent=2));print('PASS actual packaged cache and child limits; production queue/supervisor deterministic controls, real deadlines and bounded disk logs')
