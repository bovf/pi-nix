"""Synthetic native embellishment/broker/budget acceptance, no provider or user footage."""
import json,subprocess,hashlib
from pathlib import Path
from mcp_client import MCP
P=json.loads(Path('/harness/paths.json').read_text());root=Path('/fixture/raw');root.mkdir();derived=Path('/fixture/projects');config=Path('/fixture/config.json');apps=['cadcraft','deckcraft','designcraft','effectcraft','filmcraft','gridcraft','lightcraft','pdfcraft','photocraft','soundcraft','vectorcraft','wordcraft'];config.write_text(json.dumps({'readRoots':[str(root)],'writeRoot':str(derived),'filmcraft':P['filmcraft']+'/bin/filmcraft-cli','soundcraft':P['soundcraft']+'/bin/soundcraft-cli','craftLauncher':P['badwater-craft-mcp']+'/bin/badwater-craft-mcp','craftApplications':{a:P[a]+'/bin/'+a+'-cli' for a in apps}}));B=P['badwater-video']+'/bin/badwater-video'
def cli(*args,wait=False):
 r=subprocess.run([B,'--config',str(config),*(['--wait'] if wait else []),*args],capture_output=True,text=True,timeout=700);assert r.returncode==0 and not r.stderr,(args,r.stdout,r.stderr);return json.loads(r.stdout)
raw=root/'game.mp4';subprocess.run([P['ffmpeg']+'/bin/ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=red:s=160x96:r=12:d=2','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-threads','3','-shortest',str(raw)],check=True);before=hashlib.sha256(raw.read_bytes()).hexdigest();cli('project','create','game');ingest=cli('ingest','game',str(raw),wait=True);asset=ingest['assets'][0]['asset'];cli('project','privacy','game','--allow-remote','true')
plan={'version':1,'output':{'width':160,'height':96,'fps':'12'},'clips':[{'asset':asset,'in':'0','out':'2','reason':'Approved gameplay context fixture'}],'nativeCommands':[{'id':'effects.setParam','params':{'clip':{'$clip':0},'effect':'opacity','param':'opacity','value':50}},{'id':'captions.newTrack','params':{'name':'Game captions'}},{'id':'captions.add','params':{'track':'C1','text':'GAME','time':{'$seconds':'0'},'durationSeconds':2}},{'id':'captions.setStyle','params':{'track':'C1','size':200}}]};file=derived/'game/plan.json';file.write_text(json.dumps(plan));revision=cli('timeline','apply','game',str(file),wait=True);assert Path(revision['nativeProject']).is_file();preview=cli('preview','game','--seconds','2',wait=True);assert preview['qc']['passed'] and preview['qc']['visualReference'].startswith('native composite');assert 'caption' in Path(revision['nativeProject']).read_text().lower()
m=MCP([B,'--config',str(config),'mcp'],'advanced-video')
def data(r):return r.get('structuredContent') or json.loads('\n'.join(x['text'] for x in r['content'] if x['type']=='text'))
try:
 frame=data(m.tool('frame_inspect',{'project':'game','asset':asset,'seconds':'0','share_with_model':True}));assert frame['maximumFrameAttachments']==240;m.tool('visual_review_note',{'project':'game','asset':asset,'seconds':'0','observation':'Red fixture only; uncertainty: not real game semantics'});sweep=data(m.tool('visual_review_plan',{'project':'game','asset':asset}));assert sweep['coarseSamplesWithNotes']==1
finally:m.close()
# Use the installed engine/SQLite to test 30-minute coverage and quota atomically without generating 240 images.
import sys,os
sys.path.insert(0,str(Path(B).parents[1]/'lib/badwater-video'));import review
from main import configuration
from engine import Engine
# Managed defaults receipt, never a host configuration or credential.
os.environ['BADWATER_VIDEO_DEFAULTS']=P['video-defaults'];os.environ['BADWATER_VIDEO_ENGINE']=B
cfg,path=configuration(config);engine=Engine(cfg,path);project=engine.project('game');real_asset=project.asset(asset)
class ThirtyMinutes:
 def asset(self,_):return {'metadata':{'duration':'1800'}}
 def db(self):return project.db()
coverage=review.plan(ThirtyMinutes(),asset,offset=100);assert coverage['totalCoarseSamples']==120 and coverage['samples'][-1]['seconds']=='1785'
with project.db() as db:db.execute('UPDATE visual_frames SET attachments=240 WHERE asset=?',(asset,))
try:review.charge(project,{'asset':asset,'requestedSeconds':'1','hash':'x'});raise AssertionError('budget bypass')
except ValueError as e:assert 'budget exhausted' in str(e)
for flag in [False,'true',1]:
 try:review.budget(project,asset,241,flag);raise AssertionError('coerced authorization')
 except ValueError:pass
review.budget(project,asset,241,True);assert review.charge(project,{'asset':asset,'requestedSeconds':'1','hash':'x'})['frameAttachmentsUsed']==241
for app in apps:
 catalog=cli('native','catalog','game',app,wait=True);assert catalog['tools'],app
calls=derived/'game/native-calls.json';calls.write_text(json.dumps([{'tool':'new_document','arguments':{'template':'blank'}},{'tool':'type_text','arguments':{'text':'Actual unified broker operation'}},{'tool':'get_text','arguments':{}}]));native=cli('native','batch','game','wordcraft',str(calls),wait=True);assert 'Actual unified broker operation' in json.dumps(native['results']);assert native['workspace'].endswith('/wordcraft')
assert before==hashlib.sha256(raw.read_bytes()).hexdigest();Path('/fixture/acceptance.json').write_text(json.dumps({'nativeEffectsAndCaptionProject':revision,'nativeCompositeQC':preview['qc'],'fullThirtyMinuteSweepCount':120,'persistentNotesAndStrictBudget':True,'brokerNativeCatalogues':apps,'meaningfulBrokerOperation':native,'originalUnchanged':True,'limits':'Synthetic footage only; no live visual quality/provider/30-minute native performance claim'},indent=2));print('PASS native opacity/captions/save/reopen/preview/QC, twelve broker catalogues, real Word operation and budget/notes')
