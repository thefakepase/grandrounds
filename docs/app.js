/* Grand Rounds: static front-end. State lives in localStorage only. */
(() => {
const $ = s => document.querySelector(s);
const app = $('#app');
const ROLES = {
  md: ['Physician', 'var(--md)'], res: ['Resident', 'var(--res)'], stu: ['Med student', 'var(--stu)'],
  rn: ['Nurse', 'var(--rn)'], rx: ['Pharmacist', 'var(--rx)'], ems: ['EMS', 'var(--ems)'],
  hn: ['Hacker News', 'var(--hn)'], oth: ['Community', 'var(--oth)'],
};
const CLIN = ['md', 'res', 'stu', 'rn', 'rx', 'ems'];
const STANCE = { strong_rec: 'Strongly recommends', rec: 'Recommends', reference: 'Cites', critical: 'Critical', joke: 'Joke' };

/* ---------- storage (never trusted to exist) ---------- */
const store = {
  get(k, d) { try { const v = localStorage.getItem('gr:' + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('gr:' + k, JSON.stringify(v)); } catch {} },
};
let liked = store.get('liked', []), later = store.get('later', []), history = store.get('history', []);
const save = () => { store.set('liked', liked); store.set('later', later); store.set('history', history); };

/* ---------- theme ---------- */
const applyTheme = t => { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; };
applyTheme(store.get('theme', null));
$('#themeBtn').onclick = () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  const t = dark ? 'light' : 'dark'; applyTheme(t); store.set('theme', t);
};
$('#menuBtn').onclick = () => {
  if (matchMedia('(max-width: 820px)').matches) document.body.classList.toggle('open');
  else document.body.classList.toggle('collapsed');
};

/* ---------- data ---------- */
let DB, BY = {}, CAT = {}, MENTIONS = null;
const ready = fetch('data/videos.json', { cache: 'no-cache' }).then(r => r.json()).then(d => {
  DB = d;
  d.videos.forEach((v, i) => { v.i = i; BY[v.vid] = v; });
  d.areas.forEach(a => a.cats.forEach(c => { CAT[c.id] = { ...c, area: a.name, n: 0 }; }));
  d.videos.forEach(v => v.cat.forEach(c => CAT[c] && CAT[c].n++));
});
const loadMentions = () => MENTIONS ? Promise.resolve(MENTIONS)
  : fetch('data/mentions.json', { cache: 'no-cache' }).then(r => r.json()).then(m => (MENTIONS = m));

/* ---------- helpers ---------- */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtDur = s => { if (!s) return ''; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}` : `${m}:${String(x).padStart(2, '0')}`; };
const fmtNum = n => n >= 1e6 ? (n / 1e6).toFixed(1).replace('.0', '') + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'K' : String(n);
const clin = v => CLIN.reduce((a, k) => a + (v.r[k] || 0), 0);
const total = v => Object.values(v.r).reduce((a, b) => a + b, 0);
const thumb = vid => `https://i.ytimg.com/vi/${vid}/hq2.jpg`;
const toast = msg => { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 1600); };

function strip(v) {
  const tot = total(v) || 1;
  return `<span class="strip" title="${Object.entries(v.r).filter(e => e[1]).map(([k, n]) => `${ROLES[k][0]}: ${n}`).join(' · ')}">${
    Object.keys(ROLES).filter(k => v.r[k]).map(k => `<i style="width:${v.r[k] / tot * 100}%;background:${ROLES[k][1]}"></i>`).join('')}</span>`;
}
function vitalsLine(v) {
  const c = clin(v), h = v.r.hn || 0, bits = [];
  if (c) bits.push(`${c} clinician${c > 1 ? 's' : ''}`);
  if (h) bits.push(`${h} HN`);
  if (!c && !h && v.r.oth) bits.push(`${v.r.oth} people`);
  return `<div class="vitals">${strip(v)}<span>${bits.join(' + ')}</span>${v.views ? `<span>· ${fmtNum(v.views)} views</span>` : ''}</div>`;
}
function card(v, k = 0) {
  return `<a class="card" href="#/v/${v.vid}" style="animation-delay:${Math.min(k, 16) * 30}ms">
    <div class="thumb"><img loading="lazy" src="${thumb(v.vid)}" alt="">${v.dur ? `<span class="dur">${fmtDur(v.dur)}</span>` : ''}${v.crit >= 2 ? '<span class="tag-crit">DEBATED</span>' : ''}</div>
    <div class="meta"><h3>${esc(v.t)}</h3><div class="ch">${esc(v.ch)}</div>${vitalsLine(v)}</div></a>`;
}
function gridPaged(list, head, chips = '') {
  let shown = 0; const PAGE = 36;
  app.innerHTML = `${head}${chips}<div class="grid" id="grid"></div><button class="btn more" id="more">Show more</button>`;
  const more = () => {
    $('#grid').insertAdjacentHTML('beforeend', list.slice(shown, shown + PAGE).map(card).join(''));
    shown += PAGE; $('#more').style.display = shown >= list.length ? 'none' : '';
  };
  $('#more').onclick = more; more();
  if (!list.length) $('#grid').outerHTML = '<p class="empty">Nothing here yet.</p>';
}
const head = (h, p = '') => `<div class="page-head"><h1>${h}</h1>${p ? `<p>${p}</p>` : ''}</div>`;

/* ---------- recommendations: sampled from score, nudged by what you liked/watched ---------- */
function forYou() {
  const seen = new Set(history.map(h => h.vid));
  const prof = {};
  const bump = (vid, w) => { const v = BY[vid]; if (!v) return; v.cat.forEach(c => prof[c] = (prof[c] || 0) + w); };
  liked.forEach(id => bump(id, 3)); history.slice(0, 40).forEach(h => bump(h.vid, 1));
  const relBoost = {};
  [...liked, ...history.slice(0, 15).map(h => h.vid)].forEach(id => (BY[id]?.rel || []).forEach(r => relBoost[r] = (relBoost[r] || 0) + 1));
  const day = Math.floor(Date.now() / 864e5); let seed = day;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const pmax = Math.max(1, ...Object.values(prof));
  return DB.videos.filter(v => !seen.has(v.vid) && v.shelf !== 'news')
    .map(v => {
      const affinity = v.cat.reduce((a, c) => a + (prof[c] || 0), 0) / pmax;
      const w = Math.log(1 + v.sc) * (1 + affinity * 1.5 + (relBoost[v.vid] || 0) * 0.8) * (1 + clin(v) * 0.05);
      return [v, Math.pow(rnd(), 1 / w)];
    })
    .sort((a, b) => b[1] - a[1]).map(x => x[0]);
}

/* ---------- views ---------- */
const views = {
  home() {
    const areaChips = DB.areas.map(a => `<button class="chip" data-area="${a.id}">${esc(a.name)}</button>`).join('');
    const list = forYou();
    const intro = head('For <em>you</em>', `${DB.videos.length.toLocaleString()} videos that people in medicine keep recommending to each other. No account, no tracking: your likes and history stay in this browser.`);
    const show = a => {
      const ids = a ? new Set(DB.areas.find(x => x.id === a).cats.map(c => c.id)) : null;
      gridPaged(ids ? list.filter(v => v.cat.some(c => ids.has(c))) : list, intro,
        `<div class="chips"><button class="chip" data-area="">All</button>${areaChips}</div>`);
      document.querySelectorAll('.chip[data-area]').forEach(b => {
        b.classList.toggle('on', b.dataset.area === a);
        b.onclick = () => show(b.dataset.area);
      });
    };
    show('');
  },
  top() { gridPaged([...DB.videos].sort((a, b) => b.sc - a.sc), head('Most <em>recommended</em>', 'Ranked by how many separate months people in medicine recommended the video. Working clinicians count a bit more than students, enthusiastic recommendations count extra.')); },
  doctors() {
    gridPaged(DB.videos.filter(v => clin(v) >= 2).sort((a, b) => (b.r.md || 0) + (b.r.res || 0) - (a.r.md || 0) - (a.r.res || 0) || b.sc - a.sc),
      head("Clinicians' <em>picks</em>", 'Recommended by at least two people whose flair says they work in medicine, physicians and residents first.'));
  },
  long() { gridPaged(DB.videos.filter(v => v.dur >= 2400 || ['lecture', 'course', 'talk', 'documentary'].includes(v.ct) && !v.dur).sort((a, b) => b.sc - a.sc), head('Long <em>watches</em>', 'Lectures, grand rounds, courses and documentaries. Forty minutes and up.')); },
  liked() { gridPaged(liked.map(id => BY[id]).filter(Boolean), head('<em>Liked</em>')); },
  later() { gridPaged(later.map(id => BY[id]).filter(Boolean), head('Watch <em>later</em>')); },
  history() { gridPaged(history.map(h => BY[h.vid]).filter(Boolean), head('<em>History</em>', history.length ? '<button class="btn" id="clearH">Clear history</button>' : ''));
    const c = $('#clearH'); if (c) c.onclick = () => { history = []; save(); route(); }; },
  categories() {
    app.innerHTML = head('Specialties', 'Every video sits in one to three of these.') + `<div class="areas">${DB.areas.map(a => `<section class="area"><h2>${esc(a.name)}</h2>${
      a.cats.filter(c => CAT[c.id].n).sort((x, y) => CAT[y.id].n - CAT[x.id].n).map(c => `<a href="#/c/${c.id}" title="${esc(c.desc || '')}">${esc(c.name)}<span>${CAT[c.id].n}</span></a>`).join('')}</section>`).join('')}</div>`;
  },
  cat(id) { const c = CAT[id]; if (!c) return views.notfound();
    gridPaged(DB.videos.filter(v => v.cat.includes(id)).sort((a, b) => b.sc - a.sc), head(esc(c.name), esc(c.desc || c.area))); },
  search(q) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const scored = DB.videos.map(v => {
      const hay = [v.t, v.ch, v.s, v.w, (v.tags || []).join(' '), v.cat.map(c => CAT[c]?.name).join(' ')].join(' ').toLowerCase();
      let s = 0; for (const t of terms) { if (!hay.includes(t)) return null; s += (v.t.toLowerCase().includes(t) ? 3 : 1); }
      return [v, s + Math.log(1 + v.sc)];
    }).filter(Boolean).sort((a, b) => b[1] - a[1]).map(x => x[0]);
    gridPaged(scored, head(`“${esc(q)}”`, `${scored.length} result${scored.length === 1 ? '' : 's'}`));
  },
  async video(vid) {
    const v = BY[vid]; if (!v) return views.notfound();
    history = [{ vid, at: Date.now() }, ...history.filter(h => h.vid !== vid)].slice(0, 300); save();
    const isL = liked.includes(vid), isW = later.includes(vid);
    const rel = (v.rel || []).map(r => BY[r]).filter(Boolean);
    const fill = rel.length < 12 ? DB.videos.filter(x => x !== v && !v.rel?.includes(x.vid) && x.cat[0] === v.cat[0]).slice(0, 12 - rel.length) : [];
    app.innerHTML = `<div class="watch"><div>
      <div class="player"><iframe src="https://www.youtube-nocookie.com/embed/${vid}?rel=0" title="${esc(v.t)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>
      <h1>${esc(v.t)}</h1>
      <div class="row"><span class="channel">${esc(v.ch)}</span>
        <button class="btn ${isL ? 'on' : ''}" id="likeB"><svg viewBox="0 0 24 24"><path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/></svg>Like</button>
        <button class="btn ${isW ? 'on' : ''}" id="laterB"><svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4-6 4z"/></svg>Later</button>
        <a class="btn" href="https://www.youtube.com/watch?v=${vid}" target="_blank" rel="noopener">YouTube ↗</a></div>
      <div class="chart">
        ${v.w ? `<p class="why">${esc(v.w)}</p>` : ''}
        ${v.s ? `<p>${esc(v.s)}</p>` : ''}
        <div class="legend">${Object.keys(ROLES).filter(k => v.r[k]).map(k => `<span><i style="background:${ROLES[k][1]}"></i>${ROLES[k][0]} ${v.r[k]}</span>`).join('')}${v.crit ? `<span style="color:var(--ecg)">● critical ${v.crit}</span>` : ''}</div>
        <div class="kv">${v.ct ? `<span>type <b>${esc(v.ct)}</b></span>` : ''}${v.lv ? `<span>level <b>${esc(v.lv)}</b></span>` : ''}<span>recommended <b>${v.y0 === v.y1 ? v.y0 : v.y0 + '–' + v.y1}</b></span>${v.dur ? `<span>length <b>${fmtDur(v.dur)}</b></span>` : ''}</div>
        <div class="kv">${v.cat.map(c => CAT[c] ? `<a href="#/c/${c}"><b>#${esc(CAT[c].name)}</b></a>` : '').join(' ')}</div>
      </div>
      <section class="consults"><h2>Consult notes</h2><div id="notes"><p class="empty">Loading…</p></div></section>
    </div>
    <aside class="side-list"><h2>Recommended by the same people</h2>${[...rel, ...fill].slice(0, 16).map(x => `<a class="mini" href="#/v/${x.vid}"><div class="thumb"><img loading="lazy" src="${thumb(x.vid)}" alt="">${x.dur ? `<span class="dur">${fmtDur(x.dur)}</span>` : ''}</div><div><h3>${esc(x.t)}</h3><div class="ch">${esc(x.ch)}</div>${vitalsLine(x)}</div></a>`).join('')}</aside></div>`;
    $('#likeB').onclick = e => { liked = liked.includes(vid) ? liked.filter(x => x !== vid) : [vid, ...liked]; save(); e.currentTarget.classList.toggle('on'); toast(liked.includes(vid) ? 'Liked: your feed will lean this way' : 'Removed from liked'); };
    $('#laterB').onclick = e => { later = later.includes(vid) ? later.filter(x => x !== vid) : [vid, ...later]; save(); e.currentTarget.classList.toggle('on'); toast(later.includes(vid) ? 'Saved for later' : 'Removed'); };
    const m = (await loadMentions())[vid] || [];
    if (location.hash !== '#/v/' + vid) return;
    $('#notes').innerHTML = m.length ? m.map(x => `<div class="consult ${x.st === 'critical' ? 'critical' : ''}">
      <div class="who"><span class="role" style="background:${ROLES[x.role]?.[1] || 'var(--oth)'}">${ROLES[x.role]?.[0] || 'Community'}</span><span>${x.role === 'hn' ? 'news.ycombinator.com' : 'r/' + esc(x.sub)}</span><span>· ${esc(x.m)}</span><span class="stance">· ${STANCE[x.st] || ''}</span></div>
      <blockquote>${esc(x.q || x.tx)}</blockquote>
      ${x.url ? `<a class="src" href="${esc(x.url)}" target="_blank" rel="noopener">read in context ↗</a>` : ''}</div>`).join('')
      : '<p class="empty">No notes stored for this video.</p>';
  },
  about() {
    const st = DB.stats || {};
    app.innerHTML = `<article class="prose">
      <h1>About <em style="color:var(--accent)">Grand Rounds</em></h1>
      <p>YouTube's medical corner is a mix of excellent teaching and confident nonsense, and the algorithm cannot tell them apart. People who work in medicine can. For years they have been pointing each other to the good stuff in Reddit threads. This site collects those recommendations.</p>
      <div class="stats">${[['videos', DB.videos.length], ['comments read by Claude', st.mentions], ['subreddits', st.subs], ['years covered', st.years]].filter(x => x[1]).map(([k, n]) => `<div class="stat"><b>${typeof n === 'number' ? n.toLocaleString() : n}</b><span>${k}</span></div>`).join('')}</div>
      <h2>How it was made</h2>
      <p>Every comment and post from ${st.subs || 'a set of'} medical subreddits (r/medicine, r/medicalschool, r/Residency, r/nursing, r/emergencymedicine and others, from the <a href="https://github.com/ArthurHeitmann/arctic_shift" target="_blank" rel="noopener">Arctic Shift</a> archive) was scanned for YouTube links. Claude read each one to tell recommendations apart from jokes, criticism and questions, and to label the topic. A video gets in when several different people recommended it. The role badge (physician, resident, student, nurse) comes from the commenter's Reddit flair or, when there is none, from the subreddit.</p>
      <p>The health and medicine videos from <a href="https://hackertube.org" target="_blank" rel="noopener">HackerTube</a> (Hacker News recommendations, ODC-By) are included too, shown in orange. When a clinician pushes back on a video, their note shows up in red on the video page.</p>
      <p>Thumbnails are YouTube's automatic frame from the middle of the video, not the uploader's clickbait. Titles, durations and view counts come from the YouTube Data API and are refreshed periodically. Your likes, history and "watch later" are stored only in this browser.</p>
      <h2>Not medical advice</h2>
      <p>A recommendation from a stranger with a "Physician" flair is a signal, not a guarantee. Flairs on Reddit are self-reported. Talk to your own doctor.</p>
      <h2>Data</h2>
      <p>Everything behind the site is one download: <a href="data/grandrounds-data.zip">grandrounds-data.zip</a>. Give it to your own AI agent and build your own version. Usernames are not included.</p>
      <p style="color:var(--ink-3);font-size:13px">Built in an afternoon with Claude, after <a href="https://karpathy.bearblog.dev/hacker-tube/" target="_blank" rel="noopener">HackerTube</a>. Not affiliated with YouTube, Reddit or Hacker News.</p>
    </article>`;
  },
  sample() {
    let seed = 20261104; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const pick = [...DB.videos].map(v => [v, rnd()]).sort((a, b) => a[1] - b[1]).slice(0, 50).map(x => x[0]);
    gridPaged(pick, head('Spot <em>check</em>', '50 videos drawn at random (fixed seed) to check the quality of the selection by hand.'));
  },
  notfound() { app.innerHTML = head('Not found', '<a href="#/" style="color:var(--accent)">Back home</a>'); },
};

/* ---------- router ---------- */
function route() {
  const h = decodeURIComponent(location.hash.slice(2));
  const [p, a] = [h.split('/')[0], h.split('/').slice(1).join('/')];
  document.querySelectorAll('.side a').forEach(x => x.classList.toggle('on', x.dataset.nav === (p || 'home') || (p === 'c' && x.dataset.nav === 'categories')));
  document.body.classList.remove('open');
  window.scrollTo(0, 0);
  const map = { '': 'home', top: 'top', doctors: 'doctors', long: 'long', liked: 'liked', later: 'later', history: 'history', categories: 'categories', about: 'about', sample: 'sample' };
  if (p === 'v') return views.video(a);
  if (p === 'c') return views.cat(a);
  if (p === 's') { $('#q').value = a; return views.search(a); }
  (views[map[p]] || views.notfound)();
}
$('#searchForm').onsubmit = e => { e.preventDefault(); const q = $('#q').value.trim(); if (q) location.hash = '#/s/' + encodeURIComponent(q); };
addEventListener('keydown', e => {
  if (e.target.matches('input,textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
  if (e.key === '/') { e.preventDefault(); $('#q').focus(); }
  else if (e.key === 'l' && location.hash.startsWith('#/v/')) $('#likeB')?.click();
  else if (e.key === 'w' && location.hash.startsWith('#/v/')) $('#laterB')?.click();
  else if (e.key === 'g') location.hash = '#/';
});
addEventListener('hashchange', route);
ready.then(route).catch(err => { app.innerHTML = `<p class="empty">Could not load data: ${esc(err.message)}</p>`; });
})();
