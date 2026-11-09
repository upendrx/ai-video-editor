// Read-only access to the repo: board, status files, file trees.
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(fileURLToPath(new URL('../..', import.meta.url)));
const SKIP = new Set(['node_modules', '__pycache__', 'seg']);

export function safePath(rel = '') {
  const p = path.resolve(ROOT, rel);
  if (p !== ROOT && !p.startsWith(ROOT + path.sep)) throw new Error('path outside repo');
  return p;
}

const read = (rel) => { try { return readFileSync(safePath(rel), 'utf8'); } catch { return null; } };

// Rows of the first markdown table under "## <heading>".
function table(md, heading) {
  const lines = md.split('\n');
  const start = lines.findIndex((l) => l.startsWith('## ') && l.includes(heading));
  if (start < 0) return [];
  const rows = [];
  for (const l of lines.slice(start + 1)) {
    if (l.startsWith('## ')) break;
    if (!l.startsWith('|') || /^\|[\s:|-]+\|$/.test(l.trim())) continue;
    rows.push(l.trim().slice(1, -1).split('|').map((c) => c.trim()));
  }
  return rows.slice(1); // drop header
}

function status(dir) {
  const md = read(`videos/${dir}/STATUS.md`);
  if (!md) return null;
  const title = (md.match(/^# Status:\s*(.+)$/m) || [])[1] || dir;
  const current = (md.match(/\*\*Current stage:\*\*\s*(.+)$/m) || [])[1] || '';
  const checklist = [...md.matchAll(/^- \[([ x])\]\s*(.+)$/gm)].map((m) => ({ done: m[1] === 'x', text: m[2] }));
  return { title, current, stage: parseInt(current, 10), checklist };
}

export function readBoard() {
  const md = read('planning/BOARD.md') || '';
  const updated = (md.match(/^Updated ([^.]+)\./m) || [])[1] || '';
  const weekends = table(md, 'Weekend plan').map(([when, you, claude]) => ({ when, you, claude }));
  const dirs = existsSync(safePath('videos'))
    ? readdirSync(safePath('videos')).filter((d) => /^\d{3}-/.test(d) && statSync(safePath(`videos/${d}`)).isDirectory())
    : [];
  const videos = table(md, 'All videos').map(([num, folder, title, lang, kind, stage, next]) => {
    const dir = (folder.match(/videos\/([^`/\s]+)/) || [])[1] || null;
    const stageNum = parseInt(stage, 10);
    return { id: dir || `plan-${title}`, num: num === '—' ? null : num, dir, plan: dir ? null : folder.replace(/[()]/g, ''),
      title: title.replace(/\*\*/g, ''), lang, kind, stage: Number.isNaN(stageNum) ? 0 : stageNum, next };
  });
  for (const d of dirs) if (!videos.some((v) => v.dir === d)) videos.push({ id: d, num: d.slice(0, 3), dir: d, title: d, lang: '', kind: '', stage: 0, next: '' });
  const has = (d, f) => existsSync(safePath(`videos/${d}/${f}`));
  for (const v of videos) if (v.dir) {
    v.status = status(v.dir);
    v.has = { shots: has(v.dir, '03-edit/shots.json'), script: has(v.dir, '01-script/script.md'), build: has(v.dir, '03-edit/build') };
  }
  return { updated, weekends, videos };
}

export function listTree(rel, depth = 4) {
  const abs = safePath(rel);
  let names;
  try { names = readdirSync(abs); } catch { return []; }
  return names
    .filter((n) => !n.startsWith('.') && !SKIP.has(n))
    .map((n) => {
      const p = path.join(abs, n);
      const st = statSync(p);
      const r = path.relative(ROOT, p);
      return st.isDirectory()
        ? { name: n, path: r, dir: true, children: depth > 1 ? listTree(r, depth - 1) : [] }
        : { name: n, path: r, dir: false, size: st.size, mtime: st.mtimeMs };
    })
    .sort((a, b) => (b.dir - a.dir) || a.name.localeCompare(b.name, undefined, { numeric: true }))
    .slice(0, 300);
}

export function readText(rel, max = 1_000_000) {
  const abs = safePath(rel);
  if (statSync(abs).size > max) return null;
  return readFileSync(abs, 'utf8');
}
