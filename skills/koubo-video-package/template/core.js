/* v3: stronger motion. Every value is a pure function of output time; scene times are source-clip seconds. */
const {edl, face, frames, assets, fps, beat} = DATA;
let acc = 0; const segs = edl.map(([a, b]) => { const s = {a, b, o: acc}; acc += b - a; return s; });
const TOTAL = acc;
const S = (t) => { for (const s of segs) { if (t <= s.b) return s.o + Math.max(0, t - s.a); } return TOTAL; };
const clamp = (p) => Math.min(1, Math.max(0, p));
const ease = (p) => 1 - Math.pow(1 - clamp(p), 3);
const back = (p, c = 2.0) => { const x = clamp(p) - 1; return 1 + (c + 1) * x * x * x + c * x * x; };
const LAYOUT = {
  full: {x: 0, y: 0, w: 1080, h: 1920, r: 0, dw: 1440, ax: .5, ay: .45},
  half: {x: 48, y: 930, w: 984, h: 740, r: 40, dw: 1010, ax: .5, ay: .46},
  avatar: {x: 716, y: 1190, w: 330, h: 330, r: 165, dw: 500, ax: .5, ay: .48},
};
const FILE = (txt) => `<div class="bar"><span>●</span>${txt}</div>`;
const huge = (t, top, size, html, extra = '') => `<div class="huge big" style="top:${top}px;font-size:${size}px;${extra}" data-t="${t}">${html}</div>`;
