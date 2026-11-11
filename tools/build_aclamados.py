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
NOT_ARTISTS = {'variousartists', 'varios', 'soundtrack', 'varios artistas', 'original cast', 'castrecording'}

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
    body = body.replace('\\' + q, q).replace('\\\\', '\\')
    return body

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

def read_list(path):
    h = open(path, encoding='utf-8').read()
    t = re.search(r'LIST_TYPE\s*=\s*["\'](\w+)', h)
    if not t:
        return None
    m = re.search(r'\bvar\s+(SONGS|ALBUMS)\s*=\s*\[(.*?)\n?\]\s*;', h, re.S)
    if not m:
        return None
    ai = ARTIST_COL_OVERRIDE.get(os.path.basename(path)) or artist_index(h)
    if ai not in (1, 2):
        ai = 1 if m.group(1) == 'ALBUMS' else 2   # convención por defecto
        rows_probe = re.search(r'\[\s*\d+\s*,\s*' + STR + r'\s*,\s*' + STR, m.group(2))
        if not rows_probe:
            return None
    ti = 3 - ai
    rows = []
    for r in re.finditer(r'\[\s*\d+\s*,\s*' + STR + r'\s*,\s*' + STR, m.group(2)):
        cols = {1: js_str(r.group(1)), 2: js_str(r.group(2))}
        rows.append((cols[ai], cols[ti]))
    return t.group(1), rows

def main():
    dry = '--dry' in sys.argv
    art, alb, sng = (collections.defaultdict(set) for _ in range(3))
    disp = {}
    variants = collections.defaultdict(collections.Counter)
    counted, skipped = [], []
    for f in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
        name = os.path.basename(f)
        if name in SKIP_FILES:
            continue
        res = read_list(f)
        if not res or not res[1]:
            skipped.append(name); continue
        typ, rows = res
        counted.append(name)
        for artist, title in rows:
            artist = primary_artist(artist)
            ka = norm(artist)
            if not ka or ka in NOT_ARTISTS:
                continue
            art[ka].add(name); variants[('a', ka)][artist] += 1
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
