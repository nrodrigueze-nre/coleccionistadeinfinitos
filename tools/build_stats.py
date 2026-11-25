#!/usr/bin/env python3
"""Inserta en cada página de lista el bloque "Top 3 de la lista" (antes de las
reseñas): artistas con más entradas, años con más entradas y, en listas de
álbumes, los álbumes más mencionados en otras listas del sitio (en listas de
canciones, las décadas con más canciones).
Idempotente: reemplaza lo que haya entre <!--STATS3--> y <!--/STATS3-->.
Uso: python3 tools/build_stats.py [--dry]
"""
import re, glob, os, sys, html, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_aclamados as b

START, END = '<!--STATS3-->', '<!--/STATS3-->'

def top(counter, first_rank, n=3):
    items = [(k, c) for k, c in counter.items() if c >= 2]
    items.sort(key=lambda x: (-x[1], first_rank.get(x[0], 10**6)))
    return items[:n]

def col(title, items, fmt):
    if not items:
        body = '<li class="s3-empty">Sin repetidos</li>'
    else:
        body = ''.join('<li><span class="s3-n">%s</span><span class="s3-c">%s</span></li>' % (html.escape(str(k)), html.escape(fmt(c))) for k, c in items)
    return '<div class="stats3-col"><h4>%s</h4><ol>%s</ol></div>' % (title, body)

def main():
    dry = '--dry' in sys.argv
    pages = {}
    album_lists = collections.defaultdict(set)   # (artista, álbum) -> listas que lo mencionan
    song_lists = collections.defaultdict(set)    # (artista, canción) -> listas que la mencionan
    for f in sorted(glob.glob(os.path.join(b.ROOT, '*.html'))):
        name = os.path.basename(f)
        if name in b.SKIP_FILES: continue
        res = b.read_list(f)
        if not res or not res[1]: continue
        pages[name] = res
        target = album_lists if res[0] == 'albumes' else song_lists
        for artist, title, _y in res[1]:
            target[(b.norm(b.primary_artist(artist)), b.norm(title))].add(name)
    changed = 0
    for name, (typ, rows) in pages.items():
        isalb = typ == 'albumes'
        unit = 'álbumes' if isalb else 'canciones'
        art = collections.Counter(); art_rank = {}; disp = {}
        yrs = collections.Counter(); yr_rank = {}
        alb = {}; alb_rank = {}
        for i, (artist, title, year) in enumerate(rows):
            pa = b.primary_artist(artist); k = b.norm(pa)
            if not k or k in b.NOT_ARTISTS: continue
            art[k] += 1; art_rank.setdefault(k, i); disp.setdefault(k, pa)
            if year:
                yrs[year] += 1; yr_rank.setdefault(year, i)
            ak = (k, b.norm(title)); n = len((album_lists if isalb else song_lists).get(ak, ()))
            if n >= 2:
                alb[title + ' — ' + pa] = n; alb_rank.setdefault(title + ' — ' + pa, i)
        n = len(rows)
        # Artistas: si ninguno se repite (o uno solo cubre casi toda la lista), se muestran los 3 primeros
        art_top = [(disp[k], c) for k, c in top(art, art_rank)]
        if not art_top or art_top[0][1] >= 0.9 * n:
            first3 = [(t + ' — ' + a, str(y) if y else '') for a, t, y in rows[:3]]
            c1 = col('Los 3 primeros de la lista', first3, lambda c: c)
        else:
            c1 = col('Artistas con más %s' % unit, art_top, lambda c: '%d' % c)
        cols = [c1]
        # Años: solo si la lista trae años y no es de un único año
        with_year = sum(yrs.values())
        yr_top = top(yrs, yr_rank)
        if yr_top and with_year >= 0.5 * n and yr_top[0][1] < 0.9 * n:
            cols.append(col('Años con más %s' % unit, yr_top, lambda c: '%d' % c))
        # Menciones en otras listas del sitio (álbumes en listas de álbumes, canciones en listas de canciones)
        alb_items = sorted(alb.items(), key=lambda x: (-x[1], alb_rank[x[0]]))[:3]
        if alb_items:
            cols.append(col('Álbumes con más menciones' if isalb else 'Canciones con más menciones', alb_items, lambda c: '%d listas' % c))
        if len(cols) == 1 and 'Los 3 primeros' in c1:
            block = START + '<section class="stats3"><div class="sec-label">Top 3 de la lista</div><div class="stats3-grid">' + c1 + '</div></section>' + END + '\n'
        else:
            block = START + '<section class="stats3"><div class="sec-label">Top 3 de la lista</div><div class="stats3-grid">' + ''.join(cols) + '</div></section>' + END + '\n'
        p = os.path.join(b.ROOT, name)
        h = open(p, encoding='utf-8').read()
        if START in h:
            new = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', lambda m: block, h, count=1, flags=re.S)
        else:
            m = re.search(r'<section class="feat-section"', h)
            if not m or not block: continue
            new = h[:m.start()] + block + h[m.start():]
        if new != h:
            changed += 1
            if not dry: open(p, 'w', encoding='utf-8').write(new)
        if dry and name in ('rollingstone-200-best-songs-1990s.html', 'pitchfork-100-best-indie-rock-albums.html'):
            print(name, re.sub(r'<[^>]+>', ' | ', block)[:400])
    print('páginas actualizadas:', changed, 'de', len(pages))

if __name__ == '__main__':
    main()
