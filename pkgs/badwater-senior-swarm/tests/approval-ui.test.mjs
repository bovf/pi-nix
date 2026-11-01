import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {getKeybindings, visibleWidth, Text, TuiMainScreen, TuiAltScreen, stripTerminalSequences} from '@earendil-works/pi-tui';
import {APPROVE, createApprovalReader, reviewDocument, confirmationText, reviewApproval} from '../approval-ui.mjs';

const fixture = () => ({
  id: 'synthetic-review', repo: '/fixture/repo', goal: 'A bounded synthetic outcome',
  snapshot: {head: 'a'.repeat(40), digest: 'b'.repeat(64), branch: 'refs/heads/main', clean: true}, planHash: 'c'.repeat(64),
  plan: {summary: ('Long evidence paragraph with 漢字 🦄 e\u0301.\n').repeat(2000), acceptance: ['Overall-acceptance-sentinel'], assumptions: ['Assumption-sentinel'], rollout: 'Rollout-sentinel',
    tasks: [{id: 'fix', title: 'Fix the fixture', paths: ['src/example.mjs'], dependencies: ['dependency-sentinel'], criteria: ['Task-acceptance-sentinel'], verify: [{argv: ['node', '--test', 'example.test.mjs'], timeoutSeconds: 37}]}]},
});
function reader(run = fixture(), columns = 80, rows = 24) {
  const result = [], terminal = {columns, rows}, renders = [];
  const component = createApprovalReader(run, '/fixture/TAIL-SENTINEL.json', {terminal, requestRender: () => renders.push(true)}, {fg: (_color, value) => value}, getKeybindings(), value => result.push(value));
  const render = () => {
    const lines = component.render(terminal.columns);
    assert(lines.length <= Math.max(0, terminal.rows - 4));
    for (const line of lines) assert(visibleWidth(line) <= terminal.columns, 'terminal width overflow');
    return lines;
  };
  render(); return {component, result, terminal, render, renders};
}
const startLine = lines => Number(lines.find(line => line.startsWith('Lines ')).match(/^Lines (\d+)/)[1]);

test('review contains every effective plan field and exact check, with a bounded confirmation', () => {
  const run = fixture(), text = reviewDocument(run, '/fixture/review.json');
  for (const sentinel of ['Overall-acceptance-sentinel', 'Assumption-sentinel', 'Rollout-sentinel', 'Task-acceptance-sentinel', 'dependency-sentinel', 'src/example.mjs', '["node","--test","example.test.mjs"]', '37s', run.snapshot.digest, run.planHash, 'No push']) assert(text.includes(sentinel), sentinel);
  assert(text.includes('Role: developer')); run.plan.tasks[0].role = 'librarian'; assert(reviewDocument(run, '/fixture/review.json').includes('Role: librarian'));
  assert(text.includes(run.plan.summary)); assert(confirmationText(run).length < 700); assert(!confirmationText(run).includes(run.plan.summary));
});

test('long plans scroll by line/page/home/end without moving or hiding controls', () => {
  const f = reader(), initial = f.render(); assert.equal(startLine(initial), 1); assert.match(initial.at(-1), /Enter: Continue/);
  f.component.handleInput('\x1b[B'); assert.equal(startLine(f.render()), 2);
  f.component.handleInput('\x1b[6~'); assert(startLine(f.render()) > 2);
  f.component.handleInput('\x1b[5~'); assert.equal(startLine(f.render()), 2);
  f.component.handleInput('\x1b[F'); assert(f.render().join('\n').includes('TAIL-SENTINEL.json'));
  assert.equal(f.render().at(-1), initial.at(-1));
  f.component.handleInput('\x1b[H'); assert.equal(startLine(f.render()), 1);
  assert.deepEqual(f.result, []);
});

test('resize, Unicode wrapping and tiny terminals stay bounded and fail closed', () => {
  const f = reader(); f.component.handleInput('\x1b[F');
  for (const [columns, rows] of [[120, 45], [40, 12], [80, 24]]) { f.terminal.columns = columns; f.terminal.rows = rows; assert.match(f.render().at(-1), /Cancel/); }
  f.terminal.columns = 20; f.terminal.rows = 6; assert.match(f.render()[0], /Resize/);
  for (const key of ['\r', '\t', '\r']) f.component.handleInput(key);
  assert.deepEqual(f.result, []); f.component.handleInput('\x1b'); assert.deepEqual(f.result, [false]);
});

test('continue is not approval, final selection defaults to Cancel, and Back preserves the review', () => {
  const f = reader(); f.component.handleInput('\x1b[6~'); const position = startLine(f.render());
  f.component.handleInput('\r'); assert.deepEqual(f.result, []); assert.match(f.render()[0], /Confirm exact plan/); assert.match(f.render().at(-1), /^\[Cancel\]/);
  f.component.handleInput('b'); assert.equal(startLine(f.render()), position);
  f.component.handleInput('\r'); f.render(); f.component.handleInput('\r'); assert.deepEqual(f.result, [false]);
  const accepted = reader(); accepted.component.handleInput('\r'); accepted.render(); accepted.component.handleInput('\t'); accepted.render(); accepted.component.handleInput('\r'); assert.deepEqual(accepted.result, [true]);
});

test('Escape, Ctrl-C and q cancel from both stages; wheel scroll never approves', () => {
  for (const key of ['\x1b', '\x03', 'q']) for (const confirming of [false, true]) {
    const f = reader(); if (confirming) { f.component.handleInput('\r'); f.render(); }
    f.component.handleInput(key); assert.deepEqual(f.result, [false]);
  }
  const f = reader(); assert.equal(f.component.handleMouse({type: 'wheel', wheelDelta: 4}).handled, true); assert.equal(startLine(f.render()), 5);
  assert.equal(f.component.handleMouse({type: 'click'}), undefined); assert.deepEqual(f.result, []);
});

test('real regular/fullscreen renderers keep overlay controls visible through scroll and resize', () => {
  for (const Screen of [TuiMainScreen, TuiAltScreen]) {
    let input, decision;
    const terminal = {columns: 80, rows: 24, kittyProtocolActive: false,
      start(handler) { input = handler; }, stop() {}, write() {}, moveBy() {}, hideCursor() {}, showCursor() {}, clearLine() {}, clearFromCursor() {}, clearScreen() {}, setTitle() {}, setProgress() {}, setProgramStatus() {}, async drainInput() {}};
    const tui = new Screen(terminal);
    const component = createApprovalReader(fixture(), '/fixture/TAIL-SENTINEL.json', tui, {fg: (_color, value) => value}, getKeybindings(), value => { decision = value; });
    tui.addChild(new Text('Synthetic previous transcript', 0, 0));
    try {
      tui.start(); tui.showOverlay(component, {width: 110, margin: 1});
      const frame = () => { tui.renderNow(true); const lines = Screen === TuiAltScreen ? tui.getScreenLines() : tui.captureRenderState().previousLines; return lines.map(stripTerminalSequences).join('\n'); };
      assert(frame().includes('Enter: Continue'));
      input('\u001b[6~'); assert(frame().includes('Enter: Continue'));
      input('\r'); assert(frame().includes('[Cancel]'));
      for (const rows of [41, 42, 43, 44, 24]) { terminal.rows = rows; assert(frame().includes('[Cancel]'), `footer clipped at ${rows} rows`); }
      terminal.columns = 40; terminal.rows = 12; assert(frame().includes('[Cancel]'));
      input('\u001b'); assert.equal(decision, false);
    } finally { tui.stop(); }
  }
});

test('untrusted plan text cannot inject ANSI, OSC, control characters or bidi labels', () => {
  const run = fixture(); run.plan.summary = '\x1b[2J\x1b]52;c;fake\x07\u202e hidden\r\nRead me';
  const text = reviewDocument(run, '/fixture/review.json'); assert(!/[\x00-\x09\x0b-\x1f\x7f-\x9f\u202a-\u202e]/.test(text)); assert(text.includes('\\u001b')); assert(text.includes('\\u202e'));
  const f = reader(run); assert(!f.render().join('\n').includes('\x1b'));
});

test('RPC offers Cancel first and a compact decision plus complete private review artifact', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'badwater-senior-swarm-ui-')); t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  const run = fixture(), notices = [], selections = [];
  const ctx = {hasUI: true, mode: 'rpc', ui: {notify: value => notices.push(value), custom() { throw new Error('RPC must not use custom TUI'); }, async select(title, options) { selections.push({title, options}); return 'Cancel'; }}};
  assert.equal(await reviewApproval(run, directory, ctx), false);
  const artifact = path.join(directory, `approval-review-${run.planHash}.json`), record = JSON.parse(fs.readFileSync(artifact, 'utf8'));
  assert.deepEqual(record.plan, run.plan); assert.equal(record.planHash, run.planHash); assert.deepEqual(record.source, run.snapshot); assert.equal(fs.statSync(artifact).mode & 0o777, 0o600);
  assert(notices[0].includes(artifact)); assert.deepEqual(selections[0].options, ['Cancel', APPROVE]); assert(selections[0].title.length < 800);
  ctx.ui.select = async () => APPROVE; assert.equal(await reviewApproval(run, directory, ctx), true);
  ctx.ui.select = async () => undefined; assert.equal(await reviewApproval(run, directory, ctx), false);
  await assert.rejects(() => reviewApproval(run, directory, {...ctx, hasUI: false}), /interactive/);
  await assert.rejects(() => reviewApproval(run, directory, {...ctx, mode: 'print'}), /interactive/);
});

test('TUI uses one bounded two-stage overlay and does not fall back after cancellation', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'badwater-senior-swarm-reader-')); t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  let decision;
  const ctx = {hasUI: true, mode: 'tui', ui: {async custom(factory, options) {
    assert.equal(options.overlay, true); assert.equal(options.overlayOptions.width, 110);
    const component = factory({terminal: {columns: 80, rows: 24}, requestRender() {}}, {fg: (_color, value) => value}, getKeybindings(), value => { decision = value; });
    component.render(80); component.handleInput('\x1b'); return decision;
  }, select() { throw new Error('cancel must not launch RPC fallback'); }}};
  assert.equal(await reviewApproval(fixture(), directory, ctx), false);
});
