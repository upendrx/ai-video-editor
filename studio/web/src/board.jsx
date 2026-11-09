import { marked } from 'marked';
import { STAGES } from './api.js';

const inline = (s) => ({ __html: marked.parseInline(s || '') });

export function BoardView({ board, jobs, openVideo }) {
  if (!board) return <div className="work pad"><div className="empty">Loading board…</div></div>;
  const busy = new Set(jobs.filter((j) => j.status === 'running').map((j) => j.video));
  return (
    <div className="work pad boardview">
      <div className="weekends">
        <div className="sh">Weekend plan <span className="muted">board updated {board.updated}</span></div>
        <div className="wk-row">
          {board.weekends.map((w) => (
            <div key={w.when} className="wk">
              <b dangerouslySetInnerHTML={inline(w.when)} />
              <p dangerouslySetInnerHTML={inline(w.you)} />
            </div>
          ))}
        </div>
      </div>
      <div className="kanban">
        {STAGES.map((s, i) => {
          const cards = board.videos.filter((v) => v.stage === i);
          return (
            <div key={s} className="col">
              <div className="colh"><span className={`pill s${i}`}>{i}</span>{s}<span className="muted">{cards.length}</span></div>
              {cards.map((v) => (
                <button key={v.id} className={`card ${v.dir ? '' : 'idea'}`} onClick={() => v.dir && openVideo(v.dir)} disabled={!v.dir}>
                  <div className="ch">
                    <span className="num">{v.num || '—'}</span>
                    <span className="chips">{v.lang && <em>{v.lang}</em>}{v.kind && <em>{v.kind.split(' ')[0]}</em>}</span>
                    {busy.has(v.dir) && <span className="spin" title="job running" />}
                  </div>
                  <div className="ct">{v.title}</div>
                  {v.next && <div className="cn" dangerouslySetInnerHTML={inline(v.next)} />}
                </button>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
