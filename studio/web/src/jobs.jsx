import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { marked } from 'marked';
import { api, fmtDur } from './api.js';

export const MODES = [
  ['plan', 'Plan', 'Read only, changes nothing'],
  ['ask', 'Ask before edits', 'Blocked actions come back for you to allow'],
  ['edit', 'Edit automatically', 'Edits files, risky commands blocked'],
  ['auto', 'Auto', 'Decides for itself what is safe to run'],
  ['full', 'Full access', 'Runs anything without asking'],
];

export function ModePicker({ mode, setMode, up }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();
  useEffect(() => {
    const close = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  const cur = MODES.find((m) => m[0] === mode) || MODES[2];
  return (
    <span className="mode" ref={ref}>
      <button className={`mode-btn m-${cur[0]}`} onClick={() => setOpen(!open)} title="Permission mode for AI runs"><i />{cur[1]} ▾</button>
      {open && (
        <div className={`menu ${up ? 'up' : ''}`}>
          {MODES.map(([k, l, d]) => (
            <button key={k} className={`m-${k} ${k === mode ? 'on' : ''}`} onClick={() => { setMode(k); setOpen(false); }}>
              <i /><span>{l}<small>{d}</small></span>
            </button>
          ))}
        </div>
      )}
    </span>
  );
}

export function CommandBar({ video, videos, setVideo, mode, setMode, health, onRun }) {
  const [engine, setEngine] = useState('claude');
  const [text, setText] = useState('');
  const ref = useRef();
  useEffect(() => {
    const k = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); ref.current?.focus(); } };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, []);
  const submit = () => {
    if (!text.trim()) return;
    if (engine !== 'shell' && mode === 'full' && !window.confirm('Full access: the AI can run any command without asking. Continue?')) return;
    onRun({ engine, text, video, mode });
    setText('');
  };
  const ph = engine === 'shell' ? 'Shell command, runs in the repo folder…' : `Ask ${engine === 'claude' ? 'Claude' : 'Antigravity'}${video ? ` about ${video.slice(0, 3)}` : ''}…`;
  return (
    <div className="cmd">
      <div className="seg">
        {[['claude', 'Claude'], ['agy', 'Antigravity'], ['shell', 'Shell']].map(([k, l]) => (
          <button key={k} className={engine === k ? 'on' : ''} onClick={() => setEngine(k)}>{l}</button>
        ))}
      </div>
      <select className="epsel" value={video || ''} onChange={(e) => setVideo(e.target.value || null)} title="Episode context">
        {videos.filter((v) => v.dir).map((v) => <option key={v.dir} value={v.dir}>{v.num} · {v.title.slice(0, 34)}</option>)}
      </select>
      <input ref={ref} value={text} placeholder={ph} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') submit(); }} />
      <kbd>⌘K</kbd>
      {engine !== 'shell' && <ModePicker mode={mode} setMode={setMode} />}
      <button className="run" onClick={submit} disabled={!text.trim() || (engine === 'agy' && !health?.agy?.version)}>Run ⏎</button>
    </div>
  );
}

function useNow(active) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { if (!active) return; const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, [active]);
  return now;
}

const ENGINE = { claude: 'Claude', agy: 'Antigravity', script: 'Script' };
const dur = (j, now) => fmtDur((j.ended || (j.started ? now : null)) - j.started);

export function JobsPanel({ jobs, jobId, setJobId, events, mode, onRun, compact }) {
  const now = useNow(jobs.some((j) => j.status === 'running'));
  const job = jobs.find((j) => j.id === jobId);
  return (
    <div className={`jobs ${compact ? 'compact' : ''}`}>
      <div className="joblist">
        <div className="ph"><span>Jobs</span><span className="muted">{jobs.filter((j) => j.status === 'running').length} running</span></div>
        <div className="scroll">
          {jobs.length === 0 && <div className="empty sm">No runs yet. Click an action or type a prompt.</div>}
          {jobs.map((j) => (
            <button key={j.id} className={`jrow ${j.id === jobId ? 'sel' : ''}`} onClick={() => setJobId(j.id)}>
              <i className={`dot ${j.status}`} />
              <span className={`eng e-${j.engine}`}>{ENGINE[j.engine]}</span>
              <span className="jt">{j.title}</span>
              <span className="jv">{j.video?.slice(0, 3)}</span>
              <span className="jd">{j.status === 'queued' ? 'queued' : dur(j, now)}</span>
            </button>
          ))}
        </div>
      </div>
      <Feed job={job} events={events} now={now} mode={mode} onRun={onRun} />
    </div>
  );
}

function Feed({ job, events, now, mode, onRun }) {
  const ref = useRef();
  const stick = useRef(true);
  const [reply, setReply] = useState('');
  useLayoutEffect(() => { if (stick.current && ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [events]);
  useEffect(() => { stick.current = true; }, [job?.id]);
  const shown = useMemo(() => events.slice(-2000), [events]);

  if (!job) return <div className="feed"><div className="ph"><span>Output</span></div><div className="empty">Select a job to see its live output</div></div>;
  const live = job.status === 'running' || job.status === 'queued';
  const canContinue = (job.engine === 'claude' || job.engine === 'agy') && job.session_id && !live;
  const cont = (text, allow) => { onRun({ engine: job.engine, text, video: job.video, mode, resume: job.session_id, allow }); setReply(''); };

  return (
    <div className="feed">
      <div className="ph">
        <span className="ft"><i className={`dot ${job.status}`} />{job.title}</span>
        <span className="meta">
          <span className={`eng e-${job.engine}`}>{ENGINE[job.engine]}</span>
          {job.mode && <span className="muted">{MODES.find((m) => m[0] === job.mode)?.[1]}</span>}
          <span className="muted">{job.status} · {dur(job, now)}</span>
          {job.cost != null && <span className="muted">${job.cost.toFixed(2)}</span>}
          {live && <button className="stop" onClick={() => api.stop(job.id)}>■ Stop</button>}
        </span>
      </div>
      <div className="log" ref={ref} onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40; }}>
        {shown.map((e) => <Ev key={e.seq} e={e} />)}
        {live && <div className="ev sys"><span className="spin" /> working…</div>}
      </div>
      {canContinue && job.denials?.length > 0 && (
        <div className="denied">
          <div><b>Blocked:</b> Claude needed permission for {job.denials.join(', ')}.</div>
          <button onClick={() => cont(`You now have permission to use ${job.denials.join(', ')}. Continue where you stopped.`, job.denials)}>Allow &amp; continue</button>
        </div>
      )}
      {canContinue && (
        <div className="reply">
          <input value={reply} placeholder="Reply to continue this session…" onChange={(e) => setReply(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && reply.trim()) cont(reply); }} />
          <button disabled={!reply.trim()} onClick={() => cont(reply)}>Continue</button>
        </div>
      )}
    </div>
  );
}

function Ev({ e }) {
  if (e.kind === 'text') return <div className="ev text" dangerouslySetInnerHTML={{ __html: marked.parse(e.text) }} />;
  if (e.kind === 'tool') { const [n, ...r] = e.text.split('  '); return <div className="ev tool"><b>{n}</b>{r.join('  ')}</div>; }
  return <div className={`ev ${e.kind}`}>{e.text}</div>;
}
