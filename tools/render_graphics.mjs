// Render the kit graphics and the word captions of one build to video files, locally (no AI Producer).
//   node tools/render_graphics.mjs videos/<ep>/03-edit/build [--only m-l07-12,m-o09] [--fps 30] [--jobs 3] [--no-captions]
// Reads build/graphics/{main,over}/hosts.html (start, duration, composition file per graphic) and build/words.json.
// Writes build/render/<id>.mov (HEVC with alpha, one per graphic), build/render/captions.mov (alpha, full length)
// and build/render/manifest.json (what tools/finish_local.py composites). Unchanged graphics are skipped on re-runs.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i < 0 ? d : args[i + 1]; };
const BUILD = path.resolve(args[0]);
const FPS = Number(opt('--fps', 30));
const JOBS = Number(opt('--jobs', 4));
const ONLY = opt('--only', null)?.split(',');
const OUT = path.join(BUILD, 'render');
fs.mkdirSync(OUT, { recursive: true });
const GSAP = fs.readFileSync(path.join(HERE, 'vendor', 'gsap.min.js'), 'utf8');
// HEVC with alpha (VideoToolbox): small files, transparency kept for the overlay pass.
const ALPHA = ['-c:v', 'hevc_videotoolbox', '-alpha_quality', '0.9', '-q:v', '70', '-pix_fmt', 'bgra', '-tag:v', 'hvc1'];
const FONTS = `<link rel="stylesheet" href="file://${path.join(HERE, 'vendor', 'fonts.css')}">`; // Geist + JetBrains Mono, stored locally

function hosts(lane) {
  const f = path.join(BUILD, 'graphics', lane, 'hosts.html');
  if (!fs.existsSync(f)) return [];
  return [...fs.readFileSync(f, 'utf8').matchAll(/<div class="visual-host[^>]*>/g)].map(([tag]) => {
    const a = (k) => (tag.match(new RegExp(`${k}="([^"]*)"`)) || [])[1];
    return { id: a('data-composition-id'), lane, src: path.join(BUILD, 'graphics', lane, a('data-composition-src')),
             start: Number(a('data-start')), duration: Number(a('data-duration')) };
  }).filter((h) => h.id && h.id !== 'narrator-captions');
}

function encoder(file) {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    ...ALPHA, file], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((ok, bad) => ff.on('close', (c) => (c === 0 ? ok() : bad(new Error(`ffmpeg ${c} for ${file}`)))));
  return { kill: () => ff.kill('SIGKILL'), write: (buf) => new Promise((ok) => (ff.stdin.write(buf) ? ok() : ff.stdin.once('drain', ok))), end: () => { ff.stdin.end(); return done; } };
}

async function renderGraphic(ctx, h) {
  const out = path.join(OUT, `${h.id}.mov`);
  if (fs.existsSync(out) && fs.statSync(out).mtimeMs > fs.statSync(h.src).mtimeMs) return 'cached';
  const inner = fs.readFileSync(h.src, 'utf8').replace(/^[\s\S]*?<template>/, '').replace(/<\/template>[\s\S]*$/, '');
  // Written next to the composition so relative asset paths still resolve.
  const tmp = path.join(path.dirname(h.src), `_render_${h.id}.html`);
  fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8">${FONTS}
<style>html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:transparent}
[data-composition-id]{position:relative;width:1920px;height:1080px;overflow:hidden}</style>
<script>${GSAP}</script><script>window.__timelines={};</script></head><body>${inner}</body></html>`);
  const page = await ctx.newPage();
  try {
    await page.goto('file://' + tmp, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    const ok = await page.evaluate((id) => !!window.__timelines[id], h.id);
    if (!ok) throw new Error(`no timeline registered for ${h.id}`);
    await page.evaluate(() => Promise.all(['400 30px Geist', '800 60px Geist', '400 30px "JetBrains Mono"'].map((f) => document.fonts.load(f))));
    var enc = encoder(out);
    const n = Math.max(1, Math.round(h.duration * FPS));
    for (let i = 0; i < n; i++) {
      await page.evaluate(([id, t]) => { window.__timelines[id].seek(t, false); }, [h.id, i / FPS]);
      await enc.write(await page.screenshot({ omitBackground: true, type: 'png' }));
    }
    await enc.end();
    return `${n} frames`;
  } catch (e) {
    enc?.kill(); fs.rmSync(out, { force: true }); throw e;
  } finally {
    await page.close();
    fs.rmSync(tmp, { force: true });
  }
}

// Captions: groups of up to 4 words (new group after punctuation or a 0.35 s gap), current word in amber.

function captionStates(words, windows, total) {
  const groups = []; let g = [];
  words.forEach((w, i) => {
    const prev = words[i - 1];
    if (g.length && (g.length >= 4 || /[.!?,;:]$/.test(prev[0]) || w[1] - prev[2] > 0.35)) { groups.push(g); g = []; }
    g.push(w);
  });
  if (g.length) groups.push(g);
  const states = []; let t = 0;
  groups.forEach((grp, gi) => {
    const end = Math.min(grp[grp.length - 1][2] + 0.25, gi + 1 < groups.length ? groups[gi + 1][0][1] : total);
    grp.forEach((w, wi) => {
      const s = w[1], e = wi + 1 < grp.length ? grp[wi + 1][1] : end;
      if (s > t + 0.01) states.push({ blank: true, d: s - t });
      const win = windows.find((x) => s >= x.start && s < x.end);
      states.push({ words: grp.map((x) => x[0]), active: wi, ink: win?.ink || null, pos: win?.position || 82, d: Math.max(e - s, 1 / FPS) });
      t = s + Math.max(e - s, 1 / FPS);
    });
  });
  if (total > t) states.push({ blank: true, d: total - t });
  return states;
}

// Mis-heard words, fixed by hand: 03-edit/caption-fixes.txt, one "wrong words => right words" per line (# comments).
function applyFixes(words) {
  const f = path.join(BUILD, '..', 'caption-fixes.txt');
  if (!fs.existsSync(f)) return words;
  const norm = (w) => w.toLowerCase().replace(/[^\p{L}\p{N}']/gu, '');
  const rules = fs.readFileSync(f, 'utf8').split('\n').map((l) => l.replace(/#.*/, '').split('=>'))
    .filter((r) => r.length === 2 && r[0].trim()).map(([a, b]) => [a.trim().split(/\s+/).map(norm), b.trim() ? b.trim().split(/\s+/) : []]);
  let out = [...words], n = 0;
  for (const [from, to] of rules) {
    for (let i = 0; i + from.length <= out.length; i++) {
      if (!from.every((w, k) => norm(out[i + k][0]) === w)) continue;
      const seg = out.slice(i, i + from.length), t0 = seg[0][1], t1 = seg[seg.length - 1][2];
      const tail = (seg[seg.length - 1][0].match(/[.,!?;:]+$/) || [''])[0], step = (t1 - t0) / Math.max(1, to.length);
      const rep = to.map((w, k) => [k === to.length - 1 && !/[.,!?;:]$/.test(w) ? w + tail : w, t0 + k * step, t0 + (k + 1) * step]);
      out.splice(i, from.length, ...rep); i += rep.length - 1; n++;
    }
  }
  console.log(`caption fixes: ${n} applied`);
  return out;
}

// Mean brightness (0-255) of the caption band of base.mp4, twice a second; light frames get dark ink.
function bandBrightness() {
  return new Promise((ok) => {
    let o = '';
    const ff = spawn('ffmpeg', ['-v', 'error', '-i', path.join(BUILD, 'base.mp4'), '-vf',
      'fps=2,crop=1600:160:160:800,scale=160:16,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-', '-f', 'null', '-']);
    ff.stdout.on('data', (d) => (o += d)); ff.on('close', () => ok([...o.matchAll(/YAVG=([\d.]+)/g)].map((m) => Number(m[1]))));
  });
}

async function renderCaptions(ctx, total) {
  const fixed = path.join(BUILD, 'words-fixed.json');  // script spelling from tools/fix_captions.py, if it ran
  const words = applyFixes(JSON.parse(fs.readFileSync(fs.existsSync(fixed) ? fixed : path.join(BUILD, 'words.json'), 'utf8')));
  // Dark ink while a full-cover kit card is fully on screen (not during its fades) or the footage under the captions is light;
  // white with a shadow elsewhere.
  // ink follows the episode theme (build/spec_main.json "theme"); dark ink gets a deeper amber highlight so it reads on light ground
  const theme = (() => { try { return JSON.parse(fs.readFileSync(path.join(BUILD, 'spec_main.json'), 'utf8')).theme; } catch { return null; } })();
  const INK = { 'home-warm': '#2b1f17', 'studio-red': '#22191b' }[theme] || '#1c3a3f';
  const windows = hosts('main').map((h) => ({ start: h.start + 0.3, end: h.start + h.duration - 0.35, ink: INK, position: 78 }));
  const lum = await bandBrightness();
  lum.forEach((y, i) => { if (y > 125) windows.push({ start: i / 2, end: (i + 1) / 2, ink: INK, position: 82 }); });
  const states = captionStates(words, windows, total);
  const dir = path.join(OUT, 'cap'); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir);
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(HERE, 'vendor', 'fonts.css'));  // same origin as the local fonts
  await page.setContent(`<!doctype html><html><head>${FONTS}<style>html,body{margin:0;width:1920px;height:1080px;background:transparent;overflow:hidden}
#c{position:absolute;left:160px;right:160px;text-align:center;font:800 64px/1.15 Geist,'Helvetica Neue',Arial,sans-serif;letter-spacing:-.5px}
#c span{margin:0 .14em}</style></head><body><div id="c"></div></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  const list = []; let k = 0;
  for (const s of states) {
    const f = path.join(dir, `${String(k++).padStart(5, '0')}.png`);
    await page.evaluate((s) => {
      const c = document.getElementById('c');
      c.innerHTML = s.blank ? '' : s.words.map((w, i) => `<span style="color:${i === s.active ? (s.ink ? '#c77a12' : '#ffa726') : (s.ink || '#ffffff')}">${w.replace(/</g, '&lt;')}</span>`).join(' ');
      c.style.top = `${(s.pos || 82) * 10.8 - 40}px`;
      c.style.textShadow = s.ink ? 'none' : '0 4px 18px rgba(0,0,0,.75), 0 2px 4px rgba(0,0,0,.8)';
    }, s);
    await page.screenshot({ path: f, omitBackground: true });
    list.push(`file '${f}'\nduration ${s.d.toFixed(4)}`);
  }
  list.push(`file '${path.join(dir, String(k - 1).padStart(5, '0') + '.png')}'`);
  fs.writeFileSync(path.join(dir, 'list.txt'), list.join('\n') + '\n');
  await page.close();
  await new Promise((ok, bad) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'list.txt'),
    '-r', String(FPS), ...ALPHA, path.join(OUT, 'captions.mov')], { stdio: 'inherit' })
    .on('close', (c) => (c === 0 ? ok() : bad(new Error('captions ffmpeg ' + c)))));
  return states.filter((s) => !s.blank).length;
}

const all = [...hosts('main'), ...hosts('over')].filter((h) => !ONLY || ONLY.includes(h.id));
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
ctx.setDefaultTimeout(120000);
let queue = [...all], fails = [];
for (const jobs of [JOBS, 1]) {  // a second, one-at-a-time pass retries anything that failed under load
  const retry = [];
  await Promise.all(Array.from({ length: jobs }, async () => {
    for (let h; (h = queue.shift());) {
      try { console.log(`${h.id}: ${await renderGraphic(ctx, h)}`); } catch (e) { retry.push(h); console.log(`${h.id}: failed (${e.message.split('\n')[0]})`); }
    }
  }));
  queue = retry; fails = retry.map((h) => h.id);
  if (!retry.length) break;
}
let captions = null;
if (!args.includes('--no-captions') && !ONLY) {
  const total = Number(String(await new Promise((ok) => { let o = ''; spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.join(BUILD, 'base.mp4')]).stdout.on('data', (d) => (o += d)).on('end', () => ok(o)); })).trim());
  console.log(`captions: ${await renderCaptions(ctx, total)} states`);
  captions = 'captions.mov';
}
await browser.close();
if (!ONLY) {
  // Pop times per item come from each composition's own AT array (the build-up beats).
  const items = all.map((h) => {
    const at = (fs.readFileSync(h.src, 'utf8').match(/const AT = \[([^\]]*)\]/) || [])[1];
    return { id: h.id, lane: h.lane, file: `${h.id}.mov`, start: h.start, duration: h.duration, beats: at ? at.split(',').map(Number) : [] };
  }).filter((h) => !fails.includes(h.id));
  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify({ fps: FPS, captions, graphics: items, failed: fails }, null, 1));
}
console.log(fails.length ? `done, ${fails.length} failed: ${fails.join(', ')}` : `done, ${all.length} graphics`);
