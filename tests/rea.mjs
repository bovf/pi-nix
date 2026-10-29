// Installed, offline package gate. Run only in a private filesystem/network sandbox.
import assert from "node:assert/strict";
import { readFileSync, mkdirSync, mkdtempSync, readdirSync, lstatSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { execFileSync, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { withStdioMcp } from "./mcp-stdio.mjs";

const [pkg] = process.argv.slice(2);
const root = `${pkg}/lib/rea`;
const manifest = JSON.parse(readFileSync(`${root}/package.json`));
const catalog = JSON.parse(readFileSync(`${root}/dist/mcp-catalog.json`));
const run = (...args) => execFileSync(`${pkg}/bin/rea`, args, { encoding: "utf8", timeout: 60_000 });
assert.equal(run("--version").trim(), manifest.version);
assert.match(run("--help"), /REA|rea/);
const health = JSON.parse(run("doctor", "--provider", "ghidra", "--json"));
assert.equal(health.healthy, true, JSON.stringify(health.scope_checks));
for (const args of [["setup"], ["update"], ["--update"], ["uninstall"], ["--json", "setup"], ["--format=json", "update"], ["mcp", "add"], ["--incur-update-check"]]) {
  const result = spawnSync(`${pkg}/bin/rea`, args, { encoding: "utf8" });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /managed by Nix/);
}
// Incur accepts one optional leading CLI-name token for builtins. Exercise
// registration with empty and populated private homes; refusal must not write,
// replace or remove config, even with global flags or a missing package runner.
const registrationRefusals = [];
function snapshot(directory) {
  return ["", ...readdirSync(directory, { recursive: true }).sort()].map(name => {
    const path = join(directory, name);
    const stat = lstatSync(path, { bigint: true });
    return [name, String(stat.mode), String(stat.mtimeNs), String(stat.ctimeNs), stat.isFile() ? readFileSync(path).toString("base64") : null];
  });
}
for (const prefix of [[], ["rea"]]) {
  for (const action of ["add", "remove"]) {
    const command = [...prefix, "mcp", action, "--agent", "amp"];
    const variants = [command, ["--json", ...command], ["--format=json", ...command], ["--format", "json", ...command], [...prefix, "mcp", "--json", action, "--agent", "amp"]];
    for (const args of variants) {
      for (const existingConfig of [false, true]) {
        const fixture = mkdtempSync(join(process.cwd(), "rea-registration-"));
        const home = join(fixture, "home");
        const work = join(fixture, "work");
        mkdirSync(home);
        mkdirSync(work);
        if (existingConfig) {
          mkdirSync(join(home, ".config/amp"), { recursive: true });
          writeFileSync(join(home, ".config/amp/settings.json"), JSON.stringify({
            retained: "fixture-only", "amp.mcpServers": { rea: { command: "/fixture-owned/rea", args: ["mcp"] }, other: { command: "/fixture-owned/other" } },
          }) + "\n", { mode: 0o600 });
        }
        const before = snapshot(fixture);
        const result = spawnSync(`${pkg}/bin/rea`, args, {
          encoding: "utf8", timeout: 10_000, cwd: work,
          env: { ...process.env, HOME: home, XDG_CONFIG_HOME: join(home, ".config"), PATH: "" },
        });
        assert.ifError(result.error);
        assert.deepEqual(snapshot(fixture), before, `registration wrote fixture config: ${JSON.stringify(args)}`);
        assert.equal(result.status, 1, JSON.stringify(args));
        assert.match(result.stderr, /managed by Nix/, JSON.stringify(args));
        registrationRefusals.push({ args, existingConfig, exitStatus: result.status, fixtureUnchanged: true });
        rmSync(fixture, { recursive: true });
      }
    }
  }
}
writeFileSync("rea-registration-refusals.json", JSON.stringify(registrationRefusals, null, 2));
assert.equal(registrationRefusals.length, 40);
const require = createRequire(`${root}/package.json`);
assert.ok(require("semver").satisfies(process.versions.node, manifest.engines.node), "managed Node violates REA engine bound");
assert.equal(typeof require("@lydell/node-pty").spawn, "function", "real native PTY module must load");
assert.throws(() => require.resolve("frida"), /Cannot find module/);
const transcript = await withStdioMcp(`${pkg}/bin/rea`, ["mcp"], async (request, initialized) => {
  assert.equal(initialized.serverInfo.version, manifest.version);
  const listed = await request("tools/list", {});
  assert.deepEqual(listed.tools.map(t => t.name).sort(), catalog.tools.map(t => t.name).sort());
  assert.equal(listed.tools.length, 229);
  const actual = new Map(listed.tools.map(t => [t.name, t]));
  for (const tool of catalog.tools) {
    assert.deepEqual(actual.get(tool.name), tool, tool.name);
  }
  // Read-only runtime settings, not a provider/session/process/network operation.
  assert.deepEqual((await request("prompts/list", {})).prompts, catalog.prompts.map(({ parameters, ...prompt }) => prompt));
  const settings = await request("tools/call", { name: "inspect_analysis_settings", arguments: {} });
  assert.notEqual(settings.isError, true);
});
mkdirSync("synthetic-app", { recursive: true });
writeFileSync("synthetic-app/package.json", JSON.stringify({ name: "synthetic-rea-fixture", version: "1.0.0", main: "index.js" }));
writeFileSync("synthetic-app/index.js", 'export function fixtureAdd(a, b) { return a + b; }\n');
const inspection = run("analyze-javascript-application", `${process.cwd()}/synthetic-app`, "--json");
assert.match(inspection, /fixtureAdd|index.js/);
writeFileSync("rea-mcp-transcript.json", JSON.stringify(transcript, null, 2));
console.log(`PASS: REA ${manifest.version}; 40 registration refusals with unchanged fixture files/metadata; exact 229-tool MCP catalog/schemas and 6 prompts, settings, CLI/Ghidra health, real PTY import, synthetic static JS; no live targets`);
