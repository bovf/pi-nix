import path from 'node:path';
import {ScrollView, Text, matchesKey, Key, truncateToWidth} from '@earendil-works/pi-tui';
import {ensure, writeJson} from './lib.mjs';

export const APPROVE = 'Approve exact plan';
export const AUTHORITY = 'Authorize isolated developer worktrees, approved checks, serial integration and local checkpoint commits only. Your source branch is not edited. No push, main merge, activation, deployment, credentials or production access. Checks execute repository code; worktrees/tool filters are not an OS sandbox.';
// Keep repository/model text from injecting terminal controls or bidirectional labels.
export const displayText = value => String(value).replace(/\r\n/g, '\n').replace(/[\x00-\x09\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
const bullets = values => Array.isArray(values) ? values.map(value => '- ' + value).join('\n') || '(none)' : JSON.stringify(values, null, 2);

export function reviewDocument(run, artifact) {
  const plan = run.plan;
  return displayText([
    'BADWATER SENIOR SWARM — FULL APPROVAL REVIEW',
    `Run: ${run.id}\nRepository: ${run.repo}\nSource: ${run.snapshot.head}\nBranch: ${run.snapshot.branch}\nSource digest: ${run.snapshot.digest}\nPlan SHA-256: ${run.planHash}`,
    'Goal\n' + run.goal,
    'Summary\n' + plan.summary,
    'Overall acceptance\n' + bullets(plan.acceptance),
    'Assumptions\n' + bullets(plan.assumptions),
    ...plan.tasks.map(task => [
      `TASK ${task.id}: ${task.title}`,
      'Role: ' + (task.role || 'developer'),
      'Dependencies: ' + (task.dependencies.join(', ') || '(none)'),
      'Owned paths\n' + bullets(task.paths),
      'Acceptance\n' + bullets(task.criteria),
      'Exact verification commands (execute repository code)\n' + task.verify.map(check => `${JSON.stringify(check.argv)} — timeout ${check.timeoutSeconds}s`).join('\n'),
    ].join('\n\n')),
    'Rollout\n' + plan.rollout,
    'Authorization boundary\n' + AUTHORITY,
    'Complete machine-readable review artifact\n' + artifact,
  ].join('\n\n'));
}

export function confirmationText(run) {
  return `Run: ${run.id}\nSource: ${run.snapshot.head}\nPlan SHA-256: ${run.planHash}\nTasks: ${run.plan.tasks.length}; checks: ${run.plan.tasks.reduce((n, task) => n + task.verify.length, 0)}\n\nApprove only the exact review you read. Local worktrees/checks/commits only.\nNo push, main merge, activation, deployment, credentials or production.\nChecks execute repository code; worktrees are not an OS sandbox.`;
}

export function createApprovalReader(run, artifact, tui, theme, keybindings, done) {
  const review = new ScrollView(new Text(reviewDocument(run, artifact), 0, 0), {scrollbar: 'hidden', overscroll: 'contain'});
  const confirmation = new ScrollView(new Text(confirmationText(run), 0, 0), {scrollbar: 'hidden', overscroll: 'contain'});
  let confirming = false, selected = 0, width = 0;
  const active = () => confirming ? confirmation : review;
  const fits = () => width >= 38 && tui.terminal.columns >= 38 && tui.terminal.rows >= 12;
  const redraw = () => tui.requestRender();
  return {
    render(columns) {
      width = columns;
      const height = Math.max(0, Math.min(40, tui.terminal.rows - 4));
      const clip = line => truncateToWidth(line, columns);
      if (!fits()) return ['Resize to at least 38 columns × 12 rows.', 'Esc/q: Cancel; nothing will be approved.'].map(clip).slice(0, height);
      const view = active(), lines = view.render(columns), bodyHeight = height - 7;
      view.updateLayout(lines.length, bodyHeight, redraw);
      const body = lines.slice(view.scrollTop, view.scrollTop + bodyHeight);
      while (body.length < bodyHeight) body.push('');
      const choices = ['Cancel', APPROVE].map((label, i) => theme.fg(i === selected ? 'accent' : 'dim', i === selected ? `[${label}]` : label)).join('   ');
      return [
        theme.fg('accent', confirming ? 'Confirm exact plan — no changes applied yet' : 'Badwater Senior Swarm — read before approving'),
        `Run: ${run.id} | ${run.plan.tasks.length} tasks`,
        `Source: ${run.snapshot.head}`,
        `Plan: ${run.planHash}`,
        ...body,
        `Lines ${view.scrollTop + 1}–${Math.min(lines.length, view.scrollTop + bodyHeight)} / ${lines.length}`,
        confirming ? 'Tab/←→ choose · b back · Esc cancel' : '↑↓ scroll · PgUp/PgDn page · Home/End',
        confirming ? choices : 'Enter: Continue | Esc/q: Cancel',
      ].map(clip);
    },
    handleInput(data) {
      if (keybindings.matches(data, 'tui.select.cancel') || matchesKey(data, Key.ctrl('c')) || matchesKey(data, 'q')) { done(false); return; }
      if (!fits()) return;
      const view = active();
      if (confirming && matchesKey(data, 'b')) { confirming = false; selected = 0; }
      else if (confirming && [Key.tab, Key.left, Key.right].some(key => matchesKey(data, key))) selected = 1 - selected;
      else if (keybindings.matches(data, 'tui.select.confirm')) {
        if (confirming) { done(selected === 1); return; }
        confirming = true; selected = 0;
      } else if (keybindings.matches(data, 'tui.select.up')) view.scrollBy(-1);
      else if (keybindings.matches(data, 'tui.select.down')) view.scrollBy(1);
      else if (keybindings.matches(data, 'tui.select.pageUp')) view.scrollBy(-Math.max(1, view.viewportHeight - 1));
      else if (keybindings.matches(data, 'tui.select.pageDown')) view.scrollBy(Math.max(1, view.viewportHeight - 1));
      else if (matchesKey(data, Key.home)) view.scrollToStart();
      else if (matchesKey(data, Key.end)) view.scrollToEnd();
      else return;
      redraw();
    },
    handleMouse(event) {
      if (!fits() || event.type !== 'wheel') return;
      active().scrollBy(event.wheelDelta || 0);
      return {handled: true, requestRender: true};
    },
    invalidate() { review.invalidate(); confirmation.invalidate(); },
  };
}

export async function reviewApproval(run, directory, ctx) {
  ensure(ctx.hasUI && ['tui', 'rpc'].includes(ctx.mode), 'Approval requires an interactive TUI or RPC human interface');
  const artifact = path.join(directory, `approval-review-${run.planHash}.json`);
  writeJson(artifact, {version: 1, id: run.id, goal: run.goal, repo: run.repo, source: run.snapshot, planHash: run.planHash, plan: run.plan, authority: AUTHORITY});
  if (ctx.mode === 'tui') {
    return await ctx.ui.custom((tui, theme, keybindings, done) => createApprovalReader(run, artifact, tui, theme, keybindings, done), {overlay: true, overlayOptions: {width: 110, margin: 1}}) === true;
  }
  ctx.ui.notify(`Read the complete approval review before selecting Approve: ${displayText(artifact)}`, 'info');
  return await ctx.ui.select('Approve this exact swarm plan?\n' + confirmationText(run), ['Cancel', APPROVE]) === APPROVE;
}
