"""Sample aggregate RSS only inside the private PID namespace; no host process reads."""
import json,subprocess,sys,threading,time
from pathlib import Path
stop=threading.Event();peak=0;count=0

def sample():
 global peak,count
 while not stop.is_set():
  rss=0
  for status in Path('/proc').glob('[0-9]*/status'):
   try:
    rss+=next((int(line.split()[1]) for line in status.read_text().splitlines() if line.startswith('VmRSS:')),0)
   except (OSError,ValueError):pass
  peak=max(peak,rss);count+=1;stop.wait(.05)

thread=threading.Thread(target=sample,daemon=True);thread.start();start=time.monotonic()
try:result=subprocess.run([sys.executable,*sys.argv[1:]])
finally:stop.set();thread.join(timeout=1)
Path('/fixture/resources.json').write_text(json.dumps({'aggregatePrivateNamespaceSampledPeakRssKiB':peak,'samples':count,'intervalSeconds':.05,'wallSeconds':time.monotonic()-start,'scope':'Synthetic fixture workload; sampled aggregate, not exhaustive peak/large-recording/hardware benchmark'},indent=2)+'\n');raise SystemExit(result.returncode)
