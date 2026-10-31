import test from 'node:test';
import assert from 'node:assert/strict';
import { authorizedOrigins, requestAllowed, parseArguments } from '../browser.mjs';

test('browser defaults authorize only exact numeric loopback target origin', () => {
  const origins = authorizedOrigins('http://127.0.0.1:8123/path');
  assert.deepEqual(origins, ['http://127.0.0.1:8123']);
  assert.equal(requestAllowed('http://127.0.0.1:8123/image', origins), true);
  for (const url of ['http://127.0.0.1:8124', 'http://localhost:8123', 'https://example.com',
    'file:///etc/passwd', 'data:text/html,hi', 'ws://127.0.0.1:8123', 'http://user@127.0.0.1:8123'])
    assert.equal(requestAllowed(url, origins), false, url);
  assert.deepEqual(authorizedOrigins('http://[::1]:8000'), ['http://[::1]:8000']);
});

test('browser requires exact explicit extra-origin authorization', () => {
  for (const url of ['http://localhost:8123', 'https://example.com', 'http://192.168.1.1'])
    assert.throws(() => authorizedOrigins(url), /explicit/);
  assert.deepEqual(authorizedOrigins('https://example.com/a', ['https://example.com']), ['https://example.com']);
  for (const origin of ['https://example.com/path', 'https://example.com/?token=x',
    'https://example.com/#x', 'file:///tmp/test', 'https://user:pass@example.com'])
    assert.throws(() => authorizedOrigins('http://127.0.0.1', [origin]));
});

test('browser arguments reject host-profile, CDP, relative output and ambiguous options', () => {
  const base = ['--url', 'http://127.0.0.1:8000', '--output', '/tmp/new-evidence'];
  assert.deepEqual(parseArguments(base).origins, ['http://127.0.0.1:8000']);
  for (const extra of [['--cdp', 'http://127.0.0.1:9222'], ['--profile', '/home/user'],
    ['--url', 'http://127.0.0.1:9000'], ['--unknown']])
    assert.throws(() => parseArguments([...base, ...extra]));
  assert.throws(() => parseArguments(['--url', 'file:///tmp/a', '--output', '/tmp/out']));
  assert.throws(() => parseArguments(['--url', 'http://127.0.0.1', '--output', 'relative']));
});
