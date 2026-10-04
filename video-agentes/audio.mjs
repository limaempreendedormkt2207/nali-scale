// Synthesizes the 15s soundtrack (music bed + SFX synced to the animation) -> out/trilha.wav
// Timeline mirrors T in index.html. Beat grid: 0.3 + 0.35n (kick every 0.7s).
import fs from 'node:fs';

const SR = 48000, DUR = 15, N = SR * DUR;
const L = new Float32Array(N), Rr = new Float32Array(N), SEND = new Float32Array(N);
let seed = 1234567;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
const noise = () => rnd() * 2 - 1;
const TAU = Math.PI * 2;
const mtof = m => 440 * Math.pow(2, (m - 69) / 12);

function put(i, v, pan = 0, send = 0) {
  if (i < 0 || i >= N) return;
  const gl = Math.cos((pan + 1) * Math.PI / 4), gr = Math.sin((pan + 1) * Math.PI / 4);
  L[i] += v * gl * 1.414; Rr[i] += v * gr * 1.414; SEND[i] += v * send;
}

/* ---------- instruments ---------- */
function kick(t0, lvl = .55) {
  let ph = 0; const s = Math.floor(t0 * SR);
  for (let k = 0; k < SR * .5; k++) {
    const tt = k / SR;
    const f = 46 + 120 * Math.exp(-tt * 30);
    ph += TAU * f / SR;
    const env = Math.exp(-tt * 7.5) * Math.min(1, tt / .002);
    put(s + k, (Math.sin(ph) * env + noise() * Math.exp(-tt * 400) * .25) * lvl);
  }
}
function hat(t0, lvl = .05, pan = 0) {
  const s = Math.floor(t0 * SR); let prev = 0;
  for (let k = 0; k < SR * .08; k++) {
    const x = noise(); const y = x - prev; prev = x;
    put(s + k, y * Math.exp(-k / SR * 60) * lvl, pan, .1);
  }
}
function pluck(t0, f, lvl = .06, pan = 0) {
  const s = Math.floor(t0 * SR);
  for (let k = 0; k < SR * .6; k++) {
    const tt = k / SR;
    const v = Math.sin(TAU * f * tt) * Math.exp(-tt * 9) + .35 * Math.sin(TAU * 2 * f * tt) * Math.exp(-tt * 16);
    put(s + k, v * lvl * Math.min(1, tt / .003), pan, .45);
  }
}
function bell(t0, f, lvl = .16, pan = 0) {
  const s = Math.floor(t0 * SR);
  for (let k = 0; k < SR * 1.6; k++) {
    const tt = k / SR;
    const v = Math.sin(TAU * f * tt + 1.1 * Math.sin(TAU * 2 * f * tt) * Math.exp(-tt * 7)) * Math.exp(-tt * 4.2);
    put(s + k, v * lvl * Math.min(1, tt / .002), pan, .6);
  }
}
// state-variable filtered noise sweep (whoosh / riser)
function sweep(t0, dur, f0, f1, lvl, { shape = 'hump', q = 2.2, pan0 = 0, pan1 = 0, send = .35 } = {}) {
  const s = Math.floor(t0 * SR), n = Math.floor(dur * SR);
  let low = 0, band = 0;
  for (let k = 0; k < n; k++) {
    const x = k / n;
    const f = f0 * Math.pow(f1 / f0, x);
    const F = 2 * Math.sin(Math.PI * Math.min(f, SR / 6) / SR);
    const hp = noise() - low - band / q * 1;
    band += F * hp; low += F * band;
    const env = shape === 'hump' ? Math.pow(Math.sin(Math.PI * x), 1.6)
      : shape === 'rise' ? Math.pow(x, 2.2) * (x > .97 ? (1 - x) / .03 : 1)
      : Math.pow(1 - x, 2);
    put(s + k, band * env * lvl, pan0 + (pan1 - pan0) * x, send);
  }
}
function impact(t0, lvl = .6) {
  const s = Math.floor(t0 * SR); let ph = 0, lp = 0;
  for (let k = 0; k < SR * 2.2; k++) {
    const tt = k / SR;
    ph += TAU * (36 + 70 * Math.exp(-tt * 9)) / SR;
    const sub = Math.sin(ph) * Math.exp(-tt * 2.2) * Math.min(1, tt / .003);
    const c = .04 + .5 * Math.exp(-tt * 6);
    lp += c * (noise() - lp);
    const crash = lp * Math.exp(-tt * 3.2) * 1.4;
    put(s + k, (sub * .9 + crash * .5) * lvl, 0, .5);
  }
}
function tick(t0, lvl = .08, f = 3800) {
  const s = Math.floor(t0 * SR); let low = 0, band = 0; const F = 2 * Math.sin(Math.PI * f / SR);
  for (let k = 0; k < SR * .012; k++) {
    const hp = noise() - low - band / 3; band += F * hp; low += F * band;
    put(s + k, band * Math.exp(-k / SR * 500) * lvl, (rnd() - .5) * .5, .05);
  }
}
function pad(t0, t1, notes, lvl = .03) {
  const s = Math.floor(t0 * SR), e = Math.floor(t1 * SR);
  for (const m of notes) for (const det of [-.07, .07]) {
    const f = mtof(m + det); const ph0 = rnd() * TAU;
    for (let k = s; k < e + SR * .6 && k < N; k++) {
      const tt = (k - s) / SR, rel = (k - e) / SR;
      const env = Math.min(1, tt / .45) * (rel > 0 ? Math.max(0, 1 - rel / .6) : 1);
      const x = TAU * f * tt + ph0;
      const v = Math.sin(x) + .28 * Math.sin(2 * x) + .12 * Math.sin(3 * x);
      put(k, v * env * lvl * duck(k / SR), det < 0 ? -.35 : .35, .35);
    }
  }
}
function bass(t0, t1, m, lvl = .16) {
  const f = mtof(m); const s = Math.floor(t0 * SR), e = Math.floor(t1 * SR);
  for (let k = s; k < e && k < N; k++) {
    const tt = (k - s) / SR, left = (e - k) / SR;
    const env = Math.min(1, tt / .02) * Math.min(1, left / .05);
    put(k, Math.sin(TAU * f * tt) * env * lvl * duck(k / SR));
  }
}

/* ---------- timeline ---------- */
const KICKS = []; for (let t = 2.4; t <= 12.21; t += .7) KICKS.push(+t.toFixed(3));
function duck(t) { // sidechain feel
  let d = 1;
  for (const k of KICKS) if (t >= k && t < k + .4) d = Math.min(d, 1 - .55 * Math.exp(-(t - k) * 9));
  return d;
}
// chords: Am  F  C  G  -> Cadd9
const CH = [
  [0.0, 3.1, [57, 60, 64, 69], 45],
  [3.1, 5.9, [53, 57, 60, 65], 41],
  [5.9, 8.7, [55, 60, 64, 67], 48],
  [8.7, 12.2, [55, 59, 62, 67], 43],
  [12.2, 15, [60, 64, 67, 74, 72], 48],
];
CH.forEach(([a, b, notes, root], i) => {
  pad(a, b, notes, i === 0 ? .022 : i === 4 ? .03 : .026);
  if (a >= 2.4 && i < 4) for (let t = Math.max(a, 2.4); t < b - .01; t += .35) bass(t, t + .3, root - 12, .15);
});
bass(12.2, 15, 36, .13);

// intro
sweep(0, .65, 300, 5000, .5, { shape: 'rise', pan0: -.4, pan1: .4 });
impact(.65, .32);
[.1, .22, .36].forEach(t => tick(t, .05, 2400));
for (let i = 0; i < 7; i++) tick(.55 + i * .035, .06, 1800);
for (let i = 0; i < 6; i++) tick(.74 + i * .035, .05, 2200);
[1.0, 1.35, 1.7, 2.05].forEach(t => hat(t, .03));
sweep(1.95, .5, 600, 6000, .32, { pan0: .5, pan1: -.5 }); // hook exits

// core appears
impact(2.4, .45); bell(2.4, mtof(81), .12);
KICKS.forEach((t, i) => kick(t, t < 4.5 ? .42 : .55));
// card
sweep(2.65, .45, 400, 3000, .28, { pan0: -.2, pan1: .2 });
for (let r = 0; r < 3; r++) for (let c = 0; c < 10; c++) tick(3.1 + r * .3 + c * .034 + rnd() * .008, .05 + rnd() * .03, 3000 + rnd() * 1500);
// absorb
sweep(4.0, .5, 300, 7000, .38, { shape: 'rise' });
impact(4.5, .5); bell(4.5, mtof(76), .12);
sweep(4.5, .55, 2000, 500, .18, { pan0: .6, pan1: -.6 }); // track draws

// S3 hats + arp
for (let t = 4.85; t < 11.9; t += .7) hat(t, .045, .25);
for (let t = 5.2; t < 11.9; t += .7) hat(t + .175, .02, -.25);
const ARP = { 3.1: [65, 69, 72, 77], 5.9: [67, 72, 76, 79], 8.7: [67, 71, 74, 79] };
let ai = 0;
for (let t = 4.5; t < 11.85; t += .175, ai++) {
  const key = t < 5.9 ? 3.1 : t < 8.7 ? 5.9 : 8.7;
  const seq = ARP[key];
  pluck(t, mtof(seq[[0, 2, 1, 3, 2, 1][ai % 6]]), .035, ai % 2 ? .45 : -.45);
}
// node activations: arc whoosh + bell
const ACT = [5.2, 6.6, 8.0, 9.4], NOTES = [76, 79, 81, 84];
ACT.forEach((t, i) => {
  if (i > 0) sweep(t - .45, .45, 800, 4000, .2, { pan0: -.3, pan1: .3 });
  bell(t, mtof(NOTES[i]), .15, [0, .4, 0, -.4][i]);
  tick(t, .08, 5000);
});
// loop
sweep(10.8 - .05, .4, 800, 4000, .2);
bell(10.8, mtof(88), .1);
bell(11.15, mtof(88), .13); bell(11.15, mtof(81), .1);
sweep(11.15, .7, 400, 9000, .45, { shape: 'rise', pan0: -.6, pan1: .6 });
for (let i = 0; i < 8; i++) tick(11.15 + i * .085, .05 + i * .006, 4000 + i * 300);
// exit + wipe
sweep(11.85, .38, 5000, 300, .25);
impact(12.2, .75);
bell(12.2, mtof(72), .1); bell(12.2, mtof(79), .08);
// end card
[0, 1, 2, 3].forEach(i => kick(12.55 + i * .05, .16));
sweep(12.85, .7, 3000, 9000, .1, { pan0: -.5, pan1: .5 }); // SCALE shimmer
bell(12.9, mtof(84), .06, -.3);
tick(13.25, .08, 2600);
bell(13.6, mtof(88), .12, .2); bell(13.62, mtof(91), .06, -.2);
bell(13.95, mtof(96), .035);

/* ---------- reverb (Schroeder) ---------- */
function reverb(input, delays, ap) {
  const out = new Float32Array(N);
  for (const d of delays) {
    const buf = new Float32Array(d); let idx = 0, lp = 0;
    for (let i = 0; i < N; i++) {
      const y = buf[idx];
      lp = y * .65 + lp * .35;
      buf[idx] = input[i] + lp * .82;
      idx = (idx + 1) % d;
      out[i] += y / delays.length;
    }
  }
  for (const d of ap) {
    const buf = new Float32Array(d); let idx = 0;
    for (let i = 0; i < N; i++) {
      const b = buf[idx]; const y = -out[i] + b;
      buf[idx] = out[i] + b * .5; idx = (idx + 1) % d; out[i] = y;
    }
  }
  return out;
}
const wl = reverb(SEND, [1693, 1759, 1623, 1548], [245, 605]);
const wr = reverb(SEND, [1721, 1789, 1601, 1577], [251, 613]);

/* ---------- master ---------- */
const outL = new Float32Array(N), outR = new Float32Array(N);
let peak = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  const fade = Math.min(1, t / .01) * Math.min(1, (DUR - t) / .6);
  outL[i] = Math.tanh((L[i] + wl[i] * .55) * 1.3) * fade;
  outR[i] = Math.tanh((Rr[i] + wr[i] * .55) * 1.3) * fade;
  peak = Math.max(peak, Math.abs(outL[i]), Math.abs(outR[i]));
}
const g = .89 / peak;
const buf = Buffer.alloc(44 + N * 4);
buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 4, 4); buf.write('WAVE', 8);
buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22);
buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
buf.write('data', 36); buf.writeUInt32LE(N * 4, 40);
for (let i = 0; i < N; i++) {
  buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, outL[i] * g)) * 32767), 44 + i * 4);
  buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, outR[i] * g)) * 32767), 46 + i * 4);
}
fs.mkdirSync('out', { recursive: true });
fs.writeFileSync('out/trilha.wav', buf);
console.log('out/trilha.wav written, peak gain', g.toFixed(3));
