// Studio server: local only (127.0.0.1), token cookie, REST + WebSocket.
import Fastify from 'fastify';
import fstatic from '@fastify/static';
import fws from '@fastify/websocket';
import { randomBytes } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync, mkdirSync, watch } from 'node:fs';
import { execFile } from 'node:child_process';
import { homedir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ROOT, readBoard, listTree, readText, safePath } from './repo.js';
import { Jobs, MODES, AGY, aiArgv } from './jobs.js';
import { ACTIONS, publicActions } from './actions.js';

const PORT = Number(process.env.STUDIO_PORT || 4545);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(HERE, '../data');
const DIST = path.join(HERE, '../dist');
mkdirSync(DATA, { recursive: true });

const tokenFile = path.join(DATA, 'token');
if (!existsSync(tokenFile)) writeFileSync(tokenFile, randomBytes(18).toString('hex'), { mode: 0o600 });
const TOKEN = readFileSync(tokenFile, 'utf8').trim();

const jobs = new Jobs(path.join(DATA, 'studio.sqlite'));
const app = Fastify({ logger: false });
await app.register(fws);
await app.register(fstatic, { root: ROOT, prefix: '/files/', decorateReply: false, dotfiles: 'deny', acceptRanges: true });
mkdirSync(path.join(DIST, 'assets'), { recursive: true });
await app.register(fstatic, { root: path.join(DIST, 'assets'), prefix: '/assets/', decorateReply: false, index: false });

const authed = (req) => (req.headers.cookie || '').split(/;\s*/).includes(`studio=${TOKEN}`);
app.addHook('onRequest', async (req, reply) => {
  const host = (req.headers.host || '').split(':')[0];
  if (host !== '127.0.0.1' && host !== 'localhost') return reply.code(403).send('local only');
  if (req.method !== 'GET' && req.headers.origin && !/^http:\/\/(127\.0\.0\.1|localhost):/.test(req.headers.origin)) return reply.code(403).send('bad origin');
  const url = req.url.split('?')[0];
  if (url === '/' || url.startsWith('/assets/')) return;
  if (!authed(req)) return reply.code(401).send({ error: 'open the link printed in the terminal' });
});

app.get('/', (req, reply) => {
  if (req.query.t === TOKEN) {
    return reply.header('set-cookie', `studio=${TOKEN}; HttpOnly; SameSite=Strict; Path=/; Max-Age=31536000`).redirect('/');
  }
  if (!authed(req)) return reply.code(401).type('text/html').send('<body style="background:#141416;color:#ccc;font:14px system-ui;padding:40px">Open the Studio link printed in the terminal (it contains the access token).</body>');
  if (!existsSync(path.join(DIST, 'index.html'))) return reply.type('text/html').send('Run <code>npm run build</code> first.');
  return reply.type('text/html').send(readFileSync(path.join(DIST, 'index.html')));
});

// ---------- repo
app.get('/api/board', () => readBoard());
app.get('/api/tree', (req) => listTree(req.query.path || 'videos', Number(req.query.depth || 4)));
app.get('/api/text', (req, reply) => {
  try {
    const t = readText(req.query.path);
    return t === null ? reply.code(413).send({ error: 'file too large' }) : { text: t };
  } catch (e) { return reply.code(404).send({ error: String(e.message) }); }
});

// ---------- engines
const version = (cmd) => new Promise((res) => execFile(cmd, ['--version'], { timeout: 15000 }, (e, out) => res(e ? null : out.trim().split('\n')[0])));
const agyVersion = () => { try { return JSON.parse(readFileSync(path.join(homedir(), '.gemini/bin/agy.version.json'), 'utf8')).version; } catch { return null; } };
app.get('/api/health', async () => {
  const claude = await version('claude');
  return { claude: { version: claude }, agy: { version: existsSync(AGY) ? agyVersion() || 'installed' : null }, modes: MODES };
});
app.get('/api/actions', () => publicActions());

// ---------- jobs
app.get('/api/jobs', () => jobs.list());
app.get('/api/jobs/:id', (req, reply) => {
  const job = jobs.get(Number(req.params.id));
  return job ? { job, events: jobs.events(job.id) } : reply.code(404).send({ error: 'no job' });
});
app.post('/api/jobs/:id/stop', (req) => { jobs.stop(Number(req.params.id)); return { ok: true }; });

const context = (video) => (video ? `We are working on video videos/${video} (see its STATUS.md and its row in planning/BOARD.md).\n\n` : '');

app.post('/api/actions/:id/run', (req, reply) => {
  const a = ACTIONS.find((x) => x.id === req.params.id);
  const { video, mode = 'edit', file } = req.body || {};
  if (!a || !video) return reply.code(400).send({ error: 'unknown action or no video' });
  safePath(`videos/${video}`);
  if (a.needs && !file) return reply.code(400).send({ error: `select a ${a.needs} file first` });
  if (file) safePath(file);
  const argv = a.engine === 'script' ? a.argv(video, file) : aiArgv(a.engine, a.prompt(video), mode);
  return jobs.enqueue({ title: a.label, engine: a.engine, video, mode: a.engine === 'script' ? null : mode, argv });
});

app.post('/api/run', (req, reply) => {
  const { engine, text, video, mode = 'edit', resume, allow } = req.body || {};
  if (!text?.trim() || !['claude', 'agy', 'shell'].includes(engine)) return reply.code(400).send({ error: 'engine and text required' });
  if (video) safePath(`videos/${video}`);
  const argv = engine === 'shell' ? ['zsh', '-lc', text] : aiArgv(engine, resume ? text : context(video) + text, mode, { resume, allow });
  return jobs.enqueue({ title: text.trim().split('\n')[0].slice(0, 80), engine: engine === 'shell' ? 'script' : engine, video, mode: engine === 'shell' ? null : mode, argv });
});

// ---------- live updates
const clients = new Set();
const send = (msg) => { const s = JSON.stringify(msg); for (const c of clients) if (c.readyState === 1) c.send(s); };
app.get('/ws', { websocket: true }, (socket) => { clients.add(socket); socket.on('close', () => clients.delete(socket)); });
jobs.on('job', (job) => send({ t: 'job', job }));
jobs.on('event', (id, ev) => send({ t: 'ev', id, ev }));

let fsTimer;
for (const dir of ['planning', 'videos']) {
  try {
    watch(safePath(dir), { recursive: true }, (_e, f) => {
      if (f && /(^|\/)(\.|node_modules|seg\/)/.test(f)) return;
      clearTimeout(fsTimer);
      fsTimer = setTimeout(() => send({ t: 'fs' }), 500);
    });
  } catch {}
}

await app.listen({ host: '127.0.0.1', port: PORT });
console.log(`\n  Studio running → http://127.0.0.1:${PORT}/?t=${TOKEN}\n`);
