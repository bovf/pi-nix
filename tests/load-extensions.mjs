// Run in an empty HOME/cwd and a network namespace:
// unshare -Urn node tests/load-extensions.mjs <pi store path> <package store paths...>
// Factory/resource loading only: no sessions, model calls, or external services.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const [core, ...packages] = process.argv.slice(2);
assert(core && packages.length, "provide Pi and package store paths");
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(`${core}/lib/node_modules/pi-monorepo/dist/index.js`)
);
const loader = new DefaultResourceLoader({
  cwd: process.cwd(),
  agentDir: `${process.env.HOME}/.pi/agent`,
  settingsManager: SettingsManager.inMemory({ packages }),
  noContextFiles: true,
});
await loader.reload();
const { extensions, errors } = loader.getExtensions();
console.log(JSON.stringify({
  packages,
  extensions: extensions.map((extension) => ({
    path: extension.path,
    tools: [...extension.tools.keys()],
    commands: [...extension.commands.keys()],
  })),
  errors,
  skills: loader.getSkills().skills.map((skill) => skill.name),
  skillDiagnostics: loader.getSkills().diagnostics,
}, null, 2));
assert.deepEqual(errors, []);
assert(extensions.length || loader.getSkills().skills.length, "no resources loaded");
process.exit(0);
