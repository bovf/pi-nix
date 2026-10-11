"""Real installed-engine CLI vertical slice in a fresh private filesystem/network namespace."""
import hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
P=json.loads(Path('/harness/paths.json').read_text());R=Path('/fixture/raw');R.mkdir();D=Path('/fixture/projects');D.mkdir();L=Path('/fixture/receipts');L.mkdir();config=Path('/fixture/video.json');config.write_text(json.dumps({'readRoots':[str(R)],'writeRoot':str(D),'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli','timeoutSeconds':600}))
B=P['badwater-video']+'/bin/badwater-video'
def command(label,args,timeout=180):
 (L/(label+'.command.json')).write_text(json.dumps(args)+'\n');t=time.monotonic();r=subprocess.run(args,capture_output=True,timeout=timeout);(L/(label+'.stdout')).write_bytes(r.stdout);(L/(label+'.stderr')).write_bytes(r.stderr);(L/(label+'.status')).write_text(str(r.returncode)+'\n');assert r.returncode==0,(label,r.stderr.decode());assert not r.stderr,(label,r.stderr.decode());return r.stdout,time.monotonic()-t

def cli(label,args,wait=False):
 out,elapsed=command(label,[B,'--config',str(config),*(['--wait'] if wait else []),*args],timeout=700);return json.loads(out),elapsed
ff=P['ffmpeg']+'/bin/ffmpeg'
for name,color,freq in [('a name; $(touch SHOULD_NOT_EXIST).mp4','red',440),('b.mp4','blue',880)]:
 command('fixture-'+str(freq),[ff,'-nostdin','-v','error','-f','lavfi','-i',f'color=c={color}:s=160x96:r=12:d=2','-f','lavfi','-i',f'sine=frequency={freq}:sample_rate=48000:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-threads','3','-c:a','aac','-shortest',str(R/name)])
before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir()}
cli('project-create',['project','create','demo']);info,_=cli('asset-ingest',['ingest','demo',*[str(p) for p in R.iterdir()]],wait=True);a={Path(v['path']).name:v['asset'] for v in info['assets']};aid=a['a name; $(touch SHOULD_NOT_EXIST).mp4'];bid=a['b.mp4']
plan={'version':1,'output':{'width':160,'height':96,'fps':'12','aspect':'5/3'},'clips':[{'asset':bid,'in':'1/4','out':'7/4','reason':'Keep blue demonstration first'},{'asset':aid,'in':'1/2','out':'3/2','reason':'Retain red conclusion second'}],'constraints':{'targetDuration':'5/2','tolerance':'0','mustInclude':[{'asset':bid,'in':'1/2','out':'1'}],'mustExclude':[{'asset':aid,'in':'0','out':'1/4'}]}}
planfile=D/'demo/plan.json';planfile.write_text(json.dumps(plan));v,_=cli('plan-validate',['timeline','validate','demo',str(planfile)]);assert v['duration']=='5/2'
revision,_=cli('native-apply',['timeline','apply','demo',str(planfile)],wait=True);assert Path(revision['nativeProject']).is_file();assert revision['revision']==1
preview,_=cli('native-preview',['preview','demo','--out','preview.mp4','--seconds','1'],wait=True);final,_=cli('native-export',['export','demo','--out','final.mp4'],wait=True);assert preview['qc']['passed'] and final['qc']['passed'];assert abs(float(final['qc']['actualDuration'])-2.5)<0.1
video=final['video']
for at,color,freq in [('0.5','blue',880),('2','red',440)]:
 out,_=command('frame-'+color,[ff,'-nostdin','-v','error','-ss',at,'-i',video,'-frames:v','1','-vf','scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-']);rgb=list(out);assert rgb[2 if color=='blue' else 0]>150 and rgb[0 if color=='blue' else 2]<60,(color,rgb)
 out,_=command('audio-'+color,[ff,'-nostdin','-v','error','-ss',at,'-i',video,'-t','0.25','-vn','-ac','1','-ar','16000','-f','f32le','-']);x=np.frombuffer(out,dtype='<f4');detected=float(np.fft.rfftfreq(len(x),1/16000)[np.argmax(np.abs(np.fft.rfft(x)))]);assert abs(detected-freq)<12,(freq,detected)
frame,_=cli('bounded-frame',['inspect','demo',bid,'--at','1/2']);assert Path(frame['path']).stat().st_size<1_000_000
frame2,_=cli('bounded-frame-cache',['inspect','demo',bid,'--at','1/2']);assert frame2['cached']
cli('project-reopen',['project','open','demo']);history,_=cli('revision-history',['history','demo']);assert len(history['revisions'])==1
assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in R.iterdir()};assert not Path('/fixture/SHOULD_NOT_EXIST').exists()
Path('/fixture/acceptance.json').write_text(json.dumps({'installedRuntime':P['badwater-video'],'nativeCLIEditableProject':True,'nativePreviewAndFinalContentChecked':True,'originalsUnchanged':True,'injectedFilenameNotExecuted':True,'frameInspectionAndCache':True,'plan':plan,'revision':revision,'preview':preview,'final':final},indent=2)+'\n');print('PASS installed CLI engine: real native project/edit/reopen, blue-red preview/final with 880/440Hz, immutable originals, injection and frame cache')
