import { useCallback, useEffect, useRef, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { api, useLive } from './api.js';
import { Bin, Viewer, Inspector, Pipeline } from './panels.jsx';
import { CommandBar, JobsPanel } from './jobs.jsx';
import { BoardView } from './board.jsx';

const H = () => <PanelResizeHandle className="handle h" />;
const V = () => <PanelResizeHandle className="handle v" />;

export default function App() {
  const [page, setPage] = useState('edit');
  const [board, setBoard] = useState(null);
  const [health, setHealth] = useState(null);
  const [actions, setActions] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [video, setVideo] = useState(null);
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [events, setEvents] = useState([]);
  const [mode, setMode] = useState(() => { try { return localStorage.getItem('studio.mode') || 'edit'; } catch { return 'edit'; } });
  const [fsTick, setFsTick] = useState(0);
  const [toast, setToast] = useState(null);
  const jobIdRef = useRef(jobId);
  jobIdRef.current = jobId;

  const loadBoard = useCallback(() => api.board().then(setBoard).catch(() => {}), []);
  useEffect(() => {
    loadBoard();
    api.health().then(setHealth).catch(() => {});
    api.actions().then(setActions).catch(() => {});
    api.jobs().then(setJobs).catch(() => {});
  }, [loadBoard]);

  useEffect(() => {
    if (!video && board) setVideo(board.videos.find((v) => v.dir && v.stage >= 1 && v.stage <= 6)?.dir || board.videos.find((v) => v.dir)?.dir);
  }, [board, video]);

  useEffect(() => { try { localStorage.setItem('studio.mode', mode); } catch {} }, [mode]);

  useEffect(() => {
    if (!jobId) return setEvents([]);
    api.job(jobId).then((r) => { if (jobIdRef.current === jobId) setEvents(r.events); }).catch(() => {});
  }, [jobId]);

  useLive((m) => {
    if (m.t === 'job') {
      setJobs((js) => [m.job, ...js.filter((j) => j.id !== m.job.id)].sort((a, b) => b.id - a.id));
      if (m.job.status === 'done' || m.job.status === 'failed') {
        setToast({ ok: m.job.status === 'done', text: `${m.job.title} · ${m.job.status}` });
        setTimeout(() => setToast(null), 4000);
      }
    } else if (m.t === 'ev' && m.id === jobIdRef.current) setEvents((es) => [...es, m.ev]);
    else if (m.t === 'fs') { loadBoard(); setFsTick((x) => x + 1); }
  });

  const start = async (p) => {
    try {
      const job = await p;
      setJobId(job.id);
      setJobs((js) => [job, ...js.filter((j) => j.id !== job.id)]);
    } catch (e) { setToast({ ok: false, text: e.message }); setTimeout(() => setToast(null), 4000); }
  };

  const current = board?.videos.find((v) => v.dir === video);
  const running = jobs.filter((j) => j.status === 'running').length;
  const openVideo = (dir) => { setVideo(dir); setFile(null); setPage('edit'); };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="logo" />Studio<span className="sub">Rust in AI</span></div>
        <nav className="pages">
          {[['edit', 'Edit'], ['board', 'Board'], ['jobs', 'Jobs']].map(([k, l]) => (
            <button key={k} className={page === k ? 'on' : ''} onClick={() => setPage(k)}>
              {l}{k === 'jobs' && running > 0 && <span className="badge">{running}</span>}
            </button>
          ))}
        </nav>
        <CommandBar video={video} videos={board?.videos || []} setVideo={openVideo} mode={mode} setMode={setMode} health={health}
          onRun={(body) => start(api.run(body))} />
        <div className="health">
          <Engine name="Claude" ok={!!health?.claude?.version} title={health?.claude?.version} />
          <Engine name="Antigravity" ok={!!health?.agy?.version} title={health?.agy?.version ? `agy ${health.agy.version}` : 'agy not found in ~/.gemini/bin'} />
        </div>
      </header>

      {page === 'edit' && (
        <PanelGroup direction="vertical" autoSaveId="studio.v" className="work">
          <Panel defaultSize={66} minSize={30}>
            <PanelGroup direction="horizontal" autoSaveId="studio.h">
              <Panel defaultSize={19} minSize={12}>
                <Bin board={board} video={video} setVideo={(d) => { setVideo(d); setFile(null); }} file={file} setFile={setFile} fsTick={fsTick} />
              </Panel>
              <H />
              <Panel defaultSize={53} minSize={25}>
                <Viewer video={current} file={file} fsTick={fsTick} />
              </Panel>
              <H />
              <Panel defaultSize={28} minSize={18}>
                <Inspector video={current} file={file} actions={actions} mode={mode} setMode={setMode} health={health}
                  jobs={jobs} onAction={(a) => start(api.runAction(a.id, { video, mode, file }))} />
              </Panel>
            </PanelGroup>
          </Panel>
          <V />
          <Panel defaultSize={34} minSize={14}>
            <div className="bottom">
              <Pipeline video={current} />
              <JobsPanel jobs={jobs.filter((j) => !video || j.video === video || !j.video)} jobId={jobId} setJobId={setJobId} events={events}
                mode={mode} onRun={(body) => start(api.run(body))} compact />
            </div>
          </Panel>
        </PanelGroup>
      )}
      {page === 'board' && <BoardView board={board} jobs={jobs} openVideo={openVideo} />}
      {page === 'jobs' && (
        <div className="work pad"><JobsPanel jobs={jobs} jobId={jobId} setJobId={setJobId} events={events} mode={mode} onRun={(body) => start(api.run(body))} /></div>
      )}
      {toast && <div className={`toast ${toast.ok ? 'ok' : 'bad'}`}>{toast.text}</div>}
    </div>
  );
}

const Engine = ({ name, ok, title }) => (
  <span className={`engine ${ok ? 'ok' : 'off'}`} title={title || 'not found'}><i />{name}</span>
);
