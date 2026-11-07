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
const expo = (p) => { p = clamp(p); return p === 1 ? 1 : 1 - Math.pow(2, -10 * p); };
const inout = (p) => { p = clamp(p); return p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const BOUNDS = SCENES.slice(1).map((s) => s.o);
const facesAt = (i) => {
  const k = Math.max(0, Math.min(face.pts.length - 1, Math.round(i / face.step)));
  let sx = 0, sy = 0, n = 0; for (let j = k - 4; j <= k + 4; j++) { const f = face.pts[j]; if (f) { sx += f[0]; sy += f[1]; n++; } }
  return n ? [sx / n, sy / n] : [.42, .45];
};
const box = (name, fx, fy, zoom) => {
  const L = LAYOUT[name], dw = L.dw * zoom, dh = dw * 4 / 3;
  const ox = Math.min(0, Math.max(L.w - dw, L.w * L.ax - fx * dw));
  const oy = Math.min(name === 'half' ? 200 : 0, Math.max(L.h - dh, L.h * L.ay - fy * dh));
  return {...L, dw, dh, ox, oy};
};
const pulseAt = (t) => { if (!beat) return 0; const k = (t - beat.phase) / beat.period; const d = (k - Math.floor(k)) * beat.period; return Math.exp(-d * 9); };
const barPulse = (t) => { if (!beat) return 0; const p = beat.period * 2; const k = (t - beat.phase) / p; return Math.exp(-(k - Math.floor(k)) * p * 8); };
function reveal(it, t) {
  const x = (t - it.o), el = it.el;
  if (it.u !== null && t >= it.u) { const q = clamp((t - it.u) / 0.25); el.style.opacity = 1 - q; el.style.filter = `blur(${q * 14}px)`; return; }
  const b = el.dataset.base || '';
  const dur = it.kind === 'slam' ? 0.55 : 0.45, q = expo(x / dur);
  el.style.opacity = clamp(x / (dur * 0.6));
  el.style.filter = q < 1 ? `blur(${(1 - q) * (it.kind === 'slam' ? 18 : 12)}px)` : '';
  const rise = it.kind === 'row' ? 30 : it.kind === 'card' ? 60 : 24;
  const sc = it.kind === 'slam' ? lerp(1.08, 1, q) : lerp(0.96, 1, q);
  el.style.transform = `${b} translateY(${(1 - q) * rise}px) scale(${sc})`;
}
window.EVENTS = () => ({
  scenes: SCENES.map((s) => s.o),
  slams: [],
  pops: SCENES.flatMap((s) => s.items.filter((i) => (i.kind === 'card' || i.kind === 'slam') && i.o > s.o + 0.05).map((i) => i.o)),
  wipes: [...SCENES.slice(1).filter((s, n) => s.p !== SCENES[n].p).map((s) => s.o), ...CHAPTERS.map((c) => c.o)],
  chapters: CHAPTERS.map((c) => c.o),
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
  const punch = 0;
  const zoom = push;
  const [fx, fy] = facesAt(i);
  const A = box(prev.p, fx, fy, zoom), Z = box(scene.p, fx, fy, zoom), p = cur === 0 ? 1 : inout(local / 0.55), v = (k) => lerp(A[k], Z[k], p);
  const toHalf = scene.p === 'half', fromHalf = prev.p === 'half' && cur > 0;
  const ext = lerp(fromHalf ? 320 : 0, toHalf ? 320 : 0, clamp(p));
  const bob = 0;
  Object.assign(person.style, {left: v('x') + 'px', top: v('y') + bob + 'px', width: v('w') + 'px', height: v('h') + 'px', borderRadius: Math.max(0, v('r')) + 'px',
    background: toHalf || (fromHalf && local < 0.1) ? '#FFE9A0' : '#222', boxShadow: scene.p === 'full' ? 'none' : scene.p === 'avatar' ? '0 0 0 5px rgba(255,255,255,.95), 0 24px 50px rgba(60,40,0,.32)' : '0 30px 60px rgba(60,40,0,.25)'});
  Object.assign(img.style, {left: v('ox') + 'px', top: v('oy') + 'px', width: v('dw') + 'px', height: v('dh') + 'px',
    opacity: toHalf ? 0 : (fromHalf && local < 0.1 ? 0 : 1)});
  const curCut = !!scene.cut || toHalf, prevCut = cur > 0 && (!!prev.cut || fromHalf);
  const cutOp = curCut ? 1 : (prevCut ? (local < 0.1 ? 1 : 0) : 0);
  Object.assign(cutBox.style, {left: v('x') + 'px', top: v('y') - ext + 'px', width: v('w') + 'px', height: v('h') + ext + 'px', opacity: cutOp, display: cutOp > 0 ? 'block' : 'none'});
  Object.assign(cimg.style, {left: v('ox') + 'px', top: v('oy') + ext + 'px', width: v('dw') + 'px', height: v('dh') + 'px'});
  scene.el.style.opacity = 1;
  const drift = 1 + 0.025 * prog;
  scene.el.style.transform = scene.p === 'full' ? '' : `scale(${drift}) translateY(${-14 * prog}px)`;
  scene.el.style.transformOrigin = '50% 30%';
  scene.items.forEach((it) => reveal(it, t));
  scene.strikes.forEach(({el, o}) => { el.style.transform = `scaleX(${ease((t - o) / 0.16)})`; });
  scene.marks.forEach(({el, o}) => { el.style.background = t >= o ? 'rgba(255,227,110,.9)' : 'transparent'; });
  
  let d = 9; for (const o of BOUNDS) d = Math.min(d, Math.abs(t - o));
  const bl = Math.max(0, 1 - d / 0.2);
  world.style.filter = bl > 0 ? `blur(${(bl * bl) * 16}px) brightness(${1 + bl * 0.06})` : '';
  world.style.transform = '';
  wipe.style.visibility = 'hidden';
  // Chapter slam: yellow panel with a huge number.
  const ch = CHAPTERS.find((c) => t >= c.o - 0.25 && t < c.o + 0.85);
  if (ch) {
    const u = t - ch.o + 0.25, enter = expo(u / 0.35), leave = inout((u - 0.8) / 0.3);
    flash.style.visibility = 'visible'; flash.style.opacity = enter * (1 - leave); flash.style.transform = '';
    $('fnum').textContent = ch.num; $('fname').textContent = ch.name;
    $('fnum').style.transform = `translateY(${(1 - enter) * 40}px) scale(${lerp(1.06, 1, enter)})`;
    $('fnum').style.filter = `blur(${(1 - enter) * 16}px)`;
  } else flash.style.visibility = 'hidden';
  let seen = ''; for (let n = 0; n <= cur; n++) if (SCENES[n].ch) seen = SCENES[n].ch;
  if (scene.at >= 49 || scene.p === 'full') seen = '';
  chEl.style.display = seen ? 'block' : 'none'; chEl.textContent = seen;
  const sub = SUBS.find((x) => t >= x.a && t < x.b);
  const html = sub ? sub.t + (sub.en ? `<span class="en">${sub.en}</span>` : '') : '';
  if (subEl.innerHTML !== html) subEl.innerHTML = html;
  subEl.className = (sub && sub.t.replace(/<[^>]+>/g, '').length > 14 ? 'long' : '') + (scene.p === 'avatar' ? ' dark' : '');
  const sq = sub ? expo((t - sub.a) / 0.25) : 1; subEl.style.opacity = sq; subEl.style.filter = sq < 1 ? `blur(${(1 - sq) * 8}px)` : ''; subEl.style.transform = `translateY(${(1 - sq) * 10}px)`;
  const n5 = String(i + 1).padStart(5, '0'), jobs = [];
  const src = `file://${DATA.framesDir}/f_${n5}.jpg`;
  if (img.getAttribute('src') !== src) { img.src = src; jobs.push(img.decode()); }
  if (cutOp > 0) { const cs = `file://${DATA.cutDir}/c_${n5}.png`; if (cimg.getAttribute('src') !== cs) { cimg.src = cs; jobs.push(cimg.decode()); } }
  await Promise.all(jobs);
};
