// Render individual frames to PNG for quick review: node preview.mjs 0.8 3.5 ...
import { chromium } from 'playwright';
import path from 'node:path';
const out = process.env.OUT || 'out/preview';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto('file://' + path.resolve('index.html'));
await page.evaluate(() => window.ready);
const fs = await import('node:fs');
fs.mkdirSync(out, { recursive: true });
for (const a of process.argv.slice(2)) {
  const t = parseFloat(a);
  await page.evaluate(t => window.renderFrame(t), t);
  await page.screenshot({ path: `${out}/t${t.toFixed(2)}.png` });
}
await browser.close();
