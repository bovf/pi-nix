import hashlib,json,subprocess,sys,wave
from pathlib import Path
from mcp_client import MCP
P=json.loads(Path('/harness/paths.json').read_text());name=sys.argv[1]
args={'pdfcraft':['--root','/fixture'],'vectorcraft':['--headless','--automation-read-root','/fixture','--automation-write-root','/fixture']}.get(name,[])
def data(result):
 blocks=[c['text'] for c in result['content'] if c['type']=='text']
 try:return json.loads('\n'.join(blocks))
 except ValueError:return '\n'.join(blocks)
Path('/fixture/raw').mkdir(); Path('/fixture/derived').mkdir(); Path('/fixture/craft.json').write_text(json.dumps({'application':name,'command':P[name]+'/bin/'+name+'-cli','readRoots':['/fixture/raw'],'writeRoot':'/fixture/derived'})); m=MCP([P['badwater-craft-mcp']+'/bin/badwater-craft-mcp','/fixture/craft.json'],'wrapped-'+name);assert m.call('tools/list',{})['tools']
try:
 if name=='cadcraft':
  m.tool('new_drawing',{'metric':True});v=data(m.tool('inspect_drawing',{}));assert v
 elif name=='deckcraft':
  m.tool('new_presentation',{});m.tool('add_text_box',{'x':10,'y':20,'w':300,'text':'Badwater native deck'});v=data(m.tool('inspect_slide',{}));assert 'Badwater native deck' in json.dumps(v)
 elif name=='designcraft':
  m.tool('new_document',{'title':'Badwater native design','pages':2});v=data(m.tool('inspect_document',{}));assert 'Badwater native design' in json.dumps(v)
 elif name=='effectcraft':
  cmds=data(m.tool('command_list',{}));Path('/fixture/commands.json').write_text(json.dumps(cmds,indent=2)+'\n');m.tool('command_run',{'id':'comp.new','params':{'name':'Badwater native effects','width':64,'height':64,'duration':1}});v=data(m.tool('get_project',{}));assert 'Badwater native effects' in json.dumps(v)
 elif name=='filmcraft':
  m.tool('command_run',{'id':'file.newProject','params':{'name':'Badwater native film'}});m.tool('command_run',{'id':'file.newSequence','params':{'name':'Badwater MCP sequence','width':64,'height':64,'fps':12}});v=data(m.tool('sequence_inspect',{}));assert 'Badwater MCP sequence' in json.dumps(v)
 elif name=='gridcraft':
  m.tool('new_workbook',{});m.tool('set_cell',{'cell':'A1','input':'21'});m.tool('set_cell',{'cell':'B1','input':'=A1*2'});v=data(m.tool('get_cell',{'cell':'B1'}));assert '42' in json.dumps(v)
 elif name=='lightcraft':
  subprocess.run([P['ffmpeg']+'/bin/ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=orange:s=64x64','-frames:v','1','/fixture/raw/photo.png'],check=True);original=hashlib.sha256(Path('/fixture/raw/photo.png').read_bytes()).hexdigest();m.tool('import',{'paths':['/fixture/raw/photo.png'],'mode':'add'});v=data(m.tool('cmd_catalog_stats',{}));assert v;assert original==hashlib.sha256(Path('/fixture/raw/photo.png').read_bytes()).hexdigest()
 elif name=='pdfcraft':
  c=data(m.tool('doc_create',{'from':'blank','pages':2,'name':'Badwater native PDF'}));Path('/fixture/create.json').write_text(json.dumps(c,indent=2)+'\n');v=data(m.tool('doc_inspect',{}));assert 'Badwater native PDF' in json.dumps(v)
 elif name=='photocraft':
  m.tool('doc_new',{'width':64,'height':48,'name':'Badwater native image','background':'#ff0000'});v=data(m.tool('doc_inspect',{}));assert 'Badwater native image' in json.dumps(v)
 elif name=='soundcraft':
  subprocess.run([P['ffmpeg']+'/bin/ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=330:sample_rate=48000:duration=2','-c:a','pcm_s16le','/fixture/raw/mic.wav'],check=True);original=hashlib.sha256(Path('/fixture/raw/mic.wav').read_bytes()).hexdigest();m.tool('new_session',{'name':'Badwater sound processing'});imp=data(m.tool('import_audio',{'path':'/fixture/raw/mic.wav'}));Path('/fixture/import.json').write_text(json.dumps(imp,indent=2)+'\n');m.tool('execute',{'command':'clip.gain','params':{'clips':[imp['imported'][0]['clip']],'db':-6}});m.tool('save_session',{'path':'/fixture/derived/soundcraft/processed.scraft'});v=data(m.tool('bounce_mix',{'path':'/fixture/derived/soundcraft/processed.wav','start':{'seconds':0},'end':{'seconds':2},'bit_depth':'16','normalize':False}));m.tool('open_session',{'path':'/fixture/derived/soundcraft/processed.scraft'});assert original==hashlib.sha256(Path('/fixture/raw/mic.wav').read_bytes()).hexdigest();assert Path('/fixture/derived/soundcraft/processed.wav').stat().st_size>10000
 elif name=='vectorcraft':
  m.tool('draw_shape',{'shape':'rectangle','x':10,'y':20,'width':30,'height':40,'fill':'#ff0000'});v=data(m.tool('inspect_document',{}));assert v
 elif name=='wordcraft':
  m.tool('new_document',{'template':'blank'});m.tool('type_text',{'text':'Badwater native words'});v=data(m.tool('get_text',{}));assert 'Badwater native words' in json.dumps(v)
 else:raise ValueError(name)
 Path('/fixture/result.json').write_text(json.dumps({'application':name,'nativeMcpInitializeListMeaningfulOperation':True,'result':v},indent=2)+'\n');print('PASS',name,'real native MCP operation')
finally:m.close()
