import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {EventEmitter} from 'node:events';
import {PassThrough, Writable} from 'node:stream';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {launch, parseArguments} from '../browser.mjs';

test('help succeeds without browser paths, a launch, or creating output',()=>{
 const source=fileURLToPath(new URL('../browser.mjs',import.meta.url));
 const result=spawnSync(process.execPath,[source,'--help'],{encoding:'utf8',env:{PATH:''}});
 assert.equal(result.status,0,result.stderr);assert.equal(result.stderr,'');assert.match(result.stdout,/Usage: badwater-senior-swarm-browser/);assert.match(result.stdout,/No browser or filesystem changes/);assert.deepEqual(parseArguments(['--help']),{help:true});
});
test('invocation deadline cancels an in-flight parent HTTP body and drains it',async t=>{
 const directory=await fs.mkdtemp(path.join(os.tmpdir(),'badwater-senior-swarm-browser-deadline-'));t.after(()=>fs.rm(directory,{recursive:true,force:true}));
 let admitted=0,aborted=0;let started,closed;
 const ready=new Promise(resolve=>{started=resolve;});
 const socketClosed=new Promise(resolve=>{closed=resolve;});
 const server=http.createServer((req,res)=>{admitted++;req.on('close',()=>{aborted++;closed();});res.writeHead(200,{'content-type':'text/plain'});res.write('partial');started();});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 t.after(()=>new Promise(resolve=>{server.closeAllConnections();server.close(resolve);}));
 const url=`http://127.0.0.1:${server.address().port}/slow`;
 const child=new EventEmitter();child.pid=12345;child.stdout=new PassThrough();child.stderr=new PassThrough();child.stdin=new Writable({write(_chunk,_encoding,callback){callback();}});
 const start=Date.now();
 const result=launch({url,origins:[new URL(url).origin],extraOrigins:[],output:path.join(directory,'evidence')},{node:process.execPath,bwrap:'/fixture/bwrap',browsers:'/fixture/browsers',fontconfig:'/fixture/fonts'},
  {deadlineMs:200,spawnProcess(){setImmediate(()=>child.stdout.write(JSON.stringify({id:1,url,method:'GET'})+'\n'));return child;},terminate(pid){assert.equal(pid,12345);child.emit('exit',null,'SIGKILL');}});
 await ready;await assert.rejects(result,/deadline/);
 // Observe the actual socket-close event with one safety deadline, never poll.
 let timer;
 await Promise.race([socketClosed,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('HTTP request was not cancelled')),1500);})]).finally(()=>clearTimeout(timer));
 assert.equal(admitted,1);assert.equal(aborted,1);assert(Date.now()-start<2000,'request timeout outlived invocation cancellation');
 child.stdout.end();child.stderr.end();child.stdin.end();
});
