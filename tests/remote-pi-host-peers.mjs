// Run with node --experimental-import-meta-resolve in an empty HOME/cwd inside the same filesystem/network sandbox
// as load-extensions.mjs. No daemon, broker, identity storage or model calls.
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const [core, remote, todo] = process.argv.slice(2);
assert(core && remote && todo, "provide Pi, remote-pi and rpiv-todo store paths");
const host = `${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent`;
const peers = ["@earendil-works/pi-coding-agent", "@earendil-works/pi-tui", "typebox"];
const resolve = (name, root) => import.meta.resolve(name, pathToFileURL(`${root}/package.json`));
const manifest = async (root) => JSON.parse(await readFile(`${root}/package.json`, "utf8"));
function checkManifest(pkg, names) {
  for (const name of names) {
    assert.equal(pkg.dependencies?.[name], undefined, `${name} is a private dependency`);
    assert.equal(pkg.peerDependencies?.[name], "*", `${name} must be a host peer`);
  }
}
async function checkIdentity(root) {
  for (const name of peers) {
    const actual = await realpath(new URL(resolve(name, root)));
    const expected = await realpath(new URL(resolve(name, host)));
    assert.equal(actual, expected, `${name} has a conflicting installed copy`);
    assert.equal(await import(pathToFileURL(actual)), await import(pathToFileURL(expected)));
  }
}
checkManifest(await manifest(remote), peers);
checkManifest(await manifest(todo), ["typebox"]);
await checkIdentity(remote);
// rpiv-todo is extension-only and must not retain its former private typebox.
await assert.rejects(realpath(`${todo}/node_modules/typebox`), { code: "ENOENT" });
for (const entry of ["dist/index.js", "dist/bin/supervisord.js"]) {
  const run = spawnSync(process.execPath, [`${remote}/${entry}`, "--help"], {
    encoding: "utf8", timeout: 10_000,
  });
  assert.ifError(run.error);
  process.stderr.write(run.stderr);
  assert.equal(run.status, 0, run.stderr);
  assert.equal(run.stderr, "");
  assert.match(run.stdout, /Usage:/);
}

// Negative controls: both the old manifest diagnostic AND a manifest-only repair
// retaining a conflicting native copy must fail. No old code needs execution.
const fixture = await mkdtemp(join(process.cwd(), "bad-peers-"));
try {
  const bad = { type: "module", dependencies: Object.fromEntries(peers.map((p) => [p, "^0.79.10"])),
    pi: { extensions: ["./index.js"] } };
  assert.throws(() => checkManifest(bad, peers), /private dependency/);
  await writeFile(`${fixture}/package.json`, JSON.stringify(bad));
  await writeFile(`${fixture}/index.js`, "export default function () {}\n");
  for (const peer of peers) {
    const dir = `${fixture}/node_modules/${peer}`;
    await mkdir(dir, { recursive: true });
    await writeFile(`${dir}/package.json`, JSON.stringify({ name: peer, main: "index.js" }));
    await writeFile(`${dir}/index.js`, "module.exports = {};\n");
  }
  await assert.rejects(checkIdentity(fixture), /conflicting installed copy/);
  const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(`${host}/dist/index.js`));
  const loader = new DefaultResourceLoader({ cwd: process.cwd(), agentDir: `${process.env.HOME}/.pi/agent`,
    settingsManager: SettingsManager.inMemory({ packages: [fixture] }), noContextFiles: true });
  await loader.reload();
  assert.deepEqual(loader.getExtensions().errors, []);
  assert.equal(loader.getExtensions().warnings.length, 1);
  assert.match(loader.getExtensions().warnings[0].warning, /Host-provided extension packages/);
  for (const peer of peers) assert(loader.getExtensions().warnings[0].warning.includes(peer));
} finally {
  await rm(fixture, { recursive: true, force: true });
}
console.log("PASS: native host module identity; standalone CLI imports; rpiv-todo upstream fix; old manifest/copy negative controls");
