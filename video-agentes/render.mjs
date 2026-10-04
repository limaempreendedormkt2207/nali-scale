// Renders index.html frame by frame (30fps, 15s, 1080x1920) and muxes with out/trilha.wav
// Usage: node audio.mjs && node render.mjs
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const FPS = 30, DUR = 15, FRAMES = FPS * DUR;
const OUT = 'out/agentes-nali-15s.mp4';
const hasAudio = fs.existsSync('out/trilha.wav');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('[pageerror]', e.message));
await page.goto('file://' + path.resolve('index.html'));
await page.evaluate(() => window.ready);

const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-'];
if (hasAudio) args.push('-i', 'out/trilha.wav');
args.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
  '-r', String(FPS), '-movflags', '+faststart');
if (hasAudio) args.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
args.push(OUT);
const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });

const t0 = Date.now();
for (let f = 0; f < FRAMES; f++) {
  await page.evaluate(t => window.renderFrame(t), f / FPS);
  const png = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r));
  if (f % 30 === 0) console.log(`frame ${f}/${FRAMES} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('done ->', OUT);
