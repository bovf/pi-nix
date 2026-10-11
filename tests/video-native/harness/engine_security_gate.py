"""Actual installed engine: waveform ground truth, source/cache changes and owned job control."""
import hashlib,json,os,signal,subprocess,time,wave
from fractions import Fraction
from pathlib import Path
import numpy as np
P=json.loads(Path('/harness/paths.json').read_text());R=Path('/fixture/raw');R.mkdir();D=Path('/fixture/projects');D.mkdir();L=Path('/fixture/receipts');L.mkdir();config=Path('/fixture/video.json');config.write_text(json.dumps({'readRoots':[str(R)],'writeRoot':str(D),'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli','timeoutSeconds':600,'maxAutomaticRepairAttempts':2}))
B=P['badwater-video']+'/bin/badwater-video';ff=P['ffmpeg']+'/bin/ffmpeg';serial=0

def cli(args,wait=False,ok=True):
 global serial
 serial+=1;r=subprocess.run([B,'--config',str(config),*(['--wait'] if wait else []),*args],capture_output=True,timeout=650);stem=L/str(serial);stem.with_suffix('.command.json').write_text(json.dumps(args)+'\n');stem.with_suffix('.stdout').write_bytes(r.stdout);stem.with_suffix('.stderr').write_bytes(r.stderr);stem.with_suffix('.status').write_text(str(r.returncode)+'\n')
 if ok:assert r.returncode==0 and not r.stderr,(args,r.stderr.decode());return json.loads(r.stdout)
 assert r.returncode!=0,(args,r.stdout.decode());return json.loads(r.stderr)

def ffmpeg(args):subprocess.run([ff,'-nostdin','-v','error',*args],check=True,timeout=180)
def wav(path,values,rate=8000):
 with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(values,-1,1)*32767).astype('<i2').tobytes())
def ingest(path):return cli(['ingest','security',str(path)],wait=True)['assets'][0]['asset']
def wait(job):
 deadline=time.monotonic()+650
 while time.monotonic()<deadline:
  x=cli(['jobs','status',job])
  if x['state'] in ['done','failed','cancelled','interrupted']:return x
  time.sleep(0.05)
 raise AssertionError('deadline')
def identity(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
 except FileNotFoundError:return None
def descendants(pid):
 found={pid:identity(pid)}
 try:
  kids=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
 except FileNotFoundError:return found
 for p in kids:found.update(descendants(int(p)))
 return found

cli(['project','create','security']);rng=np.random.default_rng(71);n=8*8000;t=np.arange(n)/8000;noise=np.convolve(rng.normal(size=n),np.ones(5)/5,mode='same')*0.12;noise*=0.5+0.5*np.sin(t*2.1)**2;wav(R/'reference.wav',noise);wav(R/'mic.wav',np.concatenate([np.zeros(3200),noise]));ffmpeg(['-f','lavfi','-i','color=c=green:s=160x96:r=12:d=8','-i',str(R/'reference.wav'),'-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(R/'camera.mp4')]);camera=ingest(R/'camera.mp4');mic=ingest(R/'mic.wav')
aligned=cli(['align','security',camera,mic,'--max-lag','1'],wait=True);assert abs(Fraction(aligned['offsetSeconds'])-Fraction(2,5))<=Fraction(1,100),aligned
wav(R/'silent.wav',np.zeros(n));silent=ingest(R/'silent.wav');fail=wait(cli(['align','security',camera,silent,'--max-lag','1'])['job']);assert fail['state']=='failed' and 'ambiguous' in fail['error'],fail
# Repeated sine: correlation has many equally good offsets, so refuse to invent sync.
ffmpeg(['-f','lavfi','-i','color=c=red:s=160x96:r=12:d=2','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(R/'tone-camera.mp4')]);ffmpeg(['-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2','-c:a','pcm_s16le',str(R/'tone-mic.wav')]);tc=ingest(R/'tone-camera.mp4');tm=ingest(R/'tone-mic.wav');fail=wait(cli(['align','security',tc,tm,'--max-lag','1'])['job']);assert fail['state']=='failed' and 'ambiguous' in fail['error']
# Actual adaptive/frame observations, then unchanged reuse and relevant configuration invalidation.
first=cli(['analyze','security',camera,'--options','{"transcribe":false,"maxFrames":2}'],wait=True);again=cli(['analyze','security',camera,'--options','{"transcribe":false,"maxFrames":2}'],wait=True);assert again['cached'];changed=cli(['analyze','security',camera,'--options','{"transcribe":false,"maxFrames":3}'],wait=True);assert not changed['cached'] and changed['cacheKey']!=first['cacheKey']
# Content change with restored stat metadata must still invalidate a supposedly reusable analysis.
source=R/'camera.mp4';old=source.read_bytes();s=source.stat();b=bytearray(old);b[-20]^=1;source.write_bytes(b);os.utime(source,ns=(s.st_atime_ns,s.st_mtime_ns));fail=wait(cli(['analyze','security',camera,'--options','{"transcribe":false,"maxFrames":2}'])['job']);assert fail['state']=='failed' and 'changed' in fail['error'];source.write_bytes(old);os.utime(source,ns=(s.st_atime_ns,s.st_mtime_ns));retry=cli(['jobs','retry',fail['id']]);assert wait(retry['job'])['state']=='done'
# Missing/empty/corrupt, URI/traversal/symlink, malformed plans and unsafe output paths.
(R/'empty.mp4').touch();(R/'corrupt.mp4').write_bytes(b'not video');(R/'escape.mp4').symlink_to('/etc/passwd');
for path in [str(R/'missing.mp4'),str(R/'empty.mp4'),str(R/'escape.mp4'),'/etc/passwd','https://example.invalid/media.mp4',str(R/'..'/'other.mp4')]:cli(['ingest','security',path],ok=False)
corrupt=wait(cli(['ingest','security',str(R/'corrupt.mp4')])['job']);assert corrupt['state']=='failed';(D/'security/bad-plan.json').write_text('{"version":1,"output":{"width":160,"height":96,"fps":"NaN"},"clips":[]}');cli(['timeline','validate','security',str(D/'security/bad-plan.json')],ok=False)
# Real running ASR cancellation; kill only its own timeout/worker/Bubblewrap trees.
subprocess.run([P['espeak-ng']+'/bin/espeak-ng','-v','en-us','-s','120','-w',str(R/'speech.wav'),'Welcome to the tutorial. First create the project, import the video, and save the result.'],check=True);ffmpeg(['-stream_loop','20','-i',str(R/'speech.wav'),'-t','180','-c:a','pcm_s16le',str(R/'long.wav')]);long=ingest(R/'long.wav');unrelated=subprocess.Popen([P['coreutils']+'/bin/sleep','120'],start_new_session=True)
try:
 job=cli(['analyze','security',long])['job'];time.sleep(0.15)
 import sqlite3
 db=sqlite3.connect(D/'jobs.sqlite');row=db.execute('SELECT pid,process_identity,state FROM jobs WHERE id=?',(job,)).fetchone();db.close();assert row[2]=='running',row;owned=descendants(row[0]);cancel=cli(['jobs','cancel',job]);assert cancel['state']=='cancelled';assert unrelated.poll() is None
 deadline=time.monotonic()+3
 while time.monotonic()<deadline and any(identity(pid)==token and token is not None for pid,token in owned.items()):time.sleep(0.02)
 # Zombies are exited, not executing children; check live states independently.
 for pid,token in owned.items():
  if identity(pid)==token and token is not None:assert Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]=='Z',(pid,owned)
 assert cli(['jobs','status',job])['state']=='cancelled'
finally:unrelated.terminate();unrelated.wait(timeout=5)
# Hard-killed supervisor/worker reservation becomes interrupted, not a false success on restart.
job=cli(['analyze','security',long])['job'];time.sleep(0.1);db=sqlite3.connect(D/'jobs.sqlite');pid=db.execute('SELECT pid FROM jobs WHERE id=?',(job,)).fetchone()[0];db.close();os.killpg(pid,signal.SIGKILL);time.sleep(0.1);state=cli(['jobs','status',job]);assert state['state']=='interrupted',state;retry=cli(['jobs','retry',job]);assert retry['job']!=job;cli(['jobs','cancel',retry['job']]);assert cli(['jobs','status',retry['job']])['state']=='cancelled'
Path('/fixture/acceptance.json').write_text(json.dumps({'runtime':P['badwater-video'],'groundTruthAlignment':aligned,'silentAndPeriodicAlignmentRefused':True,'realCacheReuseAndConfigInvalidation':True,'restoredStatContentChangeDetected':True,'failedJobRetried':True,'invalidAssetsPathsPlans':True,'actualASRCancellationOwnedTree':True,'unrelatedProcessPreserved':True,'killedWorkerRecoveredAsInterrupted':True,'retryCancelledSafely':True},indent=2)+'\n');print('PASS real alignment/caches/content-hash/injection/invalid inputs and owned cancellation/restart/retry')
