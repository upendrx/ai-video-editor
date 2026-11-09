import { useEffect, useRef } from 'react';

async function req(method, url, body) {
  const r = await fetch(url, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body && JSON.stringify(body) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

export const api = {
  board: () => req('GET', '/api/board'),
  tree: (path) => req('GET', `/api/tree?path=${encodeURIComponent(path)}`),
  text: (path) => req('GET', `/api/text?path=${encodeURIComponent(path)}`),
  health: () => req('GET', '/api/health'),
  actions: () => req('GET', '/api/actions'),
  jobs: () => req('GET', '/api/jobs'),
  job: (id) => req('GET', `/api/jobs/${id}`),
  stop: (id) => req('POST', `/api/jobs/${id}/stop`, {}),
  runAction: (id, body) => req('POST', `/api/actions/${id}/run`, body),
  run: (body) => req('POST', '/api/run', body),
};

export const fileUrl = (path) => `/files/${path.split('/').map(encodeURIComponent).join('/')}`;

// WebSocket with auto-reconnect; handler always sees the latest closure.
export function useLive(handler) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    let ws, timer, dead = false;
    const open = () => {
      ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
      ws.onmessage = (e) => ref.current(JSON.parse(e.data));
      ws.onclose = () => { if (!dead) timer = setTimeout(open, 1500); };
    };
    open();
    return () => { dead = true; clearTimeout(timer); ws?.close(); };
  }, []);
}

export const STAGES = ['Idea', 'Topic', 'Script', 'Ready', 'Recorded', 'Edit built', 'Review', 'Exported', 'Published'];

export const fmtDur = (ms) => {
  if (ms == null || ms < 0) return '';
  const s = Math.floor(ms / 1000);
  return s < 3600 ? `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` : `${Math.floor(s / 3600)}h${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`;
};

export const fmtSize = (b) => (b == null ? '' : b < 1024 ? `${b} B` : b < 1 << 20 ? `${(b / 1024).toFixed(0)} KB` : b < 1 << 30 ? `${(b / (1 << 20)).toFixed(1)} MB` : `${(b / (1 << 30)).toFixed(2)} GB`);

export const kindOf = (name) => {
  const ext = name.split('.').pop().toLowerCase();
  if (['mp4', 'mov', 'webm', 'mkv', 'm4v'].includes(ext)) return 'video';
  if (['m4a', 'wav', 'mp3', 'aac', 'flac'].includes(ext)) return 'audio';
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
  if (['html', 'htm'].includes(ext)) return 'html';
  if (ext === 'md') return 'md';
  if (ext === 'pdf') return 'pdf';
  return 'text';
};
