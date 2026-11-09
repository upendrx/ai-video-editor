// Background job queue: spawns scripts / claude / agy (Antigravity), parses their output into feed events,
// keeps history in SQLite. One running job per episode, MAX_PARALLEL overall.
import { DatabaseSync } from 'node:sqlite';
import { spawn } from 'node:child_process';
import { EventEmitter } from 'node:events';
import { homedir } from 'node:os';
import path from 'node:path';
import { ROOT } from './repo.js';

const MAX_PARALLEL = 2;

// Picker key -> CLI flag values.
// agy: --mode plan | accept-edits | auto; "ask" = its default (request-review, no flag); full = skip-permissions flag.
export const AGY = path.join(homedir(), '.gemini/bin/agy');
export const MODES = {
  plan: { label: 'Plan (read only)', claude: 'plan', agy: ['--mode', 'plan'] },
  ask: { label: 'Ask before edits', claude: 'manual', agy: [] },
  edit: { label: 'Edit automatically', claude: 'acceptEdits', agy: ['--mode', 'accept-edits'] },
  auto: { label: 'Auto', claude: 'auto', agy: ['--mode', 'auto'] },
  full: { label: 'Full access', claude: 'bypassPermissions', agy: ['--dangerously-skip-permissions'] },
};

export function aiArgv(engine, prompt, mode, { resume, allow } = {}) {
  const m = MODES[mode] || MODES.edit;
  if (engine === 'claude') {
    return ['claude', '-p', prompt, '--output-format', 'stream-json', '--verbose', '--permission-mode', m.claude,
      ...(resume ? ['--resume', resume] : []), ...(allow?.length ? ['--allowedTools', ...allow] : [])];
  }
  return [AGY, '-p', prompt, '--output-format', 'stream-json', ...m.agy, ...(resume ? ['--conversation', resume] : [])];
}

const short = (s, n = 400) => (s.length > n ? `${s.slice(0, n)}…` : s);

function toolSummary(name, input = {}) {
  const arg = input.command || input.file_path || input.path || input.pattern || input.url || input.description || input.query || '';
  return `${name}${arg ? `  ${short(String(arg), 200)}` : ''}`;
}

export class Jobs extends EventEmitter {
  constructor(file) {
    super();
    this.db = new DatabaseSync(file);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT, engine TEXT, video TEXT, mode TEXT,
        argv TEXT, status TEXT, created INTEGER, started INTEGER, ended INTEGER, exit_code INTEGER,
        session_id TEXT, cost REAL, denials TEXT);
      CREATE TABLE IF NOT EXISTS events (job_id INTEGER, seq INTEGER, ts INTEGER, kind TEXT, text TEXT);
      CREATE INDEX IF NOT EXISTS ev_job ON events(job_id, seq);
      UPDATE jobs SET status = 'interrupted' WHERE status IN ('running', 'queued');`);
    this.procs = new Map();
    this.seq = new Map();
  }

  list(limit = 200) { return this.db.prepare('SELECT * FROM jobs ORDER BY id DESC LIMIT ?').all(limit).map(this.#row); }
  get(id) { const r = this.db.prepare('SELECT * FROM jobs WHERE id = ?').get(id); return r && this.#row(r); }
  events(id) { return this.db.prepare('SELECT seq, ts, kind, text FROM events WHERE job_id = ? ORDER BY seq').all(id); }
  #row = (r) => ({ ...r, argv: JSON.parse(r.argv), denials: r.denials ? JSON.parse(r.denials) : [] });

  enqueue({ title, engine, video = null, mode = null, argv }) {
    const { lastInsertRowid } = this.db
      .prepare('INSERT INTO jobs (title, engine, video, mode, argv, status, created) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .run(title, engine, video, mode, JSON.stringify(argv), 'queued', Date.now());
    const id = Number(lastInsertRowid);
    this.#changed(id);
    this.#pump();
    return this.get(id);
  }

  stop(id) {
    const job = this.get(id);
    if (!job) return;
    if (job.status === 'queued') { this.#set(id, { status: 'stopped', ended: Date.now() }); return; }
    const p = this.procs.get(id);
    if (!p) return;
    p.stopping = true;
    try { process.kill(-p.pid, 'SIGTERM'); } catch {}
    setTimeout(() => { try { process.kill(-p.pid, 'SIGKILL'); } catch {} }, 3000);
  }

  #set(id, fields) {
    const keys = Object.keys(fields);
    this.db.prepare(`UPDATE jobs SET ${keys.map((k) => `${k} = ?`).join(', ')} WHERE id = ?`).run(...keys.map((k) => fields[k]), id);
    this.#changed(id);
  }
  #changed(id) { this.emit('job', this.get(id)); }

  #event(id, kind, text) {
    const seq = (this.seq.get(id) || 0) + 1;
    this.seq.set(id, seq);
    const ev = { seq, ts: Date.now(), kind, text };
    this.db.prepare('INSERT INTO events (job_id, seq, ts, kind, text) VALUES (?, ?, ?, ?, ?)').run(id, seq, ev.ts, kind, text);
    this.emit('event', id, ev);
  }

  #pump() {
    const queued = this.db.prepare("SELECT * FROM jobs WHERE status = 'queued' ORDER BY id").all().map(this.#row);
    for (const job of queued) {
      if (this.procs.size >= MAX_PARALLEL) break;
      const busy = [...this.procs.values()].some((p) => job.video && p.video === job.video);
      if (!busy) this.#start(job);
    }
  }

  #start(job) {
    const { id, argv, engine } = job;
    let proc;
    try {
      proc = spawn(argv[0], argv.slice(1), { cwd: ROOT, detached: true, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, FORCE_COLOR: '0' } });
    } catch (e) {
      this.#event(id, 'err', String(e)); this.#set(id, { status: 'failed', ended: Date.now() }); return;
    }
    proc.video = job.video;
    this.procs.set(id, proc);
    this.#set(id, { status: 'running', started: Date.now() });
    this.#event(id, 'sys', `$ ${argv.map((a) => (/\s/.test(a) ? JSON.stringify(short(a, 160)) : a)).join(' ')}`);

    const parse = engine === 'claude' ? this.#claudeLine : engine === 'agy' ? this.#agyLine : (id, l) => this.#event(id, 'out', l);
    const state = { buf: '' };
    lines(proc.stdout, (l) => parse(id, l, state));
    lines(proc.stderr, (l) => this.#event(id, 'err', l));
    proc.on('error', (e) => this.#event(id, 'err', String(e)));
    proc.on('close', (code) => {
      if (state.buf) { this.#event(id, 'text', state.buf); state.buf = ''; }
      this.procs.delete(id);
      const status = proc.stopping ? 'stopped' : code === 0 ? 'done' : 'failed';
      this.#event(id, 'sys', `exited ${code ?? 'by signal'}`);
      this.#set(id, { status, ended: Date.now(), exit_code: code });
      this.#pump();
    });
  }

  #claudeLine = (id, line) => {
    let m;
    try { m = JSON.parse(line); } catch { return this.#event(id, 'out', line); }
    if (m.type === 'system' && m.subtype === 'init') {
      this.#set(id, { session_id: m.session_id });
      this.#event(id, 'sys', `session ${m.session_id.slice(0, 8)} · ${m.model} · ${m.permissionMode}`);
    } else if (m.type === 'assistant') {
      for (const c of m.message?.content || []) {
        if (c.type === 'text' && c.text.trim()) this.#event(id, 'text', c.text);
        else if (c.type === 'tool_use') this.#event(id, 'tool', toolSummary(c.name, c.input));
      }
    } else if (m.type === 'user') {
      for (const c of m.message?.content || []) {
        if (c.type !== 'tool_result') continue;
        const t = Array.isArray(c.content) ? c.content.map((x) => x.text || '').join('') : String(c.content ?? '');
        this.#event(id, c.is_error ? 'toolerr' : 'toolres', short(t));
      }
    } else if (m.type === 'result') {
      const denials = (m.permission_denials || []).map((d) => d.tool_name);
      this.#set(id, { cost: m.total_cost_usd ?? null, session_id: m.session_id, denials: JSON.stringify([...new Set(denials)]) });
      this.#event(id, m.is_error ? 'err' : 'result',
        `${m.is_error ? 'Error' : 'Done'} · ${((m.duration_ms || 0) / 1000).toFixed(0)} s · ${m.num_turns} turns${m.total_cost_usd ? ` · $${m.total_cost_usd.toFixed(2)}` : ''}`);
    }
  };

  // agy streams step_update events; assistant text arrives as deltas, joined per step.
  #agyLine = (id, line, state) => {
    let m;
    try { m = JSON.parse(line); } catch { return this.#event(id, 'out', line); }
    const flush = () => { if (state.buf.trim()) this.#event(id, 'text', state.buf); state.buf = ''; };
    if (m.event === 'init') return this.#event(id, 'sys', `agy · ${m.init?.permission_mode || ''}`);
    const u = m.step_update;
    if (u) {
      if (u.conversation_id && !state.conv) { state.conv = u.conversation_id; this.#set(id, { session_id: u.conversation_id }); }
      if (u.step_type === 'agent_response') { if (u.text_delta) state.buf += u.text_delta; if (u.state === 'DONE') flush(); }
      else if (u.step_type === 'tool') {
        flush();
        const p = u.tool_info?.parameters || {};
        if (u.state === 'ACTIVE') this.#event(id, 'tool', toolSummary(u.tool_name, { command: p.CommandLine, file_path: p.Path || p.AbsolutePath || p.TargetFile, pattern: p.Query || p.Pattern, url: p.Url }));
        else if (u.tool_info?.output) this.#event(id, 'toolres', short(String(u.tool_info.output)));
      }
    } else if (m.event === 'result') {
      flush();
      const r = m.result || {};
      const ok = r.status === 'SUCCESS';
      this.#event(id, ok ? 'result' : 'err', `${ok ? 'Done' : `Error (${r.status})`} · ${Math.round(r.duration_seconds || 0)} s${r.usage?.total_tokens ? ` · ${r.usage.total_tokens} tokens` : ''}`);
    }
  };
}

function lines(stream, cb) {
  let rest = '';
  stream.setEncoding('utf8');
  stream.on('data', (chunk) => {
    // ffmpeg and progress bars use \r; treat it as a line break
    const parts = (rest + chunk).split(/\r?\n|\r/);
    rest = parts.pop();
    for (const p of parts) if (p.trim()) cb(p);
  });
  stream.on('end', () => { if (rest.trim()) cb(rest); });
}
