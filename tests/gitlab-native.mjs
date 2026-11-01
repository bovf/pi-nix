// Installed package/skill/CLI fixture; inert HOME and no credentials/provider calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const [core, pkg] = process.argv.slice(2);
assert.equal(process.env.PI_OFFLINE, '1');
assert(core?.startsWith('/nix/store/') && pkg?.startsWith('/nix/store/'));
const home = process.env.HOME, agentDir = path.join(home, '.pi/agent'); fs.mkdirSync(agentDir, {recursive: true});
const manifest = JSON.parse(fs.readFileSync(path.join(pkg, 'package.json'), 'utf8'));
assert.equal(manifest.name, 'badwater-gitlab'); assert.deepEqual(manifest.pi.extensions, []);
assert.deepEqual(manifest.pi.skills, ['./skills/badwater-gitlab']); assert(!manifest.dependencies);
const sdk = await import(pathToFileURL(`${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent/dist/index.js`));
fs.writeFileSync(path.join(agentDir, 'settings.json'), JSON.stringify({packages: [pkg], enableInstallTelemetry: false, enableAnalytics: false}), {mode: 0o600});
const settingsManager = sdk.SettingsManager.create(process.cwd(), agentDir);
const loader = new sdk.DefaultResourceLoader({cwd: process.cwd(), agentDir, settingsManager, noContextFiles: true}); await loader.reload();
assert.deepEqual(loader.getExtensions().errors, []); assert.deepEqual(loader.getExtensions().warnings, []); assert.deepEqual(loader.getSkills().diagnostics, []);
const skills = loader.getSkills().skills.filter(s => s.name === 'badwater-gitlab'); assert.equal(skills.length, 1); assert.equal(skills[0].disableModelInvocation, true);
const text = fs.readFileSync(path.join(pkg, 'skills/badwater-gitlab/SKILL.md'), 'utf8'); assert(text.includes('not permission to connect')); assert(text.includes('GitLab account/token permissions'));
for (const file of ['connection.md', 'cli.md', 'review.md', 'ci.md']) assert(fs.statSync(path.join(pkg, 'references', file)).isFile());
const cli = fs.readFileSync(path.join(pkg, 'references/cli.md'), 'utf8'); assert(!cli.includes('@GLAB')); assert(cli.includes('/nix/store/'));
const env = {HOME: home, XDG_CONFIG_HOME: process.env.XDG_CONFIG_HOME, GLAB_CHECK_UPDATE: '0', GLAB_SEND_TELEMETRY: '0', DO_NOT_TRACK: '1', PATH: process.env.PATH};
for (const args of [['--version'], ['auth', 'login', '--help'], ['mr', 'view', '--help'], ['mr', 'diff', '--help'], ['issue', 'view', '--help'], ['ci', 'status', '--help']]) {
  const result = spawnSync(path.join(pkg, 'bin/glab'), args, {env, cwd: process.cwd(), encoding: 'utf8', timeout: 20000});
  assert.equal(result.status, 0, `offline CLI help failed for ${JSON.stringify(args)}: ${result.stderr}`);
  if (args[0] === '--version') assert(/\b1\.\d+\.\d+/.test(result.stdout));
  if (args[0] === 'auth') assert(result.stdout.includes('--hostname'));
  if (args[0] === 'mr' || args[0] === 'issue' || args[0] === 'ci') assert(result.stdout.includes('--repo'));
}
assert(!fs.existsSync(path.join(agentDir, 'mcp-auth.json'))); assert(!fs.existsSync(path.join(agentDir, 'auth.json')));
console.log('PASS installed explicit GitLab skill/managed CLI/version and pinned command help; no extension, credentials, login or model request');
