import { chromium } from 'playwright';
const [spec, out] = process.argv.slice(2);
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1932, height: 2600 } });
await p.goto(`http://127.0.0.1:8765/series/rust-in-ai/kit/harness/contact.html?spec=${spec}`);
await p.waitForTimeout(6000); await p.screenshot({ path: out, fullPage: true }); await b.close();
