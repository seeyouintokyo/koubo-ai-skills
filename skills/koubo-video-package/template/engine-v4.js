const $ = (id) => document.getElementById(id);
const stage = $('stage'), frontEl = $('front'), world = $('world');
const kindOf = (el) => el.classList.contains('row') ? 'row' : el.classList.contains('chip') || el.classList.contains('sign') ? 'chip'
  : el.classList.contains('card') ? 'card' : (el.classList.contains('big') || el.classList.contains('mega') || el.classList.contains('huge')) ? 'slam'
  : el.classList.contains('wire') ? 'pop' : 'soft';
SCENES.forEach((s, n) => {
  s.o = S(s.at); s.end = n + 1 < SCENES.length ? S(SCENES[n + 1].at) : TOTAL;
  s.el = Object.assign(document.createElement('div'), {className: 'scene' + (s.p === 'full' ? ' top' : ''), innerHTML: s.html || ''});
  s.fel = Object.assign(document.createElement('div'), {className: 'fl', innerHTML: s.front || ''});
  stage.appendChild(s.el); frontEl.appendChild(s.fel);
  const all = [...s.el.querySelectorAll('[data-t]'), ...s.fel.querySelectorAll('[data-t]')];
  s.items = all.map((el, i) => ({el, o: S(+el.dataset.t), u: el.dataset.u ? S(+el.dataset.u) : null, kind: kindOf(el), side: i % 2 ? 1 : -1, tilt: i % 2 ? 2 : -2}));
  s.strikes = [...s.el.querySelectorAll('[data-strike]')].map((el) => ({el, o: S(+el.dataset.strike)}));
  s.marks = [...s.el.querySelectorAll('[data-mark]')].map((el) => ({el, o: S(+el.dataset.mark)}));
});
const KEYS = SCENES.flatMap((s) => s.items.filter((i) => i.kind === 'slam' || i.kind === 'chip').map((i) => i.o));
const CHAPTERS = SCENES.map((s, n) => ({s, n})).filter(({s, n}) => s.ch && (n === 0 || SCENES[n - 1].ch !== s.ch)).map(({s}) => ({o: s.o, num: s.ch.slice(0, 2), name: s.ch.slice(3)}));
const chapterAt = (o) => CHAPTERS.some((c) => Math.abs(c.o - o) < 1e-6);
const WIPES = SCENES.slice(1).filter((s, i) => (s.p === 'full') !== (SCENES[i].p === 'full') && !chapterAt(s.o)).map((s) => s.o);
const img = $('pimg'), person = $('person'), cutBox = $('cut'), cimg = $('cimg');
const subEl = $('sub'), chEl = $('chapter'), wipe = $('wipe'), flash = $('flash');
const lerp = (a, b, p) => a + (b - a) * p;
// Damped oscillation after an impact (idea from video-shotcraft motion helpers, Apache-2.0).
const settle = (d, freq, damp) => d <= 0 ? 0 : Math.exp(-damp * d) * Math.sin(2 * Math.PI * freq * d);
const FULLCUTS = SCENES.slice(1).filter((s, n) => s.p === 'full' && SCENES[n].p === 'full').map((s) => s.o);
const facesAt = (i) => {
  const k = Math.max(0, Math.min(face.pts.length - 1, Math.round(i / face.step)));
  let sx = 0, sy = 0, n = 0; for (let j = k - 4; j <= k + 4; j++) { const f = face.pts[j]; if (f) { sx += f[0]; sy += f[1]; n++; } }
  return n ? [sx / n, sy / n] : [.42, .45];
};
const box = (name, fx, fy, zoom) => {
  const L = LAYOUT[name], dw = L.dw * zoom, dh = dw * (DATA.aspect || 4 / 3);
  const ox = Math.min(0, Math.max(L.w - dw, L.w * L.ax - fx * dw));
  const oy = Math.min(name === 'half' ? 200 : 0, Math.max(L.h - dh, L.h * L.ay - fy * dh));
  return {...L, dw, dh, ox, oy};
};
const pulseAt = (t) => { if (!beat) return 0; const k = (t - beat.phase) / beat.period; const d = (k - Math.floor(k)) * beat.period; return Math.exp(-d * 9); };
const barPulse = (t) => { if (!beat) return 0; const p = beat.period * 2; const k = (t - beat.phase) / p; return Math.exp(-(k - Math.floor(k)) * p * 8); };
function reveal(it, t) {
  const x = (t - it.o), el = it.el;
  if (it.u !== null && t >= it.u) { el.style.opacity = 0; return; }
  const b = el.dataset.base || '';
  if (it.kind === 'slam') {
    const q = clamp(x / 0.16);
    const s = q < 1 ? lerp(2.4, 1, ease(q)) : 1 + 0.07 * settle(x - 0.16, 3.2, 7);
    el.style.opacity = clamp(x / 0.06); el.style.filter = q < 1 ? `blur(${(1 - q) * 10}px)` : ''; el.style.transform = `${b} scale(${s})`;
  } else if (it.kind === 'chip') {
    const q = clamp(x / 0.24); el.style.opacity = clamp(x / 0.05);
    el.style.transform = `${b} scale(${lerp(2, 1, back(q, 1.6))}) rotate(${lerp(it.tilt * 7, it.tilt, ease(q))}deg)`;
  } else if (it.kind === 'row') {
    const q = clamp(x / 0.32); el.style.opacity = x >= 0 ? 1 : 0; el.style.transform = `${b} translateX(${(1 - back(q, 1.3)) * it.side * 1180}px)`;
  } else if (it.kind === 'card') {
    const q = clamp(x / 0.36); el.style.opacity = x >= 0 ? 1 : 0; el.style.transform = `${b} translateY(${(1 - back(q, 1.2)) * 900}px) rotate(${(1 - ease(q)) * 5}deg)`;
  } else {
    const q = ease(x / 0.22); el.style.opacity = q; el.style.transform = `${b} translateY(${(1 - q) * 40}px) scale(${0.8 + 0.2 * back(clamp(x / 0.22))})`;
  }
}
window.EVENTS = () => ({
  chapters: CHAPTERS.map((c) => c.o),
  fullcuts: FULLCUTS,
  scenes: SCENES.map((s) => s.o),
  slams: SCENES.flatMap((s) => s.items.filter((i) => i.kind === 'slam').map((i) => i.o)),
  pops: SCENES.flatMap((s) => s.items.filter((i) => i.kind !== 'slam' && i.o > s.o + 0.05).map((i) => i.o)),
  wipes: [...WIPES, ...CHAPTERS.map((c) => c.o)],
});
window.DURATION = TOTAL; window.FPS = fps;
window.seek = async (t) => {
  const i = Math.min(frames - 1, Math.round(t * fps));
  let cur = 0; SCENES.forEach((s, n) => { if (t >= s.o) cur = n; });
  const scene = SCENES[cur], prev = SCENES[Math.max(0, cur - 1)];
  SCENES.forEach((s, n) => { const v = n === cur ? 'visible' : 'hidden'; s.el.style.visibility = v; s.fel.style.visibility = v; });
  const local = t - scene.o, dur = Math.max(.1, scene.end - scene.o), prog = clamp(local / dur);
  const pulse = barPulse(t), beatP = pulseAt(t);
  const push = scene.p === 'avatar' ? 1 : 1 + 0.06 * prog;
  const punch = scene.p === 'full' ? 0.1 * (1 - ease(local / 0.28)) : 0;
  // The camera footage only pushes in slowly; beat pulses and cut punches move the materials, not the room.
  const zoom = push;
  const [fx, fy] = facesAt(i);
  const A = box(prev.p, fx, fy, zoom), Z = box(scene.p, fx, fy, zoom), p = cur === 0 ? 1 : back(local / 0.3, 0.9), v = (k) => lerp(A[k], Z[k], p);
  const toHalf = scene.p === 'half', fromHalf = prev.p === 'half' && cur > 0;
  const ext = lerp(fromHalf ? 320 : 0, toHalf ? 320 : 0, clamp(p));
  const bob = scene.p === 'avatar' ? Math.sin(t * 2.6) * 7 : 0;
  // A still portrait in the avatar circle gets a pulsing ring so it does not look frozen.
  const ring = scene.still && scene.p === 'avatar' ? 0.5 + 0.5 * Math.sin(t * 5.2) : null;
  const shadow = scene.p === 'full' ? 'none' : ring === null ? '0 0 0 6px #17181A, 12px 12px 0 6px #17181A'
    : `0 0 0 6px #17181A, 0 0 0 ${12 + 14 * ring}px rgba(255,212,59,${0.95 - 0.55 * ring}), 12px 12px 0 6px #17181A`;
  // 'none' scenes hide the person once the shrink transition has finished.
  person.style.display = scene.p === 'none' && (cur === 0 || prev.p === 'none' || local > 0.3) ? 'none' : 'block';
  Object.assign(person.style, {left: v('x') + 'px', top: v('y') + bob + 'px', width: v('w') + 'px', height: v('h') + 'px', borderRadius: Math.max(0, v('r')) + 'px',
    background: toHalf || (fromHalf && local < 0.1) ? '#FFD43B' : '#222', boxShadow: shadow});
  Object.assign(img.style, {left: v('ox') + 'px', top: v('oy') + 'px', width: v('dw') + 'px', height: v('dh') + 'px',
    opacity: toHalf ? 0 : (fromHalf && local < 0.1 ? 0 : 1)});
  const curCut = !!scene.cut || toHalf, prevCut = cur > 0 && (!!prev.cut || fromHalf);
  const cutOp = curCut ? 1 : (prevCut ? (local < 0.1 ? 1 : 0) : 0);
  Object.assign(cutBox.style, {left: v('x') + 'px', top: v('y') - ext + 'px', width: v('w') + 'px', height: v('h') + ext + 'px', opacity: cutOp, display: cutOp > 0 ? 'block' : 'none'});
  Object.assign(cimg.style, {left: v('ox') + 'px', top: v('oy') + ext + 'px', width: v('dw') + 'px', height: v('dh') + 'px'});
  scene.el.style.opacity = 1;
  const drift = 1 + 0.03 * prog + 0.006 * beatP + 0.012 * pulse + punch * 0.6;
  scene.el.style.transform = `scale(${drift}) translateY(${-14 * prog}px)`;
  scene.el.style.transformOrigin = '50% 30%';
  scene.fel.style.transform = `scale(${1 + 0.012 * pulse + punch * 0.6})`;
  scene.fel.style.transformOrigin = '50% 30%';
  scene.items.forEach((it) => reveal(it, t));
  scene.strikes.forEach(({el, o}) => { el.style.transform = `scaleX(${ease((t - o) / 0.16)})`; });
  scene.marks.forEach(({el, o}) => { el.style.background = t >= o ? '#FFD43B' : 'transparent'; });
  $('bg').style.backgroundPosition = `${t * 18}px ${t * 30}px`;
  let sx = 0, sy = 0, zs = 0;
  for (const k of KEYS) { const d = t - k; if (d >= 0 && d < 0.5) { sx += 18 * settle(d, 9, 9); sy += 14 * settle(d + 0.03, 7, 9); zs = Math.max(zs, 0.03 * Math.exp(-d * 12)); } }
  if (scene.p === 'full') { sx += 3 * (Math.sin(t * 9.3) + 0.6 * Math.sin(t * 24.9 + 1.7)); sy += 3 * (Math.sin(t * 14.1 + 0.9) + 0.5 * Math.sin(t * 33.9 + 3.1)); }
  // Handheld jitter and impact shake move the materials layer only; the camera footage stays steady.
  world.style.transform = '';
  for (const el of [scene.el, scene.fel]) el.style.transform = `translate(${sx}px,${sy}px) ${el.style.transform} scale(${1 + zs})`;
  // Warm bloom over hard cuts between two full-screen shots.
  let fl = 0; for (const o of FULLCUTS) { const d = t - o + 0.06; if (d >= 0 && d < 0.3) fl = Math.max(fl, d < 0.12 ? d / 0.12 : 1 - (d - 0.12) / 0.18); }
  $('bloom').style.opacity = fl * 0.85;
  // Diagonal black wipe across layout changes.
  let w = null; for (const o of WIPES) { if (t >= o - 0.12 && t < o + 0.14) w = (t - o + 0.12) / 0.26; }
  if (w === null) { wipe.style.visibility = 'hidden'; } else {
    const a = ease(w * 1.9) * 150 - 25, c = ease((w - 0.42) * 1.9) * 150 - 25;
    wipe.style.visibility = 'visible';
    wipe.style.clipPath = `polygon(${c - 25}% 0,${a + 25}% 0,${a - 25}% 100%,${c - 75}% 100%)`;
  }
  // Chapter slam: yellow panel with a huge number.
  const ch = CHAPTERS.find((c) => t >= c.o - 0.1 && t < c.o + 0.62);
  if (ch) {
    const u = t - ch.o + 0.1, enter = ease(u / 0.14), leave = ease((u - 0.56) / 0.16);
    flash.style.visibility = 'visible'; flash.style.transform = `translateX(${(1 - enter) * 110 - leave * 110}%) skewX(${(1 - enter) * -12 + leave * 12}deg)`;
    $('fnum').textContent = ch.num; $('fname').textContent = ch.name;
    $('fnum').style.transform = `scale(${u < 0.18 ? lerp(1.8, 1, ease(u / 0.18)) : 1 + 0.08 * settle(u - 0.18, 3, 7)})`;
    flash.style.filter = enter < 1 || leave > 0 ? `blur(${(1 - enter + leave) * 6}px)` : '';
  } else flash.style.visibility = 'hidden';
  let seen = ''; for (let n = 0; n <= cur; n++) if (SCENES[n].ch) seen = SCENES[n].ch;
  if (scene.at >= (DATA.chEnd ?? 49) || scene.p === 'full' || scene.p === 'none') seen = '';
  chEl.style.display = seen ? 'block' : 'none'; chEl.textContent = seen;
  const sub = SUBS.find((x) => t >= x.a && t < x.b);
  const html = sub ? sub.t + (sub.en ? `<span class="en">${sub.en}</span>` : '') : '';
  if (subEl.innerHTML !== html) subEl.innerHTML = html;
  subEl.className = sub && sub.t.replace(/<[^>]+>/g, '').length > 14 ? 'long' : '';
  subEl.style.transform = sub ? `scale(${lerp(0.82, 1, back((t - sub.a) / 0.14, 2))})` : '';
  // Optional per-video animation hook (drawn graphics, counters, charts).
  const n5 = String(i + 1).padStart(5, '0'), jobs = [];
  if (typeof TICK === 'function') TICK(t, scene, jobs);
  const src = `file://${DATA.framesDir}/f_${n5}.jpg`;
  if (img.getAttribute('src') !== src) { img.src = src; jobs.push(img.decode()); }
  if (cutOp > 0) { const cs = `file://${DATA.cutDir}/c_${n5}.png`; if (cimg.getAttribute('src') !== cs) { cimg.src = cs; jobs.push(cimg.decode()); } }
  await Promise.all(jobs);
};
