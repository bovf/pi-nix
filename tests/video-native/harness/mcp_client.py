import json,queue,subprocess,threading
from pathlib import Path
L=Path("/fixture/logs");L.mkdir(exist_ok=True)
class MCP:
 def __init__(self,argv,label):
  self.label=label;self.log=[];self.id=0;self.q=queue.Queue();self.err=L/(label+'.stderr');self.ef=self.err.open('w');self.p=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.ef,text=True)
  def read():
   for line in self.p.stdout:self.q.put(line)
  threading.Thread(target=read,daemon=True).start()
  self.call('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'badwater-native-fixture','version':'1'}});self.notify('notifications/initialized',{})
 def notify(self,method,params):self.p.stdin.write(json.dumps({'jsonrpc':'2.0','method':method,'params':params})+'\n');self.p.stdin.flush()
 def call(self,method,params):
  self.id+=1;self.p.stdin.write(json.dumps({'jsonrpc':'2.0','id':self.id,'method':method,'params':params})+'\n');self.p.stdin.flush()
  while True:
   reply=json.loads(self.q.get(timeout=30));self.log.append(reply)
   if reply.get('id')==self.id:assert 'error' not in reply,reply;return reply['result']
 def tool(self,name,args):
  result=self.call('tools/call',{'name':name,'arguments':args});assert not result.get('isError'),result;return result
 def close(self):
  self.p.stdin.close();assert self.p.wait(timeout=10)==0;self.ef.close();(L/(self.label+'.json')).write_text(json.dumps(self.log,indent=2)+'\n')
  expected={
   'designcraft-mcp':'designcraft-cli: MCP server on stdio (headless (in-process engine, no window))\n',
   'gridcraft-mcp':'gridcraft-cli: MCP server on stdio (headless (in-process engine, no window))\n',
   'lightcraft-mcp':'lightcraft-cli mcp: serving MCP on stdio (headless)\n',
   'pdfcraft-mcp':'pdfcraft-cli: MCP server on stdio (protocol 2025-06-18); close stdin to stop\n',
   'vectorcraft-mcp':'vectorcraft-cli: files confined: read root /fixture, write root /fixture\nvectorcraft-cli: MCP server on stdio (headless)\n',
  }
  assert self.err.read_text()==expected.get(self.label,''),self.err.read_text()
