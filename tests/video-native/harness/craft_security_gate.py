import hashlib,json,subprocess,sys
from pathlib import Path
from mcp_client import MCP
P=json.loads(Path('/harness/paths.json').read_text());raw=Path('/fixture/raw');raw.mkdir();derived=Path('/fixture/derived');derived.mkdir();(derived/'other').mkdir();(derived/'other/user-file').write_bytes(b'untouched sibling');protected=raw/'immutable.fcproj';protected.write_bytes(b'untouched raw');before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [protected,derived/'other/user-file']};cfg=Path('/fixture/craft.json');cfg.write_text(json.dumps({'application':'filmcraft','command':P['filmcraft']+'/bin/filmcraft-cli','readRoots':[str(raw)],'writeRoot':str(derived)}));m=MCP([P['badwater-craft-mcp']+'/bin/badwater-craft-mcp',str(cfg)],'scope-security')
try:
 m.tool('command_run',{'id':'file.newProject','params':{'name':'Scope security'}});m.tool('command_run',{'id':'file.saveAs','params':{'path':str(derived/'filmcraft/allowed.fcproj')}});assert (derived/'filmcraft/allowed.fcproj').is_file()
 for path in [str(protected),str(derived/'other/forbidden.fcproj'),'/fixture/home/forbidden.fcproj','/escape.fcproj',str(derived/'filmcraft/../other/traversal.fcproj')]:
  r=m.call('tools/call',{'name':'command_run','arguments':{'id':'file.saveAs','params':{'path':path}}});assert r.get('isError'),r
 assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [protected,derived/'other/user-file']};assert not (derived/'other/forbidden.fcproj').exists();assert not (derived/'other/traversal.fcproj').exists()
 r=m.call('tools/call',{'name':'command_run','arguments':{'id':'file.open','params':{'path':str(derived/'other/user-file')}}});assert r.get('isError'),r
finally:m.close()
# Independent syscalls/mount-table probe using byte-identical shared production policy.
video=Path(P['badwater-video'])/'lib/badwater-video';craft=Path(P['badwater-craft-mcp'])/'lib/badwater-craft-mcp';assert (video/'store.py').read_bytes()==(craft/'store.py').read_bytes();sys.path.insert(0,str(video));from store import Policy
M=json.loads(Path('/harness/video-runtime.json').read_text());c={**json.loads(Path(M['defaults']['storePath']).read_text()),'readRoots':[str(raw)],'writeRoot':str(derived/'filmcraft')};sentinel=Path('/fixture/home/private-user-file');sentinel.write_bytes(b'private synthetic home');probe='''import json,os
from pathlib import Path
mounts={p[4]:p[5].split(',') for p in (line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines())}
assert 'ro' in mounts['/'];assert 'ro' in mounts['/fixture/raw'];assert 'rw' in mounts['/fixture/derived/filmcraft']
for path in ['/fixture/derived/other/user-file','/fixture/home/private-user-file']:
 try:Path(path).read_bytes();raise AssertionError('unauthorized sibling/private HOME visible')
 except FileNotFoundError:pass
for path in ['/fixture/raw/immutable.fcproj','/escape-syscall']:
 try:Path(path).write_bytes(b'denied');raise AssertionError('unauthorized write allowed')
 except PermissionError:pass
 except OSError as exc:assert exc.errno==30
Path('/fixture/derived/filmcraft/syscall-allowed').write_bytes(b'allowed')
print(json.dumps({'rootRoMount':True,'rawRoMount':True,'appRwMount':True,'siblingAndPrivateHomeNotReadable':True,'rawAndRootWriteSyscallsDenied':True}))
''';result=subprocess.run(Policy(c).sandbox([P['python3']+'/bin/python3','-c',probe]),capture_output=True,text=True,timeout=20);assert result.returncode==0 and not result.stderr,(result.returncode,result.stderr);syscalls=json.loads(result.stdout);Path('/fixture/namespace-syscalls.json').write_text(json.dumps(syscalls,indent=2)+'\n');assert protected.read_bytes()==b'untouched raw'
Path('/fixture/acceptance.json').write_text(json.dumps({'launcher':P['badwater-craft-mcp'],'rawImmutable':True,'siblingOutputsHiddenAndUnauthorizedWritesRefused':True,'rootRemountedReadOnly':True,'authorizedNativeProjectSaved':True,'byteIdenticalPolicySyscallsAndMountTable':syscalls,'traversalAndPrivateHomeDenied':True,'scope':'Real native FilmCraft operations inside shared per-app namespace policy; no model/live settings/GUI'},indent=2));print('PASS native confined project write; read-only raw/root, hidden sibling outputs, traversal/private-home refusal, zero unexpected diagnostics')
