"""Dopo l'etichettatura: prepara l'input delle schede per i video Reddit che possono entrare nel sito.
Uso: python cards_input.py <work_dir> [per_blocco] [prefisso]
Salta i video che hanno già una scheda in cards/."""
import json, sys, os, glob, collections

W = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
ments = {}
for l in open(os.path.join(W, 'cand_mentions.jsonl'), encoding='utf-8'):
    m = json.loads(l); ments[m['k']] = m
for p in glob.glob(os.path.join(W, 'labels', '*.jsonl')):
    for l in open(p, encoding='utf-8'):
        try: d = json.loads(l)
        except Exception: continue
        if d.get('k') in ments and d.get('st'): ments[d['k']].update(d)
meta = {}
for l in open(os.path.join(W, 'meta.jsonl'), encoding='utf-8'):
    d = json.loads(l); meta[d['vid']] = d
hn = set(json.load(open(os.path.join(W, 'hn_sel.json'))))
have = set()
for p in glob.glob(os.path.join(W, 'cards', '*.jsonl')):
    for l in open(p, encoding='utf-8'):
        try: have.add(json.loads(l)['vid'])
        except Exception: pass
H = os.path.join(W, 'htdata', 'hackertube-data', 'videos.jsonl')
hn_add = set(json.load(open(os.path.join(W, 'hn_add.json')))) if os.path.exists(os.path.join(W, 'hn_add.json')) else set()
by = collections.defaultdict(list)
for m in ments.values():
    if m.get('st'): by[m['vid']].append(m)
print('etichette:', collections.Counter(m['st'] for ms in by.values() for m in ms))
rows = []
for vid, ms in by.items():
    if not meta.get(vid, {}).get('ok') or vid in have: continue
    recs = [m for m in ms if m['st'] in ('rec', 'strong_rec')]
    au = {m['author'] for m in recs}
    if not (len(au) >= 2 or any(m['kind'] == 'post' and (m['score'] or 0) >= 100 for m in recs)): continue
    rows.append({'vid': vid, 'title': meta[vid]['title'], 'channel': meta[vid]['channel'],
                 'src': 'both' if vid in hn else 'reddit', 'subs': sorted({m['sub'] for m in ms}),
                 'whys': [m['why'] for m in recs if m.get('why')][:6],
                 'quotes': [m['q'] for m in recs if m.get('q')][:3]})
for l in open(H, encoding='utf-8'):
    v = json.loads(l)
    if v['vid'] in hn_add and v['vid'] not in have and v['vid'] not in {r['vid'] for r in rows}:
        rows.append({'vid': v['vid'], 'title': v['title'], 'channel': v['channel'], 'src': 'hn', 'subs': ['hackernews'],
                     'whys': [], 'quotes': [v['quote']['text']] if v.get('quote') else [], 'hn_summary': v.get('summary', '')})
PFX = sys.argv[3] if len(sys.argv) > 3 else 'r'
os.makedirs(os.path.join(W, 'cardin'), exist_ok=True)
for i in range(0, len(rows), N):
    with open(os.path.join(W, 'cardin', f'{PFX}{i // N:02d}.jsonl'), 'w', encoding='utf-8') as f:
        for r in rows[i:i + N]: f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('video Reddit che entrano:', len(rows), '| blocchi:', (len(rows) + N - 1) // N)
