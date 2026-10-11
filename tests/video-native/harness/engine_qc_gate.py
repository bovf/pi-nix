"""Installed engine integration: fractional/VFR clocks, native conform and failed-export preservation."""
import hashlib,json,os,subprocess,sys,time
from fractions import Fraction
from pathlib import Path
P=json.loads(Path('/harness/paths.json').read_text());M=json.loads(Path('/harness/video-runtime.json').read_text());R=Path('/fixture/raw');R.mkdir();D=Path('/fixture/projects');D.mkdir();L=Path('/fixture/receipts');L.mkdir();C=Path('/fixture/video.json');user={'readRoots':[str(R)],'writeRoot':str(D),'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli','timeoutSeconds':600};C.write_text(json.dumps(user));B=P['badwater-video']+'/bin/badwater-video';ff=P['ffmpeg']+'/bin/ffmpeg';seq=0
sys.path.insert(0,P['badwater-video']+'/lib/badwater-video');from engine import Engine
config={**json.loads(Path(M['defaults']['storePath']).read_text()),**user,'engine':B};E=Engine(config,C)
def cli(args,wait=False,ok=True):
 global seq
 seq+=1;r=subprocess.run([B,'--config',str(C),*(['--wait'] if wait else []),*args],capture_output=True,timeout=650);p=L/str(seq);p.with_suffix('.command.json').write_text(json.dumps(args));p.with_suffix('.stdout').write_bytes(r.stdout);p.with_suffix('.stderr').write_bytes(r.stderr);p.with_suffix('.status').write_text(str(r.returncode))
 if ok:assert r.returncode==0 and not r.stderr,(args,r.stderr.decode());return json.loads(r.stdout)
 assert r.returncode!=0,(args,r.stdout);return json.loads(r.stderr)
def ffmpeg(args):subprocess.run([ff,'-nostdin','-v','error',*args],check=True,timeout=180)
def ingest(file,project='qc'):return cli(['ingest',project,str(file)],wait=True)['assets'][0]['asset']
def wait(job):
 deadline=time.monotonic()+650
 while time.monotonic()<deadline:
  r=cli(['jobs','status',job])
  if r['state'] in ['done','failed','cancelled','interrupted']:return r
  time.sleep(0.05)
 raise AssertionError('job deadline')
cli(['project','create','qc'])
for name,color,freq in [('a.mp4','red',440),('b.mp4','blue',880)]:ffmpeg(['-f','lavfi','-i',f'color=c={color}:s=160x96:r=12:d=3','-f','lavfi','-i',f'sine=frequency={freq}:sample_rate=48000:duration=3','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(R/name)])
a=ingest(R/'a.mp4');b=ingest(R/'b.mp4');before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir()}
plan={'version':1,'output':{'width':320,'height':180,'fps':'30000/1001','aspect':'16/9'},'clips':[{'asset':a,'in':'1/2','out':'2','reason':'First red cut'},{'asset':b,'in':'1/2','out':'3/2','reason':'Second blue cut'}],'constraints':{'targetDuration':'5/2','tolerance':'0'}};p=D/'qc/plan.json';p.write_text(json.dumps(plan));revision=cli(['timeline','apply','qc',str(p)],wait=True);final=cli(['export','qc','--out','final.mp4'],wait=True);assert final['qc']['passed'];assert final['qc']['representativeCutChecks'];assert final['qc']['audioBoundaryChecks'];assert final['qc']['streams'][0]['width']==320;assert Fraction(final['qc']['streams'][0]['avg_frame_rate'])==Fraction(30000,1001)
validation=E.validate('qc',plan);project=E.project('qc');expected=Fraction(5,2)
# Deliberately wrong but playable same-size/rate/duration render must fail actual content checks.
wrong=D/'wrong.mp4';ffmpeg(['-f','lavfi','-i','color=c=yellow:s=320x180:r=30000/1001:d=2.5','-f','lavfi','-i','sine=frequency=880:sample_rate=48000:duration=2.5','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(wrong)]);q=E.qc(project,wrong,expected,validation);assert not q['passed'] and any('content differs' in f for f in q['failures']);(L/'wrong-cut-qc.json').write_text(json.dumps(q,indent=2))
wrong_format=D/'wrong-format.mkv';ffmpeg(['-i',final['video'],'-c:v','ffv1','-c:a','pcm_s16le',str(wrong_format)]);q=E.qc(project,wrong_format,expected,validation);assert not q['passed'] and 'unexpected video format' in q['failures']
for label,filter_,required in [('dimensions','scale=160:96','missing/wrong-size video'),('fps','fps=12','incorrect frame rate')]:
 wrong=D/(label+'.mp4');ffmpeg(['-i',final['video'],'-vf',filter_,'-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac',str(wrong)]);q=E.qc(project,wrong,expected,validation);assert not q['passed'] and required in q['failures'];(L/(label+'-qc.json')).write_text(json.dumps(q,indent=2))
wrong_audio=D/'wrong-audio.mkv';ffmpeg(['-i',final['video'],'-c:v','copy','-c:a','pcm_s16le',str(wrong_audio)]);q=E.qc(project,wrong_audio,expected,validation);assert not q['passed'] and 'unexpected audio format' in q['failures'];(L/'pcm-audio-qc.json').write_text(json.dumps(q,indent=2))
missing_audio=D/'missing-audio.mp4';ffmpeg(['-i',final['video'],'-c:v','copy','-an',str(missing_audio)]);q=E.qc(project,missing_audio,expected,validation);assert not q['passed'] and 'missing audio' in q['failures'];(L/'missing-audio-qc.json').write_text(json.dumps(q,indent=2));assert all(s['codec_name']=='aac' for s in final['qc']['streams'] if s['codec_type']=='audio');(L/'healthy-native-aac-qc.json').write_text(json.dumps(final['qc'],indent=2))
second_audio=D/'second-audio.mkv';ffmpeg(['-i',final['video'],'-f','lavfi','-i','anullsrc=r=48000:cl=mono','-map','0:v','-map','0:a','-map','1:a','-c:v','copy','-c:a:0','copy','-c:a:1','pcm_s16le','-t','2.5',str(second_audio)]);q=E.qc(project,second_audio,expected,validation);assert not q['passed'] and 'unexpected audio format' in q['failures'];(L/'second-pcm-audio-qc.json').write_text(json.dumps(q,indent=2))
q=E.qc(project,Path(final['video']),Fraction(8),validation);assert not q['passed'] and any('duration' in f for f in q['failures'])
truncated=D/'truncated.mp4';content=Path(final['video']).read_bytes();truncated.write_bytes(content[:len(content)//2]);
try:E.qc(project,truncated,expected,validation)
except Exception:pass
else:raise AssertionError('truncated output accepted')
# Original source goes missing: failed replacement and automatic retries cannot destroy previous output.
out=Path(final['video']);h=hashlib.sha256(out.read_bytes()).hexdigest();source=R/'a.mp4';source.rename(R/'away.mp4');failed=wait(cli(['export','qc','--out','final.mp4','--replace'])['job']);assert failed['state']=='failed';assert hashlib.sha256(out.read_bytes()).hexdigest()==h
for _ in range(2):failed=wait(cli(['jobs','retry',failed['id'],'--automatic'])['job']);assert failed['state']=='failed';assert hashlib.sha256(out.read_bytes()).hexdigest()==h
error=cli(['jobs','retry',failed['id'],'--automatic'],ok=False);assert 'budget exhausted' in error['error'];(R/'away.mp4').rename(source)
link=out.parent/'hardlinked.mp4';os.link(out,link);failed=wait(cli(['export','qc','--out','hardlinked.mp4','--replace'])['job']);assert failed['state']=='failed' and 'linked' in failed['error'];assert hashlib.sha256(out.read_bytes()).hexdigest()==h;link.unlink();cli(['export','qc','--out','../escape.mp4'],ok=False)
# Actual VFR timestamps are retained and a fractional frame request records a real decoded PTS.
vfr=R/'vfr.mp4';ffmpeg(['-f','lavfi','-i','testsrc2=s=160x96:r=12:d=3','-f','lavfi','-i','sine=frequency=330:sample_rate=48000:duration=3','-vf',"select='not(mod(n,2))+not(mod(n,5))'",'-fps_mode','vfr','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(vfr)]);vid=ingest(vfr);metadata=E.project('qc').asset(vid)['metadata'];v=next(s for s in metadata['streams'] if s['codec_type']=='video');assert Fraction(v['avg_frame_rate'])!=Fraction(v['r_frame_rate']);frame=cli(['inspect','qc',vid,'--at','13/100']);assert abs(Fraction(frame['decodedPtsSeconds'])-Fraction(1,6))<Fraction(1,10000)
# Black/silent material is a measured finding, not automatic rejection/deletion.
black=R/'black.mp4';ffmpeg(['-f','lavfi','-i','color=c=black:s=160x96:r=12:d=1','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac',str(black)]);black_id=ingest(black);bp={'version':1,'output':{'width':160,'height':96,'fps':'12'},'clips':[{'asset':black_id,'in':'0','out':'1','reason':'Explicit legitimate black/silent source'}]};p.write_text(json.dumps(bp));cli(['timeline','apply','qc',str(p)],wait=True);blackout=cli(['export','qc','--out','black.mp4'],wait=True);assert blackout['qc']['passed'];assert blackout['qc']['findings']['blackIntervals'] and blackout['qc']['findings']['silenceIntervals']
signal=D/'signal.mp4';ffmpeg(['-f','lavfi','-i','color=c=red:s=160x96:r=12:d=2','-f','lavfi','-i','aevalsrc=0.99*sgn(sin(2*PI*12000*t)):s=48000:d=2','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(signal)]);sv={'output':{'width':160,'height':96,'fps':'12'},'ranges':[{'asset':a,'in':'0','timelineIn':'0','timelineOut':'1'},{'asset':a,'in':'1','timelineIn':'1','timelineOut':'2'}]};sq=E.qc(project,signal,Fraction(2),sv);assert sq['passed'];assert sq['findings']['possibleClipping'];assert sq['audioBoundaryChecks'][0]['possibleAbruptEdge'];(L/'signal-qc.json').write_text(json.dumps(sq,indent=2))
assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir() if str(f) in before}
Path('/fixture/acceptance.json').write_text(json.dumps({'runtime':P['badwater-video'],'nativeFitResolutionAspectFractionalFps':True,'wrongCutsDurationFormatTruncationRefused':True,'wrongDimensionsFPSAudioCodecRefused':True,'healthyNativeAACAndMissingAudioValidated':True,'actualHighDeltaAndClippingSignalFindings':True,'failedReplacementPreservedOriginalOutput':True,'automaticRetryBudgetEnforced':True,'hardlinkAndTraversalOutputsRefused':True,'VFRMetadataAndActualFractionalPTS':True,'legitimateBlackSilenceFindingsAccepted':True,'originalsUnchanged':True,'final':final,'blackFinal':blackout},indent=2)+'\n');print('PASS actual native conform/fractional FPS, VFR frame PTS, QC negative controls, safe replacements/retry budget and legitimate black/silence')
