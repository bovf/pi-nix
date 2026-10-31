import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const command = process.env.SWARM_BROWSER_COMMAND;

test('installed isolated browser captures private synthetic desktop/mobile and axe evidence',
  { skip: !command, timeout: 90_000 }, async () => {
    const root = await mkdtemp(join(tmpdir(), 'swarm-browser-test-'));
    let forbiddenHits = 0;
    let mutationHits = 0;
    let cookieHits = 0;
    const forbidden = createServer((req, res) => { forbiddenHits++; res.end('NOT AUTHORIZED'); });
    await new Promise(resolve => forbidden.listen(0, '127.0.0.1', resolve));
    const forbiddenURL = `http://127.0.0.1:${forbidden.address().port}`;
    const server = createServer((req, res) => {
      if (req.method !== 'GET' && req.method !== 'HEAD') mutationHits++;
      if (req.headers.cookie || req.headers.authorization) cookieHits++;
      if (req.url === '/redirect') { res.writeHead(302, { location: `${forbiddenURL}/redirected` }); res.end(); return; }
      if (req.url === '/download') { res.writeHead(200, { 'content-disposition': 'attachment; filename="unsafe.txt"' }); res.end('not saved'); return; }
      res.setHeader('content-type', 'text/html');
      res.end(`<!doctype html><html lang="en"><head><title>Synthetic swarm fixture</title></head>
        <body><main><h1>Private synthetic fixture</h1><button></button>
        <img src="${forbiddenURL}/image"><iframe src="file:///etc/passwd"></iframe>
        <script>fetch('/redirect').catch(()=>{}); fetch('/download').catch(()=>{});
        fetch('/mutate',{method:'POST'}).catch(()=>{});
        fetch('${forbiddenURL}/post',{method:'POST'}).catch(()=>{});
        try { new WebSocket('ws://127.0.0.1:${forbidden.address().port}/socket'); } catch {}
        document.body.dataset.emptyCookies = String(document.cookie === '');
        </script></main></body></html>`);
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    try {
      const output = join(root, 'evidence');
      const result = await new Promise((resolve, reject) => {
        const child = spawn(command, ['--url', `http://127.0.0.1:${server.address().port}`, '--output', output],
          { env: {}, stdio: ['ignore', 'pipe', 'pipe'] });
        let stdout = '', stderr = '';
        child.stdout.on('data', bytes => { stdout += bytes; });
        child.stderr.on('data', bytes => { stderr += bytes; });
        child.on('error', reject);
        child.on('exit', (code, signal) => resolve({ code, signal, stdout, stderr }));
      });
      assert.equal(result.code, 0, JSON.stringify(result));
      assert.equal(result.stderr, '');
      const report = JSON.parse(await readFile(join(output, 'report.json')));
      assert.equal(report.captures.length, 2);
      assert.ok(report.blockedRequests >= 2);
      assert.ok(report.blockedWebSockets >= 2);
      assert.ok(report.downloads >= 2);
      assert.equal(forbiddenHits, 0, 'no unauthorized network requests reach server');
      assert.equal(mutationHits, 0, 'same-origin mutation methods are refused too');
      assert.equal(cookieHits, 0, 'no cookie or authorization headers are forwarded');
      assert.ok(report.captures.every(capture => capture.initialCookieCount === 0));
      assert.ok(report.captures.every(capture => capture.httpStatus === 200));
      assert.equal((await stat(output)).mode & 0o777, 0o700);
      for (const name of ['desktop', 'mobile']) {
        const png = await readFile(join(output, `${name}.png`));
        assert.equal(png.subarray(1, 4).toString(), 'PNG');
        const axe = JSON.parse(await readFile(join(output, `${name}.axe.json`)));
        assert.ok(axe.violations.some(finding => finding.id === 'button-name'));
      }
    } finally {
      await Promise.all([new Promise(resolve => server.close(resolve)),
        new Promise(resolve => forbidden.close(resolve))]);
      await rm(root, { recursive: true, force: true });
    }
  });
