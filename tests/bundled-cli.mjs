// Run with Node in a PRIVATE filesystem + network namespace, exposing only
// /nix/store, this test and a writable empty HOME/cwd (see README). Network-only
// isolation is insufficient: extensions can discover absolute paths/Unix sockets.
// Actual packaged CLI RPC startup/shutdown; no prompts, models or service calls.
import assert from "node:assert/strict";
import { access, readFile, mkdir, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";

let [core, ...packages] = process.argv.slice(2);
assert(core && packages.length, "provide Pi and package paths, or Pi --existing-settings");
const existing = packages[0] === "--existing-settings";
assert(!existing || packages.length === 1, "existing settings supply the package selection");
assert.equal(process.cwd(), process.env.HOME, "use a private fixture HOME/cwd");
const agentDir = `${process.env.HOME}/.pi/agent`;
await mkdir(agentDir, { recursive: true });
const settingsPath = `${agentDir}/settings.json`;
const original = existing ? await readFile(settingsPath, "utf8") : undefined;
const settings = existing ? JSON.parse(original) : {
  packages, enableInstallTelemetry: false, enableAnalytics: false,
  compaction: { enabled: false }, "archimedes.mcp": { enabled: false },
};
packages = settings.packages;
assert(Array.isArray(packages) && packages.length && packages.every(p => typeof p === "string"));
assert(Array.isArray(settings.extensions ?? []));
const probe = `${process.env.HOME}/probe.mjs`;
const lifecycle = `${process.env.HOME}/lifecycle.jsonl`;
await writeFile(probe, `
import { appendFileSync } from "node:fs";
export default function (pi) {
  pi.on("session_start", (event, ctx) => {
    appendFileSync(${JSON.stringify(lifecycle)}, JSON.stringify({event: event.type,
      reason: event.reason, mode: ctx.mode, tools: pi.getAllTools().map(t => t.name)}) + "\\n");
  });
  pi.on("session_shutdown", event => {
    appendFileSync(${JSON.stringify(lifecycle)}, JSON.stringify({event: event.type, reason: event.reason,
      tools: pi.getAllTools().map(t => t.name)}) + "\\n");
  });
}
`);
// Preserve generated policy; add only the inert probe, then restore exact bytes.
const fixtureSettings = JSON.stringify({ ...settings, extensions: [...(settings.extensions ?? []), probe] });
await writeFile(settingsPath, fixtureSettings);
let run;
try {
  run = spawnSync(`${core}/bin/pi`, ["--offline", "--mode", "rpc", "--no-session", "--approve"], {
    input: '{"id":"resources","type":"get_commands"}\n', encoding: "utf8", timeout: 60_000,
    maxBuffer: 16 * 1024 * 1024,
  });
  assert.equal(await readFile(settingsPath, "utf8"), fixtureSettings, "CLI changed fixture settings");
} finally {
  if (existing) await writeFile(settingsPath, original);
}
// Keep complete stderr visible; no warning whitelist and no replacement loader.
process.stderr.write(run.stderr);
process.stdout.write(run.stdout);
assert.ifError(run.error);
assert.equal(run.status, 0, run.stderr);
assert.equal(run.stderr, "", "unexpected bundled CLI warning/error");
const records = run.stdout.trim().split("\n").filter(Boolean).map(line => JSON.parse(line));
assert(!records.some(r => r.type === "extension_error" || r.type === "error" ||
  r.level === "warning" || r.level === "error" || r.notifyType === "warning" || r.notifyType === "error"));
const response = records.find(r => r.id === "resources");
assert.equal(response?.success, true);
const commands = response.data.commands;
assert.equal(commands.filter(c => c.name === "mcp").length, 1, "builtin MCP must remain the sole owner");
for (const name of ["remote-pi", "lsp", "chrome-devtools", "goal", "btw"]) {
  if (packages.some(p => p.includes(name))) {
    assert(commands.some(c => c.name === name), `missing packaged /${name}`);
  }
}
const events = (await readFile(lifecycle, "utf8")).trim().split("\n").map(line => JSON.parse(line));
assert.deepEqual(events.map(e => e.event), ["session_start", "session_shutdown"]);
assert.equal(events[0].mode, "rpc");
assert.equal(events[0].reason, "startup");
assert.equal(events[1].reason, "quit");
const archimedes = packages.find(p => p.includes("pi-archimedes"));
if (archimedes) {
  const manifest = JSON.parse(await readFile(`${archimedes}/package.json`, "utf8"));
  assert.equal(manifest.dependencies["@pi-archimedes/mcp"], undefined);
  await assert.rejects(access(`${archimedes}/node_modules/@pi-archimedes/mcp`), { code: "ENOENT" });
  assert.doesNotMatch(await readFile(`${archimedes}/src/plugins.ts`, "utf8"), /id:\s*"mcp"/);
  if (settings["archimedes.web"]?.enabled !== false) {
    // Explicit extensions load before packages; inspect after all startup handlers ran.
    assert(events[1].tools.includes("fetch_content"), "Archimedes session_start lazy handler did not register web tools");
  }
}
console.log("PASS: installed bundled CLI loaded packaged extensions, one builtin /mcp, RPC startup/shutdown; no prompt");
