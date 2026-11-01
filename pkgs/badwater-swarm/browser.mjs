import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { isAbsolute, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';

const DEADLINE_MS = 60_000;
const MAX_JSON_BYTES = 4 * 1024 * 1024;

export function httpURL(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
    throw new Error('Only HTTP(S) URLs without userinfo are allowed');
  return url;
}

export function authorizedOrigins(target, extraOrigins = []) {
  const url = httpURL(target);
  const extras = extraOrigins.map(value => {
    const origin = httpURL(value);
    if (origin.href !== `${origin.origin}/`)
      throw new Error('Authorization must be an exact origin, without path, query or fragment');
    return origin.origin;
  });
  // Numeric loopback avoids DNS rebinding and resolver/search-domain surprises.
  if (!['127.0.0.1', '[::1]'].includes(url.hostname) && !extras.includes(url.origin))
    throw new Error('Non-loopback target requires explicit --allow-origin authorization');
  return [...new Set([url.origin, ...extras])];
}

export function requestAllowed(value, origins) {
  try { return origins.includes(httpURL(value).origin); }
  catch { return false; }
}

export const HELP = 'Usage: swarm-browser --url URL --output /absolute/new-directory [--allow-origin ORIGIN]\nCreates a fresh isolated Chromium profile; loopback only unless an exact origin is authorized. Writes desktop/mobile screenshots and axe evidence. No browser or filesystem changes for --help.';

export function parseArguments(args) {
  if (args.length === 1 && args[0] === '--help') return {help: true};
  const options = { extraOrigins: [] };
  for (let i = 0; i < args.length; i += 2) {
    const [flag, value] = args.slice(i, i + 2);
    if (!value) throw new Error(`Missing value for ${flag}`);
    if (flag === '--allow-origin') options.extraOrigins.push(value);
    else if (flag === '--url' && !options.url) options.url = value;
    else if (flag === '--output' && !options.output) options.output = value;
    else throw new Error(`Unknown or duplicate option: ${flag}`);
  }
  if (!options.url || !options.output || !isAbsolute(options.output))
    throw new Error('Usage: swarm-browser --url URL --output /absolute/new-directory [--allow-origin ORIGIN]');
  options.origins = authorizedOrigins(options.url, options.extraOrigins);
  return options;
}

async function boundedJSON(path, value) {
  const text = JSON.stringify(value, null, 2) + '\n';
  if (Buffer.byteLength(text) > MAX_JSON_BYTES) throw new Error('Evidence exceeds 4 MiB bound');
  await writeFile(path, text, { flag: 'wx', mode: 0o600 });
}

async function capture(options, paths, proxyRequest) {
  const { chromium } = await import(pathToFileURL(join(paths.playwright, 'index.mjs')).href);
  const browser = await chromium.launch({
    headless: true,
    chromiumSandbox: true,
    args: ['--disable-background-networking', '--disable-component-update',
      '--disable-domain-reliability', '--disable-sync', '--no-pings',
      '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
      '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE [::1]'],
  });
  const report = { version: 1, url: options.url, authorizedOrigins: options.origins,
    engine: `chromium ${browser.version()}`, axe: paths.axeVersion, captures: [],
    blockedRequests: 0, blockedWebSockets: 0, downloads: 0 };
  // Browser has no external network namespace access. The parent mediates bounded
  // read-only HTTP requests over stdio; each redirect returns through this policy.
  try {
    for (const [name, viewport, mobile] of [
      ['desktop', { width: 1440, height: 900 }, false],
      ['mobile', { width: 390, height: 844 }, true],
    ]) {
      const context = await browser.newContext({ viewport, isMobile: mobile, hasTouch: mobile,
        acceptDownloads: false, serviceWorkers: 'block', permissions: [],
        reducedMotion: 'reduce' });
      context.setDefaultTimeout(10_000);
      await context.route('**/*', async route => {
        if (!requestAllowed(route.request().url(), options.origins)
          || !['GET', 'HEAD'].includes(route.request().method())) {
          report.blockedRequests++;
          return route.abort('blockedbyclient');
        }
        try {
          const response = await proxyRequest(route.request().url(), route.request().method());
          if (/attachment/i.test(response.headers['content-disposition'] ?? '')) {
            report.downloads++;
            return route.abort('blockedbyclient');
          }
          await route.fulfill({ status: response.status, headers: response.headers,
            body: Buffer.from(response.body, 'base64') });
        } catch { report.blockedRequests++; await route.abort('failed'); }
      });
      await context.routeWebSocket('**/*', socket => {
        report.blockedWebSockets++;
        socket.close();
      });
      const initialCookieCount = (await context.cookies()).length;
      const page = await context.newPage();
      page.on('download', download => { report.downloads++; void download.cancel(); });
      page.on('popup', popup => { void popup.close(); });
      const navigation = await page.goto(options.url, { waitUntil: 'load', timeout: 15_000 });
      if (!navigation?.ok()) throw new Error(`Navigation failed with HTTP ${navigation?.status() ?? 'no response'}`);
      await page.evaluate(await readFile(paths.axe, 'utf8'));
      const axe = await page.evaluate(async () => {
        const result = await window.axe.run(document, { resultTypes: ['violations', 'incomplete'] });
        return { testEngine: result.testEngine, testRunner: result.testRunner,
          testEnvironment: result.testEnvironment, toolOptions: result.toolOptions,
          violations: result.violations, incomplete: result.incomplete };
      });
      await boundedJSON(`/evidence/${name}.axe.json`, axe);
      await page.screenshot({ path: `/evidence/${name}.png`, fullPage: false, timeout: 10_000 });
      report.captures.push({ name, viewport, mobileEmulation: mobile, initialCookieCount,
        finalURL: page.url(), httpStatus: navigation.status(), screenshot: `${name}.png`, axe: `${name}.axe.json`, violations: axe.violations.length,
        incomplete: axe.incomplete.length });
      await context.close();
    }
    await boundedJSON('/evidence/report.json', report);
  } finally { await browser.close(); }
}

export async function launch(options, paths, {deadlineMs = DEADLINE_MS, spawnProcess = spawn, terminate = pid => process.kill(-pid, 'SIGKILL')} = {}) {
  // A new directory is mandatory: do not expose a pre-existing tree to browser content.
  await mkdir(options.output, { mode: 0o700 });
  const args = ['--unshare-all', '--die-with-parent', '--new-session',
    '--ro-bind', '/nix/store', '/nix/store', '--proc', '/proc', '--dev', '/dev',
    '--tmpfs', '/tmp', '--dir', '/tmp/home', '--dir', '/evidence',
    '--bind', options.output, '/evidence', '--chdir', '/tmp', '--clearenv',
    '--setenv', 'HOME', '/tmp/home', '--setenv', 'TMPDIR', '/tmp',
    '--setenv', 'PLAYWRIGHT_BROWSERS_PATH', paths.browsers,
    '--setenv', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD', '1',
    '--setenv', 'FONTCONFIG_FILE', paths.fontconfig,
    paths.node, fileURLToPath(import.meta.url), '--isolated-worker'];
  await new Promise((resolve, reject) => {
    const child = spawnProcess(paths.bwrap, args, { stdio: ['pipe', 'pipe', 'pipe'], detached: true,
      env: {} });
    const invocation = new AbortController();
    const inFlight = new Set();
    let requests = 0, closing = false, timedOut = false;
    const lines = createInterface({ input: child.stdout });
    const stop = () => { closing = true; invocation.abort(); lines.close(); };
    lines.on('line', line => {
      if (closing) return;
      const work = (async () => {
      let id;
      try {
        if (line.length > 16_384) throw new Error('Proxy request too large');
        const request = JSON.parse(line);
        id = request.id;
        if (++requests > 128 || !Number.isSafeInteger(id)
          || !['GET', 'HEAD'].includes(request.method)
          || !requestAllowed(request.url, options.origins)) throw new Error('Proxy request refused');
        const response = await fetch(request.url, { method: request.method, redirect: 'manual',
          signal: AbortSignal.any([invocation.signal, AbortSignal.timeout(10_000)]), headers: { 'accept-encoding': 'identity' } });
        const headers = Object.fromEntries(response.headers);
        const chunks = [];
        let size = 0;
        for await (const chunk of response.body ?? []) {
          size += chunk.length;
          if (size > 8 * 1024 * 1024) throw new Error('Response exceeds 8 MiB');
          chunks.push(chunk);
        }
        // Fetch decodes transport encoding, so do not forward the encoded length.
        delete headers['content-encoding'];
        delete headers['content-length'];
        if (!closing && !child.stdin.destroyed) child.stdin.write(JSON.stringify({ id, status: response.status, headers,
          body: Buffer.concat(chunks).toString('base64') }) + '\n');
      } catch {
        if (!closing && !child.stdin.destroyed) child.stdin.write(JSON.stringify({ id, error: 'Proxy request refused' }) + '\n');
      }
      })();
      inFlight.add(work);
      work.finally(() => inFlight.delete(work));
    });
    let stderr = '';
    child.stderr.on('data', bytes => { stderr = (stderr + bytes).slice(-8192); });
    const timer = setTimeout(() => { timedOut = true; stop(); try { terminate(child.pid); } catch {} }, deadlineMs);
    child.on('error', error => { clearTimeout(timer); stop(); Promise.allSettled([...inFlight]).then(() => reject(error)); });
    child.on('exit', (code, signal) => {
      clearTimeout(timer); stop();
      Promise.allSettled([...inFlight]).then(() => {
        if (code === 0 && !timedOut) resolve();
        else reject(new Error(`Isolated browser failed (${timedOut ? 'deadline' : signal ?? code}): ${stderr.trim()}`));
      });
    });
    child.stdin.on('error', () => {});
    child.stdin.write(JSON.stringify(options) + '\n');
  });
  return join(options.output, 'report.json');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    if (process.argv.length === 3 && process.argv[2] === '--help') {
      console.log(HELP);
    } else {
    const paths = JSON.parse(await readFile(new URL('./browser-paths.json', import.meta.url), 'utf8'));
    if (process.argv[2] === '--isolated-worker') {
      const lines = createInterface({ input: process.stdin });
      const pending = new Map();
      let sequence = 0;
      const iterator = lines[Symbol.asyncIterator]();
      const first = await iterator.next();
      if (!first.value || first.value.length > 16_384) throw new Error('Invalid request');
      const options = JSON.parse(first.value);
      options.origins = authorizedOrigins(options.url, options.extraOrigins);
      const responses = (async () => {
        for await (const line of { [Symbol.asyncIterator]: () => iterator }) {
          const response = JSON.parse(line);
          const request = pending.get(response.id);
          pending.delete(response.id);
          if (response.error) request?.reject(new Error(response.error));
          else request?.resolve(response);
        }
      })();
      const proxyRequest = (url, method) => new Promise((resolve, reject) => {
        const id = ++sequence;
        pending.set(id, { resolve, reject });
        process.stdout.write(JSON.stringify({ id, url, method }) + '\n');
      });
      try { await capture(options, paths, proxyRequest); }
      finally { lines.close(); process.stdin.destroy(); }
      await responses;
    } else {
      const report = await launch(parseArguments(process.argv.slice(2)), paths);
      console.log(JSON.stringify({ report }));
    }
    }
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
