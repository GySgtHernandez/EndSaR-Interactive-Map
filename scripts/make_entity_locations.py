"""One-time helper: build data/entity-locations.csv for entities that have no district boundary.
Inputs: CEPI EEM district export, NCES EDGE LEA geocode file (2024-25), boundary files, map data.
"""
import csv, json, sys, math
from openpyxl import load_workbook
EEM, NCES, SITE, MAPDATA, OUT = sys.argv[1:6]

def load_js(path):
    t = open(path, encoding='utf-8').read(); return json.loads(t.split('=', 1)[1].strip().rstrip(';'))

def centroid(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    best = None
    for poly in polys:
        ring = poly[0]; a = cx = cy = 0
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
        if a and (best is None or abs(a) > abs(best[0])): best = (a, cx / (3 * a), cy / (3 * a))
    return best[2], best[1]

REMAP = {'82070': '82749', '61020': '61905', '21690': '25250'}  # boundary id corrections
dist = {f['properties']['id']: centroid(f['geometry']) for f in load_js(f'{SITE}/district-boundaries-optimized.js')['features']}
isd = {}
for f in load_js(f'{SITE}/isd-boundaries-optimized.js')['features']:
    isd[f['properties']['id']] = centroid(f['geometry'])
wb = load_workbook(EEM, read_only=True); rows = list(wb['Combined_EEM_Data'].iter_rows(values_only=True)); ix = {k: i for i, k in enumerate(rows[0])}
eem = {}
for r in rows[1:]:
    if r[ix['District Code']] and not r[ix['Entity Code']]:
        eem.setdefault(str(r[ix['District Code']]).zfill(5), r)
nces = {}
for line in open(NCES, encoding='latin-1'):
    p = line.split('|')
    if p[0].startswith('26'): nces[p[0]] = (float(p[10]), float(p[11]))
items = json.load(open(MAPDATA))['datasets']['approximated']['sources']['district']['items']
out, stats, stacked = [], {}, {}
for code in sorted(items):
    if code in dist: continue
    r = eem.get(code); lat = lon = None; how = ''
    if r and r[ix['Entity NCES Code']] in nces:
        lat, lon = nces[r[ix['Entity NCES Code']]]; how = 'NCES 2024-25 district office geocode'
    elif r and REMAP.get(host := str(r[ix['Entity Geographic LEA District Code']] or '').zfill(5), host) in dist:
        lat, lon = dist[REMAP.get(host, host)]; how = 'approximate: centre of host district (CEPI EEM)'
    elif code.endswith('000'):
        key = items[code].get('isdCode') or code[:2]
        for k in (key, key.zfill(2), code, code[:2]):
            if k in isd: lat, lon = isd[k]; how = 'approximate: centre of ISD'; break
    if lat is None:
        stats['none'] = stats.get('none', 0) + 1; continue
    if how.startswith('approximate'):  # spread stacked approximate points in a small circle
        n = stacked.get((lat, lon), 0); stacked[(lat, lon)] = n + 1
        if n: ang = n * 2.4; lat += 0.018 * math.sqrt(n) * math.cos(ang); lon += 0.024 * math.sqrt(n) * math.sin(ang)
    stats[how] = stats.get(how, 0) + 1
    kind = 'ISD' if code.endswith('000') else {'PSA District': 'PSA', 'State District': 'State District'}.get(r[ix['District Type Name']] if r else '', 'PSA')
    out.append({'district_code': code, 'name': items[code]['name'], 'entity_type': kind, 'latitude': round(lat, 5), 'longitude': round(lon, 5), 'location_source': how})
with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(stats, len(out))
