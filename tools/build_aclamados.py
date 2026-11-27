#!/usr/bin/env python3
"""Recalcula los "Más aclamados" (artistas, álbumes, canciones) leyendo los
arreglos SONGS/ALBUMS de todas las páginas de listas y reescribe las tres
líneas topArtists/topAlbums/topSongs de index.html.

Uso:  python3 tools/build_aclamados.py          (escribe index.html)
      python3 tools/build_aclamados.py --dry    (solo muestra el resultado)
Regla: cada lista cuenta UNA vez por artista / álbum / canción.
"""
import re, glob, json, sys, os, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOP_N = 10
SKIP_FILES = {'index.html', 'Index.html'}
# páginas cuyo render no permite detectar la columna del artista (índice dentro de la fila)
ARTIST_COL_OVERRIDE = {'rolling-stone-100-best-albums-2024.html': 2}
NOT_ARTISTS = {'variousartists', 'varios', 'soundtrack', 'variosartistas', 'artistasvarios', 'originalcast', 'castrecording', 'originalsoundtrack'}

def strip_accents(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()

def norm(s):
    s = strip_accents(s).lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', '', s)
    s = re.sub(r'^the ', '', s.strip())
    return re.sub(r'[^a-z0-9]+', '', s)

def primary_artist(a):
    # "X feat. Y", "X featuring Y", "X ft. Y" -> X
    return re.split(r'\s+(?:feat\.?|featuring|ft\.?)\s+', a, flags=re.I)[0].strip()

def js_str(tok):
    q = tok[0]
    body = tok[1:-1]
    return re.sub(r'\\(.)', r'\1', body)

STR = r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')'''

def artist_index(h):
    """0-based índice (1 ó 2) de la columna artista, leyendo el render de la fila."""
    m = re.search(r'dataset\.artist\s*=\s*encodeURIComponent\(\s*([\w\[\]]+)', h)
    if not m:
        m = re.search(r'data-artist=\\?"\\?"\s*\+\s*encodeURIComponent\(\s*([\w\[\]]+)', h)
    if not m:
        m = re.search(r'data-artist=\\?"[^+]*\+\s*encodeURIComponent\(\s*([\w\[\]]+)', h)
    if not m:
        return None
    expr = m.group(1)
    mi = re.fullmatch(r'\w+\[(\d)\]', expr)
    if mi:
        return int(mi.group(1))
    a = re.search(r'\b' + re.escape(expr) + r'\s*=\s*\w+\[(\d)\]', h)
    return int(a.group(1)) if a else None

TYPE_OVERRIDE = {'putumayo-world-music-coleccion.html': 'albumes',
                 'rolling-stone-10-best-latin-2015.html': 'albumes', 'rolling-stone-10-best-latin-2016.html': 'albumes',
                 'rolling-stone-10-best-latin-2017.html': 'albumes', 'rolling-stone-10-best-latin-2018.html': 'albumes'}
ARTIST_COL_OVERRIDE.update({'apple-music-10-years-top-500.html': 2,
                            'acroarte-100-albumes-esenciales-dominicana.html': 2})

def read_html_rows(h):
    """Páginas antiguas con las filas escritas a mano en el HTML (.track-row)."""
    rows = []
    for r in re.finditer(r'class="track-name">(.*?)</div>\s*<div class="track-artist">(.*?)</div>\s*</div>\s*<div class="track-year">(\d{4})?', h, re.S):
        import html as _h
        rows.append((_h.unescape(r.group(2)).strip(), _h.unescape(r.group(1)).strip(), int(r.group(3)) if r.group(3) else None))
    return rows

# ── Artistas acreditados (colaboraciones) ─────────────────────────────────────
# "Zayn & Taylor Swift" cuenta para Zayn y para Taylor Swift.  Reglas:
#  · marcadores explícitos (feat., ft., with, vs.) separan siempre: primer artista + invitados;
#    los invitados se parten también por & , and.
#  · separadores ambiguos (& , / + and x) separan solo si al menos una parte aparece como artista único
#    en alguna lista ("y" exige que todas lo sean);
#  · nunca se parten bandas del tipo "X and the Y" / "X & His Y" ni las de NEVER_SPLIT.
SEP_STRONG = re.compile(r'\s+(?:feat\.?|featuring|ft\.?|with|vs\.?)\s+', re.I)
SEP_WEAK = re.compile(r'\s*(?:,|;|/|&|\band\b)\s*|\s+[xX]\s+', re.I)
SEP_Y = re.compile(r'\s+y\s+')
BANDISH = re.compile(r'^(?:the|his|her|its|su|sus|los|las|el|la)\b', re.I)
NEVER_SPLIT = {'earthwindandfire', 'crosbystillsandnash', 'crosbystillsnashandyoung', 'hallandoates', 'simonandgarfunkel',
               'teganandsara', 'zionandlennox', 'wisinandyandel', 'wisinyandel', 'danshay', 'mars', 'mandsprestheigirlnextdoor'}
_SEP_ANY = re.compile(r'\s+(?:feat\.?|featuring|ft\.?|with|vs\.?)\s+|,|;|/|&|\band\b|\s+[xX]\s+|\s+y\s+', re.I)

def known_artists(all_artist_strings):
    """Conjunto (normalizado) de nombres que aparecen como artista único (sin separadores) en alguna lista."""
    return {norm(a) for a in all_artist_strings if a and not _SEP_ANY.search(a)}

def _weak(part, known):
    part = part.strip()
    if norm(part) in NEVER_SPLIT: return [part]
    sub = [x.strip() for x in SEP_WEAK.split(part) if x.strip()]
    if len(sub) > 1:
        if any(len(norm(x)) <= 1 for x in sub) or any(BANDISH.match(x) for x in sub[1:]): return [part]
        if any(norm(x) in known for x in sub): return sub
        return [part]
    sub = [x.strip() for x in SEP_Y.split(part) if x.strip()]
    if len(sub) > 1 and all(norm(x) in known for x in sub): return sub
    return [part]

def credited(artist, known):
    """Lista de artistas acreditados (únicos, en orden) para un campo de artista."""
    artist = (artist or '').strip()
    if not artist: return []
    parts = SEP_STRONG.split(artist)
    out = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part: continue
        if i == 0: out += _weak(part, known)
        else:
            sub = [x.strip() for x in SEP_WEAK.split(part) if x.strip()] if norm(part) not in NEVER_SPLIT else [part]
            out += sub if len(sub) > 1 and not any(BANDISH.match(x) for x in sub[1:]) else [part]
    seen, res = set(), []
    for x in out:
        k = norm(x)
        if k and k not in seen:
            seen.add(k); res.append(x)
    return res

def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        k = (norm(r[0]), norm(r[1]))
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def read_list(path):
    h = open(path, encoding='utf-8').read()
    name = os.path.basename(path)
    t = re.search(r'LIST_TYPE\s*=\s*["\'](\w+)', h)
    m = re.search(r'\b(?:var|const|let)\s+(SONGS|ALBUMS|songs|albums)\s*=\s*\[(.*?)\n?\]\s*;', h, re.S)
    if m and not re.search(r'\[\s*\d+\s*,\s*' + STR + r'\s*,\s*' + STR, m.group(2)):
        m = None
    if not m:
        rows = read_html_rows(h)
        if len(rows) < 5:
            return None
        typ = t.group(1) if t else ('albumes' if re.search(r'album', name) else 'canciones')
        return TYPE_OVERRIDE.get(name, typ), dedupe(rows)
    var = m.group(1)
    typ = t.group(1) if t else ('albumes' if var.lower() == 'albums' else 'canciones')
    typ = TYPE_OVERRIDE.get(name, typ)
    ai = ARTIST_COL_OVERRIDE.get(name) or artist_index(h)
    if ai not in (1, 2):
        ai = 1 if var == 'ALBUMS' else 2   # convención por defecto
    ti = 3 - ai
    rows = []
    for r in re.finditer(r'\[\s*\d+\s*,\s*' + STR + r'\s*,\s*' + STR + r'(?:\s*,\s*(\d{4}))?', m.group(2)):
        cols = {1: js_str(r.group(1)), 2: js_str(r.group(2))}
        rows.append((cols[ai], cols[ti], int(r.group(3)) if r.group(3) else None))
    return typ, dedupe(rows)

def main():
    dry = '--dry' in sys.argv
    art, alb, sng = (collections.defaultdict(set) for _ in range(3))
    disp = {}
    variants = collections.defaultdict(collections.Counter)
    counted, skipped = [], []
    loaded = []
    for f in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
        name = os.path.basename(f)
        if name in SKIP_FILES:
            continue
        res = read_list(f)
        if not res or not res[1]:
            skipped.append(name); continue
        loaded.append((name, res[0], res[1]))
    known = known_artists([r[0] for _n, _t, rows in loaded for r in rows])
    for name, typ, rows in loaded:
        counted.append(name)
        for artist, title, _year in rows:
            cr = [c for c in credited(artist, known) if norm(c) and norm(c) not in NOT_ARTISTS]
            if not cr:
                continue
            for c in cr:                      # cada artista acreditado suma una vez por lista
                kc = norm(c)
                art[kc].add(name); variants[('a', kc)][c] += 1
            artist = cr[0]                     # la canción/álbum se identifica con el artista principal
            ka = norm(artist)
            kt = (ka, norm(title))
            (alb if typ == 'albumes' else sng)[kt].add(name)
            variants[('t', kt)][(title, artist)] += 1
    for k, c in variants.items():
        # variante más frecuente; en empate, la que conserva acentos/mayúsculas originales
        disp[k] = sorted(c.items(), key=lambda x: (str(x[0]) == strip_accents(str(x[0])), -x[1], str(x[0])))[0][0]
    def rank(d):
        return sorted(d.items(), key=lambda x: (-len(x[1]), str(x[0])))[:TOP_N]
    top_art = [{"name": disp[('a', k)], "sub": f"{len(v)} listas"} for k, v in rank(art)]
    def tracks(d):
        out = []
        for k, v in rank(d):
            title, artist = disp[('t', k)]
            out.append({"name": title, "artist": artist, "sub": f"{artist} \u00b7 {len(v)} listas"})
        return out
    lines = {
        'topArtists': top_art,
        'topAlbums': tracks(alb),
        'topSongs': tracks(sng),
    }
    print('omitidas:', ', '.join(skipped))
    print(f"listas leídas: {len(counted)} · omitidas (sin arreglo SONGS/ALBUMS): {len(skipped)}")
    for k, v in lines.items():
        print(k, [(x['name'], x['sub']) for x in v[:5]])
    if dry:
        return
    p = os.path.join(ROOT, 'index.html')
    h = open(p, encoding='utf-8').read()
    for k, v in lines.items():
        new = 'var %s=%s;' % (k, json.dumps(v, ensure_ascii=True, separators=(',', ':')))
        h, n = re.subn(r'var ' + k + r'=\[.*?\];', lambda _m: new, h, count=1, flags=re.S)
        if n != 1:
            sys.exit('No encontré var %s en index.html' % k)
    open(p, 'w', encoding='utf-8').write(h)
    print('index.html actualizado')

if __name__ == '__main__':
    main()
