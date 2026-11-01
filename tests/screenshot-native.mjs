// Inert SDK/stdio fixture. No real desktop, browser target or model request.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
assert.equal(process.env.BADWATER_SCREENSHOT_FIXTURE, '1'); assert.equal(process.env.PI_OFFLINE, '1');
const [core, pkg, python] = process.argv.slice(2);
const sdk = await import(pathToFileURL(`${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent/dist/index.js`));
const {builtInExtensions} = await import(pathToFileURL(`${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent/dist/extensions/index.js`));
const agentDir = path.join(process.env.HOME, '.pi/agent'); fs.mkdirSync(agentDir, {recursive: true});
fs.writeFileSync(path.join(agentDir, 'settings.json'), JSON.stringify({packages: [pkg], defaultTools: ['+codemode'], enableInstallTelemetry: false, enableAnalytics: false}), {mode: 0o600});
fs.writeFileSync(path.join(agentDir, 'mcp.json'), JSON.stringify({mcpServers: {'badwater-screenshot': {command: path.join(pkg, 'bin/badwater-screenshot'), args: ['mcp'], exposure: 'codemode'}}}), {mode: 0o600});
const settingsManager = sdk.SettingsManager.create(process.cwd(), agentDir);
const loader = new sdk.DefaultResourceLoader({cwd: process.cwd(), agentDir, settingsManager, noContextFiles: true, extensionFactories: builtInExtensions.filter(e => ['mcp', 'codemode', 'tool-search'].includes(e.name))}); await loader.reload();
const loaded = loader.getExtensions(); assert.deepEqual(loaded.errors, []); assert.deepEqual(loaded.warnings, []); assert.deepEqual(loader.getSkills().diagnostics, []);
assert.equal(loader.getSkills().skills.filter(s => s.name === 'badwater-screenshot' && s.disableModelInvocation).length, 1);
assert.equal(loaded.extensions.filter(e => e.commands.has('mcp')).length, 1);
const modelRuntime = await sdk.ModelRuntime.create({authPath: path.join(agentDir, 'inert-auth.json'), modelsPath: null, refreshOnCreate: false, allowModelNetwork: false});
const {session} = await sdk.createAgentSession({cwd: process.cwd(), agentDir, settingsManager, resourceLoader: loader, sessionManager: sdk.SessionManager.inMemory(process.cwd()), modelRuntime,
  model: {id: 'inert', name: 'Inert', provider: 'fixture', api: 'openai-completions', baseUrl: 'http://127.0.0.1:1', reasoning: false, input: ['text'], cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0}, contextWindow: 8192, maxTokens: 1}});
const errors = [];
try {
  await session.bindExtensions({mode: 'print', onError: error => errors.push(error)});
  const mcp = loaded.extensions.find(e => e.path === 'builtin:mcp'), ctx = {cwd: process.cwd(), hasUI: false, mode: 'print', ui: {notify() {}}}; await mcp.commands.get('mcp').handler('', ctx);
  const call = (name, args) => mcp.tools.get('mcp__badwater_screenshot__' + name).definition.execute('fixture-' + name, args, undefined, undefined, ctx);
  const caps = await call('screenshot_capabilities', {}); assert(!caps.isError); assert(caps.content.some(c => c.type === 'text' && c.text.includes('badwater-screenshot')));
  const root = path.join(process.env.XDG_STATE_HOME, 'badwater-screenshot'); assert(!fs.existsSync(root), 'startup/capability listing touched capture storage or desktop');
  const id = 'a'.repeat(32), directory = path.join(root, 'captures', id); fs.mkdirSync(directory, {recursive: true, mode: 0o700});
  const image = path.join(directory, 'capture.png'); const generated = spawnSync(python, ['-c', 'from PIL import Image;import sys;Image.new("RGB",(8,6),"navy").save(sys.argv[1])', image], {encoding: 'utf8'}); assert.equal(generated.status, 0, generated.stderr); fs.chmodSync(image, 0o600);
  const bytes = fs.readFileSync(image); fs.writeFileSync(path.join(directory, 'capture.json'), JSON.stringify({version: 1, id, kind: 'synthetic-fixture', images: {capture: {file: 'capture.png', width: 8, height: 6, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length}}}), {mode: 0o600});
  const metadata = await call('screenshot_read_capture', {capture_id: id}); assert(!metadata.isError); assert(!metadata.content.some(c => c.type === 'image'));
  const shared = await call('screenshot_read_capture', {capture_id: id, share_with_model: true, crop: [0, 0, 4, 3]}); assert(!shared.isError); const block = shared.content.find(c => c.type === 'image'); assert(block); assert.equal(block.mimeType, 'image/png'); assert(Buffer.from(block.data, 'base64').subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
  const invalid = await call('screenshot_read_capture', {capture_id: '../../private', share_with_model: true}); assert(invalid.isError); assert.deepEqual(errors, []);
  console.log('PASS installed explicit screenshot skill/native stdio MCP, passive startup/capabilities, metadata-only default, explicit cropped synthetic PNG sharing and path rejection; no live GUI/model/target capture');
} finally {
  const {emitSessionShutdownEvent} = await import(pathToFileURL(`${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/runner.js`));
  await emitSessionShutdownEvent(session.extensionRunner, {type: 'session_shutdown', reason: 'quit'});
  session.dispose();
}
