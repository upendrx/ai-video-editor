import { useEffect, useMemo, useState } from 'react';
import { marked } from 'marked';
import { api, fileUrl, fmtSize, kindOf, STAGES } from './api.js';
import { ModePicker } from './jobs.jsx';

const inline = (s) => ({ __html: marked.parseInline(s || '') });
const MISSING = { shots: 'Needs 03-edit/shots.json', script: 'Needs 01-script/script.md', build: 'Needs 03-edit/build (run Build first cut)' };
const ICON = { video: '▶', audio: '♪', image: '▣', html: '◧', md: '¶', pdf: '▤', text: '≡' };

// ---------- media pool
export function Bin({ board, video, setVideo, file, setFile, fsTick }) {
  const [tree, setTree] = useState([]);
  useEffect(() => { if (video) api.tree(`videos/${video}`).then(setTree).catch(() => setTree([])); }, [video, fsTick]);
  const eps = (board?.videos || []).filter((v) => v.dir);

  return (
    <section className="panel">
      <div className="ph"><span>Media Pool</span><span className="muted">{eps.length} episodes</span></div>
      <div className="scroll">
        {eps.map((v) => (
          <div key={v.dir}>
            <button className={`ep ${v.dir === video ? 'sel' : ''}`} onClick={() => setVideo(v.dir)}>
              <span className="num">{v.num}</span>
              <span className="t">{v.title}</span>
              <StagePill stage={v.stage} />
            </button>
            {v.dir === video && (
              <div className="tree">
                {tree.map((n) => <Node key={n.path} n={n} depth={0} file={file} setFile={setFile} />)}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Node({ n, depth, file, setFile }) {
  const raw = n.name === '02-raw';
  const [open, setOpen] = useState(depth === 0 && !raw && n.name !== '04-export');
  const pad = { paddingLeft: 10 + depth * 13 };
  if (n.dir) {
    return (
      <>
        <button className="node dir" style={pad} onClick={() => setOpen(!open)}>
          <span className="car">{open ? '▾' : '▸'}</span>{n.name}
          {raw && <span className="lock" title="Never modified by Studio">read only</span>}
          <span className="cnt">{n.children.length}</span>
        </button>
        {open && n.children.map((c) => <Node key={c.path} n={c} depth={depth + 1} file={file} setFile={setFile} />)}
      </>
    );
  }
  const k = kindOf(n.name);
  return (
    <button className={`node ${file === n.path ? 'sel' : ''}`} style={pad} onClick={() => setFile(n.path)} title={n.path}>
      <span className={`ic k-${k}`}>{ICON[k]}</span><span className="nm">{n.name}</span><span className="cnt">{fmtSize(n.size)}</span>
    </button>
  );
}

export const StagePill = ({ stage }) => <span className={`pill s${stage}`}>{stage} {STAGES[stage]}</span>;

// ---------- viewer
export function Viewer({ video, file, fsTick }) {
  const path = file || (video?.dir ? `videos/${video.dir}/STATUS.md` : null);
  const kind = path ? kindOf(path) : null;
  const [text, setText] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setText(null); setErr(null);
    if (path && (kind === 'md' || kind === 'text')) api.text(path).then((r) => setText(r.text)).catch((e) => setErr(e.message));
  }, [path, kind, fsTick]);

  const html = useMemo(() => (kind === 'md' && text != null ? marked.parse(text) : null), [kind, text]);
  const crumbs = path ? path.split('/') : [];

  return (
    <section className="panel viewer">
      <div className="ph">
        <span className="crumbs">{crumbs.map((c, i) => <span key={i} className={i === crumbs.length - 1 ? 'last' : ''}>{c}</span>)}</span>
        {path && <a className="ghost" href={fileUrl(path)} target="_blank" rel="noreferrer">Open ↗</a>}
      </div>
      <div className={`stage-area k-${kind}`}>
        {!path && <div className="empty">Select an episode</div>}
        {kind === 'video' && <video key={path} src={fileUrl(path)} controls preload="metadata" />}
        {kind === 'audio' && <div className="audio"><div className="wave" /><audio key={path} src={fileUrl(path)} controls /></div>}
        {kind === 'image' && <img key={path} src={fileUrl(path)} alt="" />}
        {(kind === 'html' || kind === 'pdf') && <iframe key={path} src={fileUrl(path)} title={path} sandbox="allow-scripts allow-same-origin" />}
        {kind === 'md' && html && <article className="doc" dangerouslySetInnerHTML={{ __html: html }} />}
        {kind === 'text' && text != null && <pre className="code">{text}</pre>}
        {err && <div className="empty">{err}</div>}
      </div>
    </section>
  );
}

// ---------- inspector
export function Inspector({ video, file, actions, mode, setMode, health, jobs, onAction }) {
  if (!video) return <section className="panel"><div className="ph"><span>Inspector</span></div></section>;
  const st = video.status;
  const done = st?.checklist.filter((c) => c.done).length || 0;
  const fileKind = file ? kindOf(file) : null;
  const groups = [
    ['claude', 'Claude', 'A', !!health?.claude?.version],
    ['agy', 'Antigravity', 'B', !!health?.agy?.version],
    ['script', 'Scripts', 'C', true],
  ];
  const isRunning = (a) => jobs.some((j) => j.video === video.dir && j.title === a.label && (j.status === 'running' || j.status === 'queued'));

  const run = (a) => {
    if (a.confirm && !window.confirm(a.confirm)) return;
    if (a.engine !== 'script' && mode === 'full' && !window.confirm('Full access: the AI can run any command without asking. Continue?')) return;
    onAction(a);
  };

  return (
    <section className="panel inspector">
      <div className="ph"><span>Inspector</span><span className="muted">{video.lang} · {video.kind}</span></div>
      <div className="scroll">
        <div className="sec">
          <div className="ep-title"><span className="num big">{video.num}</span>{video.title}</div>
          <div className="stagebar">{STAGES.map((s, i) => <i key={s} className={i < video.stage ? 'done' : i === video.stage ? 'cur' : ''} title={`${i} ${s}`} />)}</div>
          <div className="kv"><span>Stage</span><b>{video.stage} · {STAGES[video.stage]}</b></div>
          {st?.current && <p className="note" dangerouslySetInnerHTML={inline(st.current.replace(/^\d+\s*/, ''))} />}
          {video.next && <div className="next"><span>Next</span><p dangerouslySetInnerHTML={inline(video.next)} /></div>}
        </div>

        {st?.checklist.length > 0 && (
          <div className="sec">
            <div className="sh">Checklist <span className="muted">{done}/{st.checklist.length}</span></div>
            <ul className="check">
              {st.checklist.map((c, i) => <li key={i} className={c.done ? 'done' : ''}><i />{<span dangerouslySetInnerHTML={inline(c.text)} />}</li>)}
            </ul>
          </div>
        )}

        <div className="sec">
          <div className="sh">Actions <ModePicker mode={mode} setMode={setMode} /></div>
          {groups.map(([engine, name, tier, ok]) => (
            <div key={engine} className="agroup">
              <div className="gh"><span className={`tier t${tier}`}>{tier}</span>{name}{!ok && <span className="warn">not ready</span>}</div>
              {actions.filter((a) => a.engine === engine).map((a) => {
                const missing = a.requires && !video.has?.[a.requires] ? MISSING[a.requires] : null;
                const blocked = !ok || !!missing || (a.needs === 'video' && fileKind !== 'video');
                return (
                  <button key={a.id} className="action" disabled={blocked} onClick={() => run(a)}
                    title={missing || (a.needs && fileKind !== 'video' ? 'Select a video file in the Media Pool first' : a.hint)}>
                    <span className="al">{a.label}<small>{a.hint}</small></span>
                    {isRunning(a) ? <span className="spin" /> : <span className="go">▶</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ---------- pipeline track (timeline look)
export function Pipeline({ video }) {
  const stage = video?.stage ?? 0;
  return (
    <div className="pipeline">
      <div className="track-head">PIPELINE<small>{video ? `${video.num} · ${video.title}` : ''}</small></div>
      <div className="track">
        <div className="ruler">{STAGES.map((s, i) => <span key={s}>{i}</span>)}</div>
        <div className="clips">
          {STAGES.map((s, i) => <div key={s} className={`clip ${i < stage ? 'done' : i === stage ? 'cur' : ''}`}><span>{s}</span></div>)}
          <div className="playhead" style={{ left: `calc(${((stage + 0.5) / STAGES.length) * 100}% )` }} />
        </div>
      </div>
    </div>
  );
}
