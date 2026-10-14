// Run with the official Node 22 in the private filesystem/network sandbox documented in README:
// node tests/subagents-host-peers.mjs <pi store path> <pi-subagents store path>
// Checks the installed resolver and native background child-session factory.
// Pi1.2 removed experimental Unix server/client/protocol packages; supported
// integration is the native child SDK plus the separate bundled CLI RPC gate.
import assert from "node:assert/strict";
import { fork, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const [core, subagents, childMode] = process.argv.slice(2);
assert(!childMode || childMode === "native-child");
assert(core && subagents, "provide Pi and pi-subagents store paths");
const hostModules = `${core}/lib/pi/node_modules`;
const root = `${hostModules}/@earendil-works/pi-coding-agent`;
const { HOST_PEER_ALIASES, resolveHostPeerAliases, resolvePackageSubpath } = await import(
  pathToFileURL(`${subagents}/src/runs/background/runner-aliases.js`)
);
const resolved = resolveHostPeerAliases(root);
assert.deepEqual(resolved.missing, [], "background runner host peers must exist");
// Upstream marks only the removed ./node export optional; no required peer may disappear.
const obsolete = "@earendil-works/pi-agent-core/node";
assert.deepEqual(HOST_PEER_ALIASES.filter(({ optional }) => optional), [
  { specifier: obsolete, pkg: "@earendil-works/pi-agent-core", subpath: "./node", optional: true },
]);
const nodeExport = resolvePackageSubpath(`${hostModules}/@earendil-works/pi-agent-core`, "./node");
// The CLI dropped Chord in1.2, but our supported Durable helper still requires it.
// Keep the complete installed host inventory, not a filter that hides missing peers.
const required = [...HOST_PEER_ALIASES.filter(({ specifier }) => specifier !== obsolete || nodeExport !== undefined),
  { specifier: "@earendil-works/chord", pkg: "@earendil-works/chord" },
  { specifier: "@earendil-works/chord/context", pkg: "@earendil-works/chord" },
];
assert.deepEqual(Object.keys(resolved.aliases).sort(), required.map(({ specifier }) => specifier).sort());
const hostVersion = JSON.parse(await readFile(`${root}/package.json`, "utf8")).version;
for (const name of ["server", "client", "protocol"]) {
  assert.equal(resolvePackageSubpath(`${hostModules}/@earendil-works/pi-${name}`, "."), undefined,
    `removed experimental pi-${name} must not be bundled on Pi1.2`);
}
if (Number(hostVersion.split(".")[0]) >= 1) {
  assert.equal(nodeExport, undefined);
  assert.equal(resolved.aliases[obsolete], undefined);
  const fixture = await mkdtemp(join(process.cwd(), "obsolete-alias-"));
  try {
    const source = await readFile(`${subagents}/src/runs/background/runner-aliases.js`, "utf8");
    const declaration = 'export const HOST_PEER_ALIASES = [';
    assert.equal(source.split(declaration).length, 2);
    await writeFile(`${fixture}/original.mjs`, source.replace(declaration, `${declaration}\n    { specifier: "${obsolete}", pkg: "@earendil-works/pi-agent-core", subpath: "./node" },`));
    const original = await import(pathToFileURL(`${fixture}/original.mjs`));
    assert.deepEqual(original.resolveHostPeerAliases(root).missing, [obsolete], "restoring the obsolete alias must fail on Pi >=1.0");
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
}
const modules = {};
// Also import the supported helper libraries from the same host output.
const packagedPeers = [
  { specifier: "@earendil-works/pi-codemode", pkg: "@earendil-works/pi-codemode", subpath: "." },
  { specifier: "@earendil-works/pi-mcp", pkg: "@earendil-works/pi-mcp", subpath: "." },
  { specifier: "@earendil-works/pi-durable", pkg: "@earendil-works/pi-durable", subpath: "." },
];
for (const { specifier, pkg, subpath } of [...required, ...packagedPeers]) {
  const target = await realpath(resolved.aliases[specifier] ?? resolvePackageSubpath(`${hostModules}/${pkg}`, subpath));
  assert(target.startsWith(`${core}/`), `${specifier} escaped the host output`);
  if (pkg !== "typebox") {
    const packageDir = pkg.endsWith("/pi-coding-agent") ? root : `${hostModules}/${pkg}`;
    assert.equal(JSON.parse(await readFile(`${packageDir}/package.json`, "utf8")).version, hostVersion);
  }
  if (childMode && specifier in resolved.aliases) {
    assert.equal(await realpath(fileURLToPath(import.meta.resolve(specifier))), target,
      `${specifier} must resolve through the installed preload to the host`);
    modules[specifier] = await import(specifier);
  } else {
    modules[specifier] = await import(pathToFileURL(target));
  }
}

if (childMode) {
  // Exercise the actual installed background factory with the real host SDK,
  // not an injected fake session. Never prompt, query credentials, or call a model.
  const { loadRunnerChildSessionFactory } = await import(
    pathToFileURL(`${subagents}/src/runs/background/runner-child-sessions.js`)
  );
  const factory = await loadRunnerChildSessionFactory({});
  const lifecycle = [];
  const errors = [];
  try {
    const session = await factory.create({
      cwd: process.cwd(), storage: { kind: "memory" },
      ambientExtensions: false, extensionPaths: [], noSkills: true, noContextFiles: true,
      tools: [], runtime: {},
      hooks: [{ name: "packaging-lifecycle", factory(pi) {
        pi.on("session_start", (event, ctx) => {
          assert.equal(event.reason, "startup");
          assert.equal(ctx.mode, "print");
          lifecycle.push("start");
        });
        pi.on("session_shutdown", (event) => {
          assert.equal(event.reason, "quit");
          lifecycle.push("shutdown");
        });
      } }],
      onExtensionError: (error) => errors.push(error),
    });
    assert(session.sessionId);
    assert.equal(session.sessionFile, undefined);
    assert.equal(session.hasQueuedMessages(), false);
    assert.deepEqual(lifecycle, ["start"]);
    await session.dispose();
    assert.deepEqual(lifecycle, ["start", "shutdown"]);
    assert.deepEqual(errors, []);
  } finally {
    await factory.dispose();
  }
  console.log("PASS: installed native preload resolved all bare host peers; default background child factory created/disposed an in-memory SDK session; lifecycle hooks; no prompt");

  process.send("ready");
  process.disconnect();
} else {
  // Match async-execution.js's installed JS runner branch, not the JITI CLI.
  const execArgv = ["--import", pathToFileURL(`${subagents}/runner-peer-preload.mjs`).href];
  const env = {
    ...process.env,
    PI_SUBAGENTS_PI_CODING_AGENT_PACKAGE_ROOT: root,
    PI_PACKAGE_DIR: root,
    JITI_ALIAS: JSON.stringify(resolved.aliases),
    PI_ASYNC_NATIVE_RUNNER: "1",
  };
  // The production bootstrap reads config before importing the heavy runner.
  // A regular file as asyncDir fails at its initial mkdir, after the DEFAULT
  // heavy import/factory setup but before scheduling or creating a child session.
  assert.equal(env.PI_SUBAGENTS_TEST_RUNNER_EXECUTION_MODULE, undefined);
  const asyncDir = join(process.cwd(), `runner-storage-file-${randomUUID()}`);
  await writeFile(asyncDir, "inert packaging fixture");
  const config = {
    id: "packaging-probe", cwd: process.cwd(), asyncDir,
    resultPath: join(process.cwd(), "unused-result.json"), placeholder: "",
    steps: [{ agent: "never-dispatched", task: "", inheritProjectContext: false,
      inheritGlobalContext: false, inheritSkills: false }],
  };
  const runnerArgs = [...execArgv, `${subagents}/src/runs/background/subagent-runner-bootstrap.js`];
  try {
    for (const aliasesPresent of [true, false]) {
      const probe = spawnSync(process.execPath, runnerArgs, {
        env: aliasesPresent ? env : { ...env, JITI_ALIAS: "{}" },
        input: JSON.stringify(config), encoding: "utf8", timeout: 10_000,
      });
      assert.ifError(probe.error);
      assert.equal(probe.signal, null);
      assert.equal(probe.status, 1, probe.stderr);
      if (aliasesPresent) {
        assert.match(probe.stderr, /Subagent runner error:.*EEXIST.*mkdir/);
        assert(probe.stderr.includes(asyncDir), probe.stderr);
        assert.match(probe.stderr, /at runSubagent/);
        assert(!probe.stderr.includes("ERR_MODULE_NOT_FOUND"), probe.stderr);
      } else {
        assert.match(probe.stderr, /ERR_MODULE_NOT_FOUND/);
        assert(required.some(({ pkg }) => probe.stderr.includes(`Cannot find package '${pkg}'`)), probe.stderr);
        assert(!probe.stderr.includes("at runSubagent"), probe.stderr);
      }
    }
  } finally {
    await rm(asyncDir);
  }
  console.log("PASS: production bootstrap/default heavy import reached pre-dispatch storage setup; absent-alias control failed at peer import; no task");

  // Separate Node process, production preload and actual SDK child factory; no task/model.
  const child = fork(fileURLToPath(import.meta.url), [core, subagents, "native-child"], {
    execArgv, env,
    stdio: ["ignore", "inherit", "inherit", "ipc"],
  });
  const exited = once(child, "exit");
  try {
    const [ready] = await once(child, "message", { signal: AbortSignal.timeout(10_000) });
    assert.equal(ready, "ready");
    assert.deepEqual(await exited, [0, null]);
    console.log(`PASS: ${required.length} complete host aliases at Pi ${hostVersion}; host-only imports; supported native SDK child lifecycle and shutdown`);
  } finally {
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    await exited;
  }
}
