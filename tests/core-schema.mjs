// Installed Pi1.5 schema gate: no model runtime, user config or network.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const [core, version] = process.argv.slice(2);
assert(core && version);
const root = `${core}/lib/pi/node_modules/@earendil-works/pi-schema`;
assert.equal(JSON.parse(fs.readFileSync(`${root}/package.json`, 'utf8')).version, version);
const schema = await import(pathToFileURL(`${root}/dist/index.js`));
const definition = {type: 'object', properties: {path: {type: 'string'}, limit: {type: 'integer', minimum: 1}}, required: ['path', 'limit'], additionalProperties: false};
const strict = schema.compile(definition);
assert(strict.check({path: 'fixture', limit: 2}));
assert(!strict.check({path: 'fixture', limit: '2'}));
assert(strict.errors({limit: 0}).some(error => error.path === '/path' && error.keyword === 'required'));
const input = {path: 'fixture', limit: '2'};
const parsed = schema.compile(definition, {coerce: true}).parse(input);
assert.equal(parsed.ok, true); assert.deepEqual(parsed.value, {path: 'fixture', limit: 2});
assert.equal(input.limit, '2', 'argument coercion must not mutate the caller');
console.log(`PASS installed same-release pi-schema ${version}: native import, validation, errors, coercion and caller preservation`);
