/* Buscador compartido (index + páginas de lista): artista, álbum, canción y lista.
   Carga search-index.json (generado por tools/build_search.py) la primera vez que se abre. */
(function () {
  var DATA = null, LOADING = null, ART = null;
  var ICON = { 0: '🎵', 1: '💿' };

  function norm(s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function load() {
    if (DATA) return Promise.resolve(DATA);
    if (LOADING) return LOADING;
    LOADING = fetch('search-index.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) {
      d.i.forEach(function (it) { it.n = norm(it[0] + ' ' + it[1]); it.na = norm(it[0]); it.nt = norm(it[1]); });
      d.f.forEach(function (f) { f.n = norm(f[1] + ' ' + f[2] + ' ' + f[5]); });
      var map = {};
      d.i.forEach(function (it, idx) {
        var m = map[it.na] || (map[it.na] = { name: it[0], items: [], lists: {} });
        m.items.push(idx);
        it[3].forEach(function (p) { m.lists[p[0]] = 1; });
      });
      ART = Object.keys(map).map(function (k) { var m = map[k]; m.key = k; m.nl = Object.keys(m.lists).length; return m; })
        .sort(function (a, b) { return b.nl - a.nl; });
      DATA = d; return d;
    }).catch(function () { LOADING = null; return null; });
    return LOADING;
  }

  function all(tokens, s) { for (var i = 0; i < tokens.length; i++) if (s.indexOf(tokens[i]) < 0) return false; return true; }
  function rank(it, q) { // menor = mejor
    if (it.nt === q || it.na === q) return 0;
    if (it.nt.indexOf(q) === 0 || it.na.indexOf(q) === 0) return 1;
    return 2;
  }

  function listsHTML(it) {
    var rows = it[3].slice().sort(function (a, b) { return a[1] - b[1]; }).slice(0, 15).map(function (p) {
      var f = DATA.f[p[0]];
      return '<a class="sp-lk" href="' + esc(f[0]) + '">#' + p[1] + ' · ' + esc(f[1]) + '</a>';
    });
    if (it[3].length > 15) rows.push('<span class="sp-more">y ' + (it[3].length - 15) + ' listas más</span>');
    return rows.join('');
  }

  function render(q) {
    var res = document.getElementById('sp-res');
    if (!res) return;
    var nq = norm(q), tokens = nq ? nq.split(' ') : [];
    if (!tokens.length) { res.innerHTML = '<div class="sp-empty">Busca por artista, álbum, canción o lista</div>'; return; }
    if (!DATA) { res.innerHTML = '<div class="sp-empty">Cargando…</div>'; load().then(function (d) { if (d) render(document.getElementById('sp-inp').value); else res.innerHTML = '<div class="sp-empty">No se pudo cargar el índice de búsqueda</div>'; }); return; }

    var html = '';
    // Artistas
    var arts = ART.filter(function (a) { return all(tokens, a.key); });
    arts.sort(function (a, b) { return (a.key === nq ? 0 : a.key.indexOf(nq) === 0 ? 1 : 2) - (b.key === nq ? 0 : b.key.indexOf(nq) === 0 ? 1 : 2) || b.nl - a.nl; });
    if (arts.length) {
      html += '<div class="sp-sect">Artistas</div>' + arts.slice(0, 5).map(function (a) {
        var nA = 0, nS = 0; a.items.forEach(function (ix) { if (DATA.i[ix][2]) nA++; else nS++; });
        var parts = []; if (nA) parts.push(nA + (nA === 1 ? ' álbum' : ' álbumes')); if (nS) parts.push(nS + (nS === 1 ? ' canción' : ' canciones'));
        var per = {}; a.items.forEach(function (ix) { DATA.i[ix][3].forEach(function (p) { var o = per[p[0]] || (per[p[0]] = { n: 0, best: 1e9 }); o.n++; if (p[1] < o.best) o.best = p[1]; }); });
        var ks = Object.keys(per).sort(function (x, y) { return per[y].n - per[x].n || per[x].best - per[y].best; });
        var lk = ks.slice(0, 20).map(function (k) {
          var f = DATA.f[k], o = per[k];
          return '<a class="sp-lk" href="' + esc(f[0]) + '">' + esc(f[1]) + ' · ' + o.n + (o.n === 1 ? ' entrada' : ' entradas') + ' · mejor #' + o.best + '</a>';
        }).join('');
        if (ks.length > 20) lk += '<span class="sp-more">y ' + (ks.length - 20) + ' listas más</span>';
        lk += '<span class="sp-lk sp-filter" data-artist="' + esc(a.name) + '">Ver solo sus álbumes y canciones →</span>';
        return '<div class="sp-item sp-exp"><div class="sp-ico">🎤</div><div style="min-width:0;flex:1"><div class="sp-ttl">' + esc(a.name) +
          '</div><div class="sp-sub">' + parts.join(' · ') + ' · en ' + a.nl + (a.nl === 1 ? ' lista' : ' listas') + '</div><div class="sp-lists">' + lk + '</div></div></div>';
      }).join('');
    }
    // Álbumes y canciones
    [1, 0].forEach(function (t) {
      var m = DATA.i.filter(function (it) { return it[2] === t && all(tokens, it.n); });
      m.sort(function (a, b) { return rank(a, nq) - rank(b, nq) || b[3].length - a[3].length; });
      if (!m.length) return;
      html += '<div class="sp-sect">' + (t ? 'Álbumes' : 'Canciones') + (m.length > 8 ? ' · ' + m.length : '') + '</div>' + m.slice(0, 8).map(function (it) {
        var best = Math.min.apply(null, it[3].map(function (p) { return p[1]; }));
        return '<div class="sp-item sp-exp"><div class="sp-ico">' + ICON[t] + '</div><div style="min-width:0;flex:1"><div class="sp-ttl">' + esc(it[1]) +
          '</div><div class="sp-sub">' + esc(it[0]) + ' · en ' + it[3].length + (it[3].length === 1 ? ' lista' : ' listas') + ' · mejor puesto #' + best +
          '</div><div class="sp-lists">' + listsHTML(it) + '</div></div></div>';
      }).join('');
    });
    // Listas
    var ls = [];
    DATA.f.forEach(function (f) { if (all(tokens, f.n)) ls.push(f); });
    if (ls.length) {
      html += '<div class="sp-sect">Listas</div>' + ls.slice(0, 6).map(function (f) {
        return '<a class="sp-item sp-link" href="' + esc(f[0]) + '"><div class="sp-ico">' + (f[3] === 'albumes' ? '💿' : '🎵') +
          '</div><div style="min-width:0"><div class="sp-ttl">' + esc(f[1]) + '</div><div class="sp-sub">' + esc(f[4]) + ' entradas · ' + esc(f[2]) + '</div></div></a>';
      }).join('');
    }
    res.innerHTML = html || '<div class="sp-empty">Sin resultados para "' + esc(q) + '"</div>';
  }

  var CSS = '.sp-ov{display:none;position:fixed;inset:0;background:rgba(7,6,13,.75);z-index:1000;align-items:flex-start;justify-content:center;padding-top:80px;backdrop-filter:blur(4px)}' +
    '.sp-ov.open{display:flex}.sp-box{width:min(620px,94vw);border:1px solid #2a2840;border-radius:12px;background:#14121f;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.5);font-family:"DM Sans",system-ui,sans-serif}' +
    '.sp-row{display:flex;align-items:center;gap:10px;padding:15px 18px;border-bottom:1px solid #2a2840}.sp-row svg{width:16px;height:16px;color:#8a88a0;flex-shrink:0}' +
    '.sp-inp{flex:1;background:none;border:none;outline:none;font-size:15px;color:#f2f1fa;font-family:inherit}.sp-inp::placeholder{color:#8a88a0}' +
    '.sp-esc{font-size:11px;padding:3px 8px;border:1px solid #2a2840;border-radius:5px;color:#8a88a0;cursor:pointer}' +
    '.sp-res{max-height:min(60vh,520px);overflow-y:auto}.sp-sect{padding:10px 18px 4px;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:#8a88a0}' +
    '.sp-item{display:flex;align-items:flex-start;gap:12px;padding:9px 18px;cursor:pointer;text-decoration:none;color:inherit}.sp-item:hover{background:#1d1b2e}' +
    '.sp-ico{width:34px;height:34px;border-radius:7px;border:1px solid #2a2840;background:#1d1b2e;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px}' +
    '.sp-ttl{font-size:14px;color:#f2f1fa}.sp-sub{font-size:12px;color:#8a88a0}.sp-empty{padding:36px 18px;text-align:center;color:#8a88a0;font-size:14px}';
  var CSS2 = '.sp-lists{display:none;margin-top:6px;flex-direction:column;gap:3px}.sp-exp.open .sp-lists{display:flex}' +
    '.sp-lk{font-size:12px;color:#7ab0ff;text-decoration:none}.sp-filter{cursor:pointer;margin-top:4px;font-weight:600}.sp-lk:hover{text-decoration:underline}.sp-more{font-size:11px;color:#8a88a0}' +
    '.sp-ttl{overflow:hidden;text-overflow:ellipsis}.sp-link .sp-ttl{color:inherit}.sp-srchbtn{cursor:pointer}';

  function ensureOverlay() {
    if (document.getElementById('sp')) return;
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    var d = document.createElement('div'); d.className = 'sp-ov'; d.id = 'sp';
    d.innerHTML = '<div class="sp-box"><div class="sp-row"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' +
      '<input class="sp-inp" id="sp-inp" placeholder="Buscar artista, álbum, canción o lista..." autocomplete="off"><span class="sp-esc" id="sp-esc">ESC</span></div><div class="sp-res" id="sp-res"></div></div>';
    document.body.appendChild(d);
    d.addEventListener('click', function (e) { if (e.target === d) close(); });
    var esc_ = document.getElementById('sp-esc'); if (esc_) esc_.addEventListener('click', close);
  }

  function open() {
    ensureOverlay();
    var ov = document.getElementById('sp'); ov.classList.add('open');
    var inp = document.getElementById('sp-inp'); setTimeout(function () { inp.focus(); inp.select(); }, 40);
    render(inp.value); load().then(function () { render(inp.value); });
  }
  function close() {
    var ov = document.getElementById('sp'); if (ov) ov.classList.remove('open');
  }

  function init() {
    var st = document.createElement('style'); st.textContent = CSS2; document.head.appendChild(st);
    ensureOverlay();
    var inp = document.getElementById('sp-inp');
    inp.removeAttribute('oninput'); inp.setAttribute('placeholder', 'Buscar artista, álbum, canción o lista...');
    inp.addEventListener('input', function () { render(inp.value); });
    document.getElementById('sp-res').addEventListener('click', function (e) {
      if (e.target.closest('a')) return;
      var a = e.target.closest('[data-artist]');
      if (a) { inp.value = a.getAttribute('data-artist'); render(inp.value); inp.focus(); return; }
      var x = e.target.closest('.sp-exp'); if (x) x.classList.toggle('open');
    });
    // Sustituye el buscador anterior del index y engancha el botón de las páginas de lista
    window.openSp = open; window.closeSp = function (e) { var ov = document.getElementById('sp'); if (!e || !e.target || e.target === ov) close(); };
    window.filterSp = function (q) { render(q); };
    document.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open(); }
      else if (e.key === 'Escape') close();
    });
    var mb = document.getElementById('siMenuBtn');
    if (mb && !document.querySelector('.btn-srch,.si-srchbtn')) {
      var b = document.createElement('button'); b.className = 'si-menuBtn si-srchbtn'; b.type = 'button'; b.setAttribute('aria-label', 'Buscar');
      b.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>Buscar';
      b.addEventListener('click', open);
      mb.parentNode.appendChild(b);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
