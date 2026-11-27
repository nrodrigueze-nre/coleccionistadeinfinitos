#!/usr/bin/env python3
"""Genera search-index.json para el buscador (senal-search.js): artista / álbum / canción / lista.
Formato:
  {"f": [[archivo, título, fuente, tipo, count, desc], ...],          # todas las listas de LISTS (índice = id de lista)
   "i": [[artista, título, 0=canción|1=álbum, [[id_lista, posición], ...]], ...]}  # ítems únicos
Correr después de añadir/cambiar listas:  python3 tools/build_search.py
"""
import os, re, glob, json, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_aclamados as B

def lists_meta():
    h = open(os.path.join(B.ROOT, 'index.html'), encoding='utf-8').read()
    blk = h[h.index('const LISTS'):h.index('const SECTIONS')]
    out = []
    for m in re.finditer(r'\{\s*file:\s*"([^"]+)"(.*?)\n\s*\}', blk, re.S):
        body = m.group(2)
        def g(k):
            x = re.search(r'\b' + k + r':\s*("(?:[^"\\]|\\.)*")', body)
            return json.loads(x.group(1)) if x else ''
        out.append([m.group(1), g('title'), g('source'), g('type'), g('count'), g('desc')])
    return out

def main():
    meta = lists_meta()
    items = {}
    for fi, mt in enumerate(meta):
        p = os.path.join(B.ROOT, mt[0])
        if not os.path.exists(p): continue
        res = B.read_list(p)
        if not res or not res[1]: continue
        typ, rows = res
        for pos, (artist, title, _y) in enumerate(rows, 1):
            artist = html.unescape(artist).strip(); title = html.unescape(title).strip()
            k = (B.norm(artist), B.norm(title), 1 if typ == 'albumes' else 0)
            if not k[0] and not k[1]: continue
            it = items.setdefault(k, [artist, title, k[2], []])
            it[3].append([fi, pos])
    out = {'f': meta, 'i': sorted(items.values(), key=lambda x: (-len(x[3]), x[0].lower(), x[1].lower()))}
    path = os.path.join(B.ROOT, 'search-index.json')
    open(path, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    print('listas:', len(meta), 'ítems únicos:', len(out['i']), 'bytes:', os.path.getsize(path))

if __name__ == '__main__':
    main()
