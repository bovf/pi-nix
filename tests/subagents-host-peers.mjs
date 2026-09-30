// Run with Node 24 in an empty HOME/cwd and a Linux network namespace:
// unshare -Urn node tests/subagents-host-peers.mjs <pi store path> <pi-subagents store path>
// Checks the installed resolver and native background child-session factory.
// The retained Pi server Unix handshake is a separate packaging check, not the
// pi-subagents 0.73 background transport (which uses in-process SDK sessions).
import assert from "node:assert/strict";
import { fork, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const [core, subagents, childSocket, childServerId] = process.argv.slice(2);
assert(core && subagents, "provide Pi and pi-subagents store paths");
const root = `${core}/lib/node_modules/pi-monorepo`;
const { HOST_PEER_ALIASES, resolveHostPeerAliases, resolvePackageSubpath } = await import(
  pathToFileURL(`${subagents}/src/runs/background/runner-aliases.js`)
);
const resolved = resolveHostPeerAliases(root);
assert.deepEqual(resolved.missing, [], "background runner host peers must exist");
// The resolver adds these required aliases for Pi >= 0.85 (not exported in its list).
const required = [...HOST_PEER_ALIASES,
  { specifier: "@earendil-works/chord", pkg: "@earendil-works/chord" },
  { specifier: "@earendil-works/chord/context", pkg: "@earendil-works/chord" },
];
assert.deepEqual(Object.keys(resolved.aliases).sort(), required.map(({ specifier }) => specifier).sort());
const hostVersion = JSON.parse(await readFile(`${root}/package.json`, "utf8")).version;
const modules = {};
// Also import the retained server and the workspaces added to Pi's offline build.
const packagedPeers = [
  { specifier: "@earendil-works/pi-codemode", pkg: "@earendil-works/pi-codemode", subpath: "." },
  { specifier: "@earendil-works/pi-mcp", pkg: "@earendil-works/pi-mcp", subpath: "." },
  { specifier: "@earendil-works/pi-durable", pkg: "@earendil-works/pi-durable", subpath: "." },
  { specifier: "@earendil-works/pi-session-backend-sqlite-node", pkg: "@earendil-works/pi-session-backend-sqlite-node", subpath: "." },
  { specifier: "@earendil-works/pi-server", pkg: "@earendil-works/pi-server", subpath: "." },
  { specifier: "@earendil-works/pi-server/unix", pkg: "@earendil-works/pi-server", subpath: "./unix" },
  { specifier: "@earendil-works/pi-client/unix", pkg: "@earendil-works/pi-client", subpath: "./unix" },
  { specifier: "@earendil-works/pi-protocol", pkg: "@earendil-works/pi-protocol", subpath: "." },
];
for (const { specifier, pkg, subpath } of [...required, ...packagedPeers]) {
  const target = await realpath(resolved.aliases[specifier] ?? resolvePackageSubpath(`${root}/node_modules/${pkg}`, subpath));
  assert(target.startsWith(`${core}/`), `${specifier} escaped the host output`);
  if (pkg !== "typebox") {
    const packageDir = pkg.endsWith("/pi-coding-agent") ? root : `${root}/node_modules/${pkg}`;
    assert.equal(JSON.parse(await readFile(`${packageDir}/package.json`, "utf8")).version, hostVersion);
  }
  if (childSocket && specifier in resolved.aliases) {
    assert.equal(await realpath(fileURLToPath(import.meta.resolve(specifier))), target,
      `${specifier} must resolve through the installed preload to the host`);
    modules[specifier] = await import(specifier);
  } else {
    modules[specifier] = await import(pathToFileURL(target));
  }
}

if (childSocket) {
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

  const testing = resolvePackageSubpath(`${root}/node_modules/@earendil-works/pi-server`, "./testing");
  const { TestServerHost } = await import(pathToFileURL(testing));
  const server = modules["@earendil-works/pi-server/unix"].createUnixServer(new TestServerHost(), {
    serverId: childServerId,
    path: childSocket,
  });
  assert(server instanceof modules["@earendil-works/pi-server"].Server);
  try {
    await server.start();
    process.send("ready");
    await once(process, "message");
  } finally {
    await server.close();
    process.disconnect();
  }
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
  // 0.73's production bootstrap reads config before importing the heavy runner.
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
        assert.match(probe.stderr, /Cannot find package '@earendil-works\/pi-[^']+'/);
        assert(!probe.stderr.includes("at runSubagent"), probe.stderr);
      }
    }
  } finally {
    await rm(asyncDir);
  }
  console.log("PASS: production bootstrap/default heavy import reached pre-dispatch storage setup; absent-alias control failed at peer import; no task");

  // Upstream's in-memory test host: transport/hello only, no sessions or model calls.
  const directory = await mkdtemp("/tmp/pi-peer-");
  const serverId = randomUUID();
  const socket = join(directory, `${serverId}.sock`);
  const child = fork(fileURLToPath(import.meta.url), [core, subagents, socket, serverId], {
    execArgv, env,
    stdio: ["ignore", "inherit", "inherit", "ipc"],
  });
  const exited = once(child, "exit");
  try {
    const [ready] = await once(child, "message", { signal: AbortSignal.timeout(10_000) });
    assert.equal(ready, "ready");
    const routes = await modules["@earendil-works/pi-client/unix"].discoverUnixServers({ directory });
    assert.deepEqual(routes, [{ serverId, path: socket }]);
    child.send("stop");
    assert.deepEqual(await exited, [0, null]);
    console.log(`PASS: ${required.length} complete host aliases at Pi ${hostVersion}; host-only imports; separate Pi server Unix handshake and shutdown`);
  } finally {
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    await exited;
    await rm(directory, { recursive: true, force: true });
  }
}
