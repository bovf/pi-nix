// Run in a PRIVATE filesystem/network namespace with empty HOME/cwd and
// store-only Node + Git + shell on PATH. No live repositories, settings or auth.
// Usage: node tests/archimedes-footer.mjs <pi store path> <archimedes store path>
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { stripVTControlCharacters } from "node:util";

const [core, archimedes] = process.argv.slice(2);
assert(core && archimedes, "provide Pi and Archimedes store paths");
assert.equal(process.cwd(), process.env.HOME, "use a private fixture HOME/cwd");
const sdkRoot = `${core}/lib/pi/node_modules/@earendil-works`;
const { DefaultResourceLoader, SettingsManager, Theme } = await import(
  pathToFileURL(`${sdkRoot}/pi-coding-agent/dist/index.js`)
);
const { getThemeByName } = await import(
  pathToFileURL(`${sdkRoot}/pi-coding-agent/dist/modes/interactive/theme/theme.js`)
);
const { visibleWidth } = await import(pathToFileURL(`${sdkRoot}/pi-tui/dist/index.js`));

// A real, clean Git repository one commit ahead of a local upstream; no remote.
await mkdir("repo");
process.chdir("repo");
const git = (...args) => execFileSync("git", args, { encoding: "utf8", timeout: 5_000 });
git("init", "--quiet", "--initial-branch=footer-test");
const commit = message => git("-c", "user.name=Footer Test", "-c", "user.email=footer@example.invalid",
  "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", message);
commit("baseline");
git("branch", "baseline");
commit("ahead");
git("branch", "--set-upstream-to=baseline");
assert.match(git("status", "--porcelain=v2", "--branch"), /^# branch\.ab \+1 -0$/m);
assert.equal(git("status", "--porcelain"), "", "fixture must be clean, not merely dirty");

const footerPath = `${archimedes}/node_modules/@pi-archimedes/footer/src/index.ts`;
const loader = new DefaultResourceLoader({
  cwd: process.cwd(), agentDir: `${process.env.HOME}/.pi/agent`,
  settingsManager: SettingsManager.inMemory({}),
  additionalExtensionPaths: [footerPath], noContextFiles: true,
});
await loader.reload();
const { extensions, errors, warnings = [], runtime } = loader.getExtensions();
assert.deepEqual(errors, []);
assert.deepEqual(warnings, []);
assert.equal(extensions.length, 1);
assert.equal(extensions[0].resolvedPath, footerPath);
const start = extensions[0].handlers.get("session_start");
const stop = extensions[0].handlers.get("session_shutdown");
assert.equal(start?.length, 1);
assert.equal(stop?.length, 1);
let thinking = "high";
runtime.getThinkingLevel = () => thinking;
let rendered = 0;
const diagnostics = [];
for (const level of ["error", "warn"]) {
  const write = console[level];
  console[level] = (...args) => { diagnostics.push(args); write(...args); };
}

for (const name of ["dark", "light"]) {
  const theme = getThemeByName(name);
  assert(theme instanceof Theme, "use the installed Pi Theme, not a color mock");
  assert.throws(() => theme.fg("info", "↑1"), /Unknown theme color: info/);
  let footer;
  let disposed = 0;
  const ctx = {
    mode: "tui", hasUI: true,
    model: { id: "footer-fixture", contextWindow: 128_000 },
    sessionManager: { getEntries: () => [] },
    getContextUsage: () => ({ tokens: 32_000, contextWindow: 128_000, percent: 25 }),
    ui: {
      setFooter(factory) {
        footer = factory({ requestRender() {} }, theme, {
          getGitBranch: () => "footer-test",
          getExtensionStatuses: () => new Map(),
          onBranchChange: () => () => { disposed++; },
        });
      },
    },
  };
  try {
    await start[0]({ type: "session_start", reason: "startup" }, ctx);
    assert(footer, "actual packaged footer factory must be installed");
    for (thinking of ["off", "minimal", "low", "medium", "high", "xhigh", "max"]) {
      for (const width of [80, 200]) {
        // The original footer catches the color exception, logs it, and returns [].
        // Assert actual nonempty output and the colored indicator on every redraw.
        footer.invalidate();
        const lines = footer.render(width);
        assert(lines.length > 0, `${name}/${thinking}/${width}: footer disappeared`);
        assert(lines.every(line => visibleWidth(line) <= width));
        const output = lines.join("\n");
        assert(output.includes(theme.fg("accent", "↑1")), "ahead indicator must use Pi's accent");
        assert.match(stripVTControlCharacters(output), /footer-test.*↑1/);
        assert.match(stripVTControlCharacters(output), /footer-fixture/);
        rendered++;
      }
    }
  } finally {
    footer?.dispose();
    await stop[0]({ type: "session_shutdown", reason: "quit" }, ctx);
  }
  assert.equal(disposed, 1, "release the branch subscription");
}
runtime.invalidate();
assert.deepEqual(diagnostics, [], "footer must not log errors or warnings");
console.log(`PASS: actual packaged footer, real Git ahead=1, Pi dark/light themes, ${rendered} renders; no prompt`);
