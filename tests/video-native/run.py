#!/usr/bin/env python3
"""Reproduce installed native gates without host files/network/display/provider access.
Arguments are Nix-evaluated paths/runtime JSON receipts; no media is accepted from the host.
"""
import argparse,json,os,shutil,subprocess,tempfile,time
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('--paths',type=Path,required=True);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--output',type=Path);parser.add_argument('--apps',action='store_true');args=parser.parse_args();paths=json.loads(args.paths.read_text());runtime=json.loads(args.runtime.read_text())
for key in ['bubblewrap','bash','coreutils','python3','video-python','ffmpeg','git','espeak-ng','badwater-video','filmcraft','soundcraft']:
 value=paths[key];assert value.startswith('/nix/store/') and Path(value).exists(),key
assert paths['badwater-video']==runtime['package']['storePath'];assert paths['video-python']==runtime['python']['storePath']
output=args.output or Path(tempfile.mkdtemp(prefix='badwater-video-acceptance-'));output=output.absolute();assert str(output).startswith('/tmp/') and output.resolve()==output and not output.is_symlink(),'Use a new private /tmp evidence directory';output.mkdir(mode=0o700,exist_ok=True);assert not list(output.iterdir()),'Evidence directory must start empty';harness=output/'harness';shutil.copytree(Path(__file__).parent/'harness',harness,copy_function=shutil.copyfile);harness.chmod(0o700);(harness/'paths.json').write_text(json.dumps(paths));(harness/'video-runtime.json').write_text(json.dumps(runtime));paths['video-defaults']=runtime['defaults']['storePath'];(harness/'paths.json').write_text(json.dumps(paths));results=[]
cases=[('cli','engine_gate.py'),('mcp','engine_mcp_gate.py'),('security','engine_security_gate.py'),('qc','engine_qc_gate.py'),('controls','engine_controls_gate.py'),('aligned-audio','engine_audio_gate.py'),('diagnostics','native_diagnostic_gate.py'),('advanced','advanced_gate.py'),('editorial','editorial_gate.py'),('speech','speech_gate.py'),('artifacts','artifact_gate.py')]
if args.apps:
 cases.append(('companion-confinement','craft_security_gate.py'))
 for app in ['cadcraft','deckcraft','designcraft','effectcraft','filmcraft','gridcraft','lightcraft','pdfcraft','photocraft','soundcraft','vectorcraft','wordcraft']:
  assert paths[app].startswith('/nix/store/') and Path(paths[app]).exists();cases.append((app,'wrapped_mcp_smoke.py'))
for name,script in cases:
 fixture=output/name;fixture.mkdir(mode=0o700)
 for child in ['home','config','data','cache','runtime','tmp']:(fixture/child).mkdir(mode=0o700)
 command=[paths['bubblewrap']+'/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--ro-bind','/nix/store','/nix/store','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/bin','--ro-bind',paths['bash']+'/bin/bash','/bin/sh','--dir','/usr','--dir','/usr/bin','--ro-bind',paths['coreutils']+'/bin/env','/usr/bin/env','--bind',str(fixture),'/fixture','--ro-bind',str(harness),'/harness','--chdir','/fixture','--clearenv']
 for key,value in {'HOME':'/fixture/home','XDG_CONFIG_HOME':'/fixture/config','XDG_DATA_HOME':'/fixture/data','XDG_CACHE_HOME':'/fixture/cache','XDG_RUNTIME_DIR':'/fixture/runtime','TMPDIR':'/fixture/tmp','PATH':':'.join(paths[n]+'/bin' for n in ['python3','ffmpeg','bash','coreutils','git']),'PI_OFFLINE':'1','GIT_CONFIG_NOSYSTEM':'1','PYTHONDONTWRITEBYTECODE':'1','RAYON_NUM_THREADS':'3','OMP_NUM_THREADS':'3'}.items():command+=['--setenv',key,value]
 command += [paths['video-python']+'/bin/python3','/harness/profile_gate.py','/harness/'+script]
 if script=='wrapped_mcp_smoke.py':command.append(name)
 (output/(name+'.command.json')).write_text(json.dumps(command));start=time.monotonic()
 with (output/(name+'.stdout')).open('wb') as out,(output/(name+'.stderr')).open('wb') as err:
  try:r=subprocess.run(command,stdout=out,stderr=err,timeout=2400);status=r.returncode
  except subprocess.TimeoutExpired:status=124
 result={'case':name,'status':status,'seconds':time.monotonic()-start,'runtime':paths['badwater-video']};results.append(result);(output/'results.json').write_text(json.dumps(results,indent=2));print(name,status,flush=True)
 if status:raise SystemExit(status)
print('PASS installed synthetic native gates:',output)
