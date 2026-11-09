// Proof screenshots for the documentary b-roll. Run through the Playwright MCP:
//   browser_run_code_unsafe(filename = "videos/007-rust-ai-elon-was-right/03-edit/capture_proof.js")
// Per source: <name>-top.png (headline) and <name>-hlN.png (key sentence marked in amber), 1920x1080.
async (page) => {
  const OUT = '/Users/upendrasingh/Movies/video-editing-agent/videos/007-rust-ai-elon-was-right/03-edit/proof/';
  const SRC = [
    ['github-blog-copilot', 'https://github.blog/ai-and-ml/migrating-the-github-copilot-runtime-to-rust-using-copilot/', ['292', '100 MB', '800,000', '1.7%', '$120,000']],
    ['infoq-copilot', 'https://www.infoq.com/news/2026/10/github-copilot-rust-migration/', ['5.25 seconds']],
    ['codex-going-native', 'https://github.com/openai/codex/discussions/1174', ['Node', 'Rust']],
    ['bun-blog-rust', 'https://bun.com/blog/bun-in-rust', ['forgot to free', 'better feedback loop', '535,496', 'Claude Fable 5']],
    ['register-bun', 'https://www.theregister.com/devops/2026/05/14/anthropics-bun-rust-rewrite-merged-at-speed-of-ai/5240381', ['Rust']],
        ['chromium-70', 'https://www.chromium.org/Home/chromium-security/memory-safety/', ['70%']],
    ['discord-go-rust', 'https://discord.com/blog/why-discord-is-switching-from-go-to-rust', ['every 2 minutes', 'Rust']],
    ['google-android-rust', 'https://blog.google/security/rust-in-android-move-fast-fix-things/', ['1000x', '20%', 'rollback']],
    ['nvidia-cuda-rust', 'https://developer.nvidia.com/blog/introducing-cuda-rust-two-tracks-for-writing-gpu-kernels/', ['alpha', 'Rust']],
    ['repo-codex', 'https://github.com/openai/codex', []],
    ['repo-bun', 'https://github.com/oven-sh/bun', []],
    ['repo-tokenizers', 'https://github.com/huggingface/tokenizers', []],
    ['repo-tiktoken', 'https://github.com/openai/tiktoken', []],
    ['repo-pydantic-core', 'https://github.com/pydantic/pydantic-core', []],
    ['repo-polars', 'https://github.com/pola-rs/polars', []],
    ['repo-uv', 'https://github.com/astral-sh/uv', []],
  ];
  const ONLY = globalThis.PROOF_ONLY || null; // e.g. ['msrc-70'] to re-run a few
  await page.setViewportSize({ width: 1920, height: 1080 });
  const log = [];
  for (const [name, url, phrases] of SRC) {
    if (ONLY && !ONLY.includes(name)) continue;
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(3500);
      // Best-effort: close cookie and consent banners.
      for (const t of ['Accept all', 'Accept All', 'Accept', 'I agree', 'Got it', 'Allow all', 'Agree']) {
        const b = page.getByRole('button', { name: t, exact: true }).first();
        if (await b.isVisible().catch(() => false)) { await b.click().catch(() => {}); await page.waitForTimeout(500); }
      }
      await page.screenshot({ path: `${OUT}${name}-top.png` });
      if (name.startsWith('repo-')) {
        // Languages box in the repo sidebar, marked in amber.
        const ok = await page.evaluate(() => {
          const h = [...document.querySelectorAll('h2')].find(e => e.textContent.trim() === 'Languages');
          if (!h) return false;
          const box = h.closest('.BorderGrid-cell') || h.parentElement;
          box.style.outline = '4px solid #ffa726'; box.style.borderRadius = '10px'; box.style.background = '#ffa72622';
          box.scrollIntoView({ block: 'center' });
          return box.innerText.replace(/\s+/g, ' ').slice(0, 160);
        });
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${OUT}${name}-hl1.png` });
        log.push([name, 'langs', ok]);
        continue;
      }
      let i = 0;
      for (const p of phrases) {
        const found = await page.evaluate((p) => {
          document.querySelectorAll('mark[data-proof]').forEach(m => m.replaceWith(...m.childNodes));
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let n;
          while ((n = w.nextNode())) {
            const k = n.textContent.indexOf(p);
            if (k < 0 || !n.parentElement || n.parentElement.closest('nav,header,footer,script,style')) continue;
            const r = n.parentElement.getBoundingClientRect(); if (!r.width) continue;
            // Mark the whole sentence around the phrase.
            const t = n.textContent; const s = Math.max(t.lastIndexOf('. ', k) + 1, 0); let e = t.indexOf('. ', k + p.length); e = e < 0 ? t.length : e + 1;
            const range = document.createRange(); range.setStart(n, s); range.setEnd(n, e);
            const m = document.createElement('mark'); m.dataset.proof = '1';
            m.style.cssText = 'background:#ffa726;color:#07191a;padding:2px 4px;border-radius:4px;box-decoration-break:clone;-webkit-box-decoration-break:clone';
            range.surroundContents(m);
            m.scrollIntoView({ block: 'center' });
            return t.slice(s, e).trim().slice(0, 200);
          }
          return null;
        }, p);
        if (!found) { log.push([name, p, 'NOT FOUND']); continue; }
        i += 1;
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${OUT}${name}-hl${i}.png` });
        // Close-up: page zoomed 1.7x, the marked sentence centred, for the push-in.
        await page.evaluate(() => { document.documentElement.style.zoom = '1.7'; document.querySelector('mark[data-proof]').scrollIntoView({ block: 'center', inline: 'center' }); });
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${OUT}${name}-hl${i}-zoom.png` });
        await page.evaluate(() => { document.documentElement.style.zoom = ''; });
        log.push([name, p, found]);
      }
    } catch (e) { log.push([name, 'ERROR', String(e).slice(0, 120)]); }
  }
  return log;
}
