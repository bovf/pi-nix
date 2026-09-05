// Run with Node 24 in an empty HOME/cwd and a Linux network namespace:
// unshare -Urn node tests/subagents-host-peers.mjs <pi store path> <pi-subagents store path>
// Uses the installed extension's resolver, not a copied alias list or fallback.
import assert from "node:assert/strict";
import { fork } from "node:child_process";
import { randomUUID } from "node:crypto";
import { once } from "node:events";
import { mkdtemp, readFile, realpath, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const [core, subagents, childSocket, childServerId] = process.argv.slice(2);
assert(core && subagents, "provide Pi and pi-subagents store paths");
const root = `${core}/lib/node_modules/pi-monorepo`;
const { HOST_PEER_ALIASES, resolveHostPeerAliases, resolvePackageSubpath } = await import(
  pathToFileURL(`${subagents}/src/runs/background/runner-aliases.ts`)
);
const resolved = resolveHostPeerAliases(root, subagents);
assert.deepEqual(resolved.missing, [], "background runner host peers must exist");
assert.deepEqual(resolved.supplemental, [], "must use host peers, not extension-local Pi 0.85.0");
const hostVersion = JSON.parse(await readFile(`${root}/package.json`, "utf8")).version;
const modules = {};
for (const { specifier, pkg } of HOST_PEER_ALIASES) {
  const target = await realpath(resolved.aliases[specifier]);
  assert(target.startsWith(`${core}/`), `${specifier} escaped the host output`);
  if (pkg !== "typebox") {
    const packageDir = pkg.endsWith("/pi-coding-agent") ? root : `${root}/node_modules/${pkg}`;
    assert.equal(JSON.parse(await readFile(`${packageDir}/package.json`, "utf8")).version, hostVersion);
  }
  modules[specifier] = await import(pathToFileURL(target));
}

if (childSocket) {
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
  // Upstream's in-memory test host: transport/hello only, no sessions or model calls.
  const directory = await mkdtemp("/tmp/pi-peer-");
  const serverId = randomUUID();
  const socket = join(directory, `${serverId}.sock`);
  const child = fork(fileURLToPath(import.meta.url), [core, subagents, socket, serverId], {
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
    console.log(`PASS: ${HOST_PEER_ALIASES.length} host aliases imported at Pi ${hostVersion}; no fallback; child Unix handshake and shutdown`);
  } finally {
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
    await exited;
    await rm(directory, { recursive: true, force: true });
  }
}
