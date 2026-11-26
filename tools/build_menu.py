#!/usr/bin/env python3
"""Regenera el menú "Categorías" (si-dropdown) de TODAS las páginas de lista para que
sea idéntico al del index: mismas etiquetas, mismos grupos y contadores por sección
(calculados desde LISTS/SECTIONS de index.html).  Correr después de añadir/mover listas:
    python3 tools/build_menu.py
"""
import re, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()

sec = dict(re.findall(r'^\s*"([^"]+\.html)":\s*"([^"]+)"', idx[idx.index('const SECTIONS'):], re.M))
lists = re.findall(r'file:\s*"([^"]+)".*?type:\s*"(\w+)"', idx[idx.index('const LISTS'):idx.index('const SECTIONS')], re.S)
def n(f):
    return sum(1 for file, t in lists if f(sec.get(file), t))
COUNTS = {
 'super': n(lambda s,t: s=='super'),
 'albumes-globales': n(lambda s,t: s in ('global','albums-global') and t=='albumes'),
 'canciones-globales': n(lambda s,t: s in ('global','songs-global') and t=='canciones'),
 'albumes-latinos': n(lambda s,t: s in ('latin','latinas','albums-latin') and t=='albumes'),
 'canciones-latinas': n(lambda s,t: s in ('latin','latinas','songs-latin') and t=='canciones'),
 'tematicas': n(lambda s,t: s in ('tematica','thematic')),
 'anuales': n(lambda s,t: s=='annual'),
 'decadas': n(lambda s,t: s=='decades'),
 'generos': n(lambda s,t: s=='genres'),
 'cronologia': n(lambda s,t: t=='cronologia'),
}
LBL = {'super':'Superlistas','albumes-globales':'Álbumes Globales','canciones-globales':'Canciones Globales',
 'albumes-latinos':'Álbumes Latinos','canciones-latinas':'Canciones Latinas','tematicas':'Temáticas',
 'anuales':'Listas Anuales','decadas':'Por Décadas','generos':'Por Géneros','cronologia':'Cronología'}
def a(k): return '        <a href="index.html#%s">%s <span class="si-count">· %d</span></a>' % (k, LBL[k], COUNTS[k])
GROUPS = [('Superlistas',['super','albumes-globales','canciones-globales'],''),
 ('Música latina',['albumes-latinos','canciones-latinas'],''),
 ('Por época',['anuales','decadas','cronologia'],''),
 ('Por tema / género',['tematicas','generos'],'\n        <a href="music-quotes-page.html">Music Quotes <span class="si-count">nuevo</span></a>')]
BLOCK = ('<div class="si-dropdown" id="siDropdown">\n    <div class="si-dropdown-in">\n' +
 '\n'.join('      <div class="si-catgroup"><b>%s</b>\n%s%s</div>' % (t, '\n'.join(a(k) for k in ks), extra) for t, ks, extra in GROUPS) +
 '\n    </div>\n  </div>')
# nota: el patrón consume 3 </div> finales (cierre del último grupo, dropdown-in y dropdown); el contenedor del header queda intacto
PAT = re.compile(r'<div class="si-dropdown" id="siDropdown">.*?</div>\s*</div>\s*</div>', re.S)
changed = 0
for p in sorted(glob.glob(os.path.join(ROOT, '*.html'))):
    if os.path.basename(p) in ('index.html','Index.html'): continue
    h = open(p, encoding='utf-8').read()
    if 'id="siDropdown"' not in h: continue
    new = PAT.sub(lambda m: BLOCK, h, count=1)
    if new != h:
        open(p, 'w', encoding='utf-8').write(new); changed += 1
print('menú actualizado en', changed, 'páginas;', COUNTS)
