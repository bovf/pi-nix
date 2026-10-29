// Installed Pi metadata/SDK/native-child acceptance only: never prompt or call a provider.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const [core, subagents, limitsPath, child] = process.argv.slice(2);
assert(core && subagents && limitsPath);
assert.equal(process.env.PI_OFFLINE, "1", "run only in an isolated, offline fixture");
const root = `${core}/lib/pi/node_modules/@earendil-works/pi-coding-agent`;
const pi = await import(pathToFileURL(`${root}/dist/index.js`));
const { AuthStorage } = await import(pathToFileURL(`${root}/dist/core/auth-storage.js`));
const limits = JSON.parse(await readFile(limitsPath, "utf8"));
const providers = ["openai", "openai-codex"];
// Pi1.4's pinned catalog removed these retired IDs only from the subscription route.
// Keep their reviewed limits for the API route; overrides must not resurrect them.
const retiredSubscriptionIds = ["gpt-5.3-codex-spark", "gpt-5.5"];
const activeSubscriptionIds = [
  "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra",
  "gpt-6-astra", "gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol",
];
const expectedReviewedModels = {
  openai: [...retiredSubscriptionIds, ...activeSubscriptionIds],
  "openai-codex": activeSubscriptionIds,
};
const expectedCounts = { openai: 9, "openai-codex": 7 };
const expectedChildren = 16;
assert.deepEqual(Object.keys(limits).sort(), [...retiredSubscriptionIds, ...activeSubscriptionIds].sort());
const agentDir = join(process.env.HOME, ".pi/agent");
let networkCalls = 0;
globalThis.fetch = () => { networkCalls++; throw new Error("provider/network calls forbidden"); };
const checkModel = (model) => {
  assert.equal(model.contextWindow, limits[model.id], `${model.provider}/${model.id}`);
};

if (child) {
  const { createDefaultChildSessionFactory } = await import(pathToFileURL(`${subagents}/src/runs/shared/child-session.js`));
  const factory = createDefaultChildSessionFactory();
  const errors = [];
  let started = 0;
  let stopped = 0;
  try {
    for (const provider of providers) for (const id of expectedReviewedModels[provider]) {
      const session = await factory.create({
        cwd: process.cwd(), storage: { kind: "memory" }, model: `${provider}/${id}`,
        ambientExtensions: false, extensionPaths: [], noSkills: true, noContextFiles: true,
        tools: [], runtime: {},
        hooks: [{ name: "context-check", factory(api) {
          api.on("session_start", (_event, ctx) => {
            assert.equal(ctx.model.provider, provider);
            assert.equal(ctx.model.id, id);
            checkModel(ctx.model);
            started++;
          });
          api.on("session_shutdown", () => { stopped++; });
        } }],
        onExtensionError: (error) => errors.push(error),
      });
      assert(session.sessionId);
      await session.dispose();
    }
  } finally {
    await factory.dispose();
  }
  assert.equal(started, expectedChildren);
  assert.equal(stopped, started);
  assert.deepEqual(errors, []);
  assert.equal(networkCalls, 0);
  console.log(`PASS ${started} installed native children inherit context metadata; zero prompts/network calls`);
} else {
  await mkdir(agentDir, { recursive: true });
  const modelsPath = join(agentDir, "models.json");
  const settingsPath = join(agentDir, "settings.json");
  const baseline = await pi.ModelRuntime.create({ modelsPath: null, credentials: AuthStorage.inMemory() });
  const catalogIds = baseline.getModels("openai-codex").map(m => m.id).sort();
  assert.deepEqual(catalogIds, activeSubscriptionIds, "review the exact active subscription inventory on catalog changes");
  for (const provider of providers) {
    const reviewedIds = baseline.getModels(provider).filter(m => m.id in limits).map(m => m.id).sort();
    assert.deepEqual(reviewedIds, [...expectedReviewedModels[provider]].sort(), provider);
    assert.equal(reviewedIds.length, expectedCounts[provider], provider);
    assert(baseline.getModel(provider, "gpt-6.1-sol"), `${provider}: selected default must remain available`);
  }
  for (const id of retiredSubscriptionIds) assert.equal(baseline.getModel("openai-codex", id), undefined);
  assert.equal(limits["gpt-5.3-codex-spark"], 128000, "retired Spark must not be inflated");
  for (const [id, limit] of Object.entries(limits)) {
    assert(Number.isSafeInteger(limit) && limit > 0, id);
    if (id !== "gpt-5.3-codex-spark") assert.equal(limit, 1050000);
  }
  const modelOverrides = Object.fromEntries(Object.entries(limits).map(([id, contextWindow]) => [id, { contextWindow }]));
  const declaration = { providers: Object.fromEntries(providers.map(p => [p, { modelOverrides }])) };
  await writeFile(modelsPath, JSON.stringify(declaration));
  const compactionOverrides = Object.fromEntries(providers.flatMap(p => Object.entries(limits).filter(([, n]) => n > 272000).map(([id]) => [`${p}/${id}`, { reserveTokens: 150000 }])));
  await writeFile(settingsPath, JSON.stringify({ theme: "dark", compaction: { enabled: true, reserveTokens: 32000, keepRecentTokens: 60000, modelOverrides: compactionOverrides } }));
  const runtime = await pi.ModelRuntime.create({ modelsPath, credentials: AuthStorage.inMemory() });
  const identities = models => models.map(m => `${m.type ?? "chat"}/${m.provider}/${m.id}`).sort();
  assert.deepEqual(identities(runtime.getAllModels()), identities(baseline.getAllModels()), "overrides must not add or remove models");
  for (const id of retiredSubscriptionIds) assert.equal(runtime.getModel("openai-codex", id), undefined, "overrides must not revive retired subscription models");
  for (const old of baseline.getAllModels()) {
    const current = runtime.getModelOfType(old.type ?? "chat", old.provider, old.id);
    const expected = (old.type ?? "chat") === "chat" && providers.includes(old.provider) && old.id in limits ? { ...old, contextWindow: limits[old.id] } : old;
    assert.deepEqual(JSON.parse(JSON.stringify(current)), JSON.parse(JSON.stringify(expected)), `only reviewed chat context may change: ${old.provider}/${old.id}`);
  }
  await runtime.refresh({ allowNetwork: false });
  const settings = pi.SettingsManager.create(process.cwd(), agentDir, { projectTrusted: false });
  for (const provider of providers) for (const id of expectedReviewedModels[provider]) {
    const limit = limits[id];
    const model = runtime.getModel(provider, id);
    checkModel(model);
    const resolved = settings.getCompactionSettings(model);
    assert.equal(resolved.enabled, true);
    assert.equal(resolved.keepRecentTokens, 60000);
    assert.equal(resolved.reserveTokens, limit > 272000 ? 150000 : 32000);
    assert.equal(limit - resolved.reserveTokens, limit > 272000 ? 900000 : 96000);
  }
  const model = runtime.getModel("openai", "gpt-6.1-sol");
  const loader = new pi.DefaultResourceLoader({ cwd: process.cwd(), agentDir, settingsManager: settings, noExtensions: true, noSkills: true, noContextFiles: true, noPromptTemplates: true, noThemes: true });
  await loader.reload();
  const { session } = await pi.createAgentSession({ model, modelRuntime: runtime, settingsManager: settings, resourceLoader: loader, sessionManager: pi.SessionManager.inMemory(), noTools: true });
  checkModel(session.model);
  assert.equal(session.model.provider, "openai");
  assert.equal(session.model.id, "gpt-6.1-sol");
  assert.equal(session.messages.length, 0);
  session.dispose();
  const { resolveHostPeerAliases } = await import(pathToFileURL(`${subagents}/src/runs/background/runner-aliases.js`));
  const aliases = resolveHostPeerAliases(root);
  assert.deepEqual(aliases.missing, []);
  const result = spawnSync(process.execPath, ["--import", pathToFileURL(`${subagents}/runner-peer-preload.mjs`).href, fileURLToPath(import.meta.url), core, subagents, limitsPath, "child"], {
    env: { ...process.env, PI_CODING_AGENT_DIR: agentDir, PI_PACKAGE_DIR: root, PI_SUBAGENTS_PI_CODING_AGENT_PACKAGE_ROOT: root, PI_ASYNC_NATIVE_RUNNER: "1", JITI_ALIAS: JSON.stringify(aliases.aliases) },
    encoding: "utf8", timeout: 60000,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.equal(result.stderr, "");
  process.stdout.write(result.stdout);
  assert.equal(networkCalls, 0);
  console.log(`PASS exact ${catalogIds.length} active subscription IDs; 9 API + 7 subscription reviewed pairs, 2 absent subscription IDs not revived; per-model compaction, native SDK and unchanged unrelated metadata; no live entitlement claim`);
}
