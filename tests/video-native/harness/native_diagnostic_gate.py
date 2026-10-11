"""Inert protocol fixture tests native-client diagnostics/deadlines, not editor/media quality."""
import json,os,sys,time
from pathlib import Path
P=json.loads(Path('/harness/paths.json').read_text());M=json.loads(Path('/harness/video-runtime.json').read_text());sys.path.insert(0,P['badwater-video']+'/lib/badwater-video');from native import NativeMCP,NativeError
from store import Policy
root=Path('/fixture/derived');root.mkdir();c={**json.loads(Path(M['defaults']['storePath']).read_text()),'readRoots':[],'writeRoot':str(root)};policy=Policy(c);script=root/'protocol.py';script.write_text('''import json,os,sys,time
mode=sys.argv[1]
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r:continue
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':{'protocolVersion':'2024-11-05','capabilities':{},'serverInfo':{'name':'inert-fixture','version':'1'}}}),flush=True)
 if r['method']=='initialize':
  if mode=='unexpected':os.write(2,b'unexpected fixture warning\\n')
  if mode=='line':os.write(2,b'x'*8193+b'\\n')
  if mode=='unicode':os.write(2,('😀'*2049+'\\n').encode())
  if mode=='total':os.write(2,(b'x'*4095+b'\\n')*257)
  if mode=='invalid':os.write(2,b'\\xff\\xfe\\n')
  if mode in ['line','unicode','total','invalid']:time.sleep(20)
if mode=='exit':sys.exit(7)
''');results={}
for mode,required in [('clean',None),('unexpected','unexpected native editor diagnostic'),('line','limit'),('unicode','limit'),('total','limit'),('invalid','valid UTF-8'),('exit','exited unsuccessfully')]:
 log=root/(mode+'.stderr');start=time.monotonic()
 try:
  with log.open('w') as stream:
   with NativeMCP(policy.sandbox([P['python3']+'/bin/python3',str(script),mode],root),stream,timeout=3):time.sleep(.1)
 except NativeError as exc:assert required and required in str(exc),(mode,str(exc));results[mode]=str(exc)
 else:assert required is None,mode;results[mode]='clean'
 assert time.monotonic()-start<10;assert log.stat().st_size<=1048576
Path('/fixture/acceptance.json').write_text(json.dumps({'client':P['badwater-video'],'cases':results,'diagnosticDiskBoundBytes':1048576,'shutdownSecondsBound':10,'scope':'Inert newline-protocol fixture only; native positive media acceptance lives in separate gates'},indent=2)+'\n');print('PASS native client clean/error/UTF8/line/total/exit diagnostic and bounded-shutdown controls (inert protocol only)')
