"""Assembla site/data/videos.json, mentions.json e lo zip dei dati.
Uso: python build.py <work_dir> <site_dir>
work_dir contiene: cand_mentions.jsonl, labels/*.jsonl, cards/*.jsonl, meta.jsonl, hn_sel.json, htdata/"""
import json, os, sys, glob, collections, zipfile, datetime

CLIN = ('md', 'res', 'stu', 'rn', 'rx', 'ems')
REC = ('rec', 'strong_rec')

def jl(path):
    out = []
    for l in open(path, encoding='utf-8'):
        try: out.append(json.loads(l))
        except Exception: pass   # righe troncate di blocchi interrotti
    return out

def main(W, S):
    here = os.path.dirname(os.path.abspath(__file__))
    tax = json.load(open(os.path.join(here, 'taxonomy.json'), encoding='utf-8'))
    valid = {c['id'] for a in tax['areas'] for c in a['cats']}

    # --- Reddit ---
    ments = {m['k']: m for m in jl(os.path.join(W, 'cand_mentions.jsonl'))}
    for p in glob.glob(os.path.join(W, 'labels', '*.jsonl')):
        for l in jl(p):
            if l.get('k') in ments and l.get('st'): ments[l['k']].update({'st': l.get('st'), 'why': l.get('why', ''), 'q': l.get('q', '')})
    byv = collections.defaultdict(list)
    for m in ments.values():
        if m.get('st'): byv[m['vid']].append(m)

    # --- HN (HackerTube export) ---
    H = os.path.join(W, 'htdata', 'hackertube-data')
    hn_sel = set(json.load(open(os.path.join(W, 'hn_sel.json'))))
    hnv = {v['vid']: v for v in jl(os.path.join(H, 'videos.jsonl')) if v['vid'] in hn_sel}
    hnm = collections.defaultdict(list)
    for m in jl(os.path.join(H, 'mentions.jsonl')):
        if m['vid'] in hnv: hnm[m['vid']].append(m)

    cards = {}
    for p in glob.glob(os.path.join(W, 'cards', '*.jsonl')):
        for c in jl(p): cards[c['vid']] = c
    meta = {}
    if os.path.exists(os.path.join(W, 'meta.jsonl')):
        for d in jl(os.path.join(W, 'meta.jsonl')):
            if d['vid'] not in meta or d['src'] == 'api': meta[d['vid']] = d

    videos, mentions_out, rec_authors = [], {}, {}
    for vid in set(byv) | set(hnv):
        md = meta.get(vid)
        if md is not None and not md.get('ok'): continue          # cancellato, privato o non embeddabile
        rm = byv.get(vid, [])
        recs = [m for m in rm if m['st'] in REC and m['author'] not in ('[deleted]',)]
        r = collections.Counter()
        authors = {}
        for m in recs: authors.setdefault(m['author'], m['role'])
        for role in authors.values(): r[role] += 1
        h = hnv.get(vid)
        if h: r['hn'] += h['hn']['recommenders']
        # 2 persone diverse, oppure un post linkato molto votato in una community clinica (i voti sono consigli)
        reddit_ok = len(authors) >= 2 or any(m['kind'] == 'post' and (m['score'] or 0) >= 100 for m in recs)
        if not (reddit_ok or (h and h['hn']['recommenders'] >= 2)): continue
        card = cards.get(vid, {})
        if card.get('drop'): continue                              # non è un video di medicina/salute
        # ogni mese conta quanto il ruolo più "clinico" che ha consigliato quel mese: gli studenti pesano meno
        W_ROLE = {'md': 1.0, 'res': 1.0, 'rn': 1.0, 'rx': 1.0, 'ems': 1.0, 'stu': 0.6, 'oth': 0.7}
        month_w = {}
        for m in recs: month_w[m['month']] = max(month_w.get(m['month'], 0), W_ROLE.get(m['role'], 0.7))
        strong_m = {m['month'] for m in recs if m['st'] == 'strong_rec'}
        clin_auth = sum(1 for a, ro in authors.items() if ro in CLIN and ro != 'stu')
        sc = sum(month_w.values()) + 0.5 * len(strong_m) + 0.5 * clin_auth
        if h: sc += 0.4 * h['score']   # il sito è dei clinici: HN pesa meno
        crit = sum(1 for m in rm if m['st'] == 'critical' and m['role'] in CLIN) + (h['hn']['stances'].get('critical', 0) if h else 0)
        years = [int(m['month'][:4]) for m in rm] + ([h['hn']['first_year'], h['hn']['last_year']] if h else [])
        title = (md or {}).get('title') or (h or {}).get('title') or card.get('title') or ''
        if not title: continue
        cats = [c for c in card.get('cat', []) if c in valid][:3]
        if not cats: continue
        v = {'vid': vid, 't': title, 'ch': (md or {}).get('channel') or (h or {}).get('channel') or '',
             's': card.get('s') or (h or {}).get('summary', ''), 'w': card.get('w', ''),
             'ct': card.get('ct') or (h or {}).get('content_type'), 'lv': card.get('lv'), 'shelf': card.get('shelf') or (h or {}).get('shelf_life'),
             'cat': cats, 'tags': card.get('tags', [])[:6], 'sc': round(sc, 2), 'r': {k: n for k, n in r.items() if n},
             'crit': crit, 'y0': min(years), 'y1': max(years),
             'dur': (md or {}).get('dur'), 'views': (md or {}).get('views')}
        videos.append(v)
        rec_authors[vid] = set(authors)
        notes = []
        order = {'strong_rec': 0, 'critical': 1, 'rec': 2, 'reference': 3, 'joke': 4}
        for m in sorted(rm, key=lambda m: (order.get(m['st'], 9), -(m['score'] or 0))):
            if m['st'] not in order: continue
            if m['kind'] == 'comment':
                url = f"https://www.reddit.com/r/{m['sub']}/comments/{(m.get('link_id') or 't3_')[3:]}/_/{m['id']}/"
            else:
                url = f"https://www.reddit.com/r/{m['sub']}/comments/{m['id']}/"
            notes.append({'role': m['role'], 'sub': m['sub'], 'st': m['st'], 'why': m.get('why', ''),
                          'q': m.get('q', ''), 'tx': m['text'][:500], 'url': url, 'm': m['month']})
        for m in (hnm.get(vid) or [])[:6]:
            if m['stance'] in ('rec', 'strong_rec', 'critical'):
                notes.append({'role': 'hn', 'sub': '', 'st': m['stance'], 'why': m.get('why', ''), 'q': m.get('quote', ''),
                              'tx': m['text'][:500].replace('[VIDEO]', '(this video)').replace('[LINK]', '(link)'), 'url': m['hn_url'], 'm': m['month']})
        mentions_out[vid] = notes[:14]

    # correlati: stessi raccomandatori Reddit, poi i correlati di HackerTube
    hn_rel = {d['vid']: [x['vid'] for x in d['related']] for d in jl(os.path.join(H, 'related.jsonl'))}
    inv = collections.defaultdict(set)
    for vid, au in rec_authors.items():
        for a in au: inv[a].add(vid)
    keep = {v['vid'] for v in videos}
    for v in videos:
        c = collections.Counter()
        for a in rec_authors.get(v['vid'], ()):
            if len(inv[a]) <= 40:
                for o in inv[a]:
                    if o != v['vid']: c[o] += 1
        rel = [o for o, n in c.most_common(20)]
        rel += [o for o in hn_rel.get(v['vid'], []) if o in keep and o not in rel]
        v['rel'] = rel[:16]

    videos.sort(key=lambda v: -v['sc'])
    subs = sorted({m['sub'] for m in ments.values()})
    all_years = [v['y0'] for v in videos] + [v['y1'] for v in videos]
    out = {'generated': datetime.date.today().isoformat(),
           'stats': {'mentions': sum(1 for m in ments.values() if m.get('st')) + sum(len(x) for x in hnm.values()),
                     'subs': len(subs), 'years': f'{min(all_years)}–{max(all_years)}' if all_years else ''},
           'areas': tax['areas'], 'videos': videos}
    D = os.path.join(S, 'data'); os.makedirs(D, exist_ok=True)
    json.dump(out, open(os.path.join(D, 'videos.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(mentions_out, open(os.path.join(D, 'mentions.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    with zipfile.ZipFile(os.path.join(D, 'grandrounds-data.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        # i termini della YouTube API vietano di ridistribuire i suoi dati: nello zip niente durata e visualizzazioni
        out_zip = {**out, 'videos': [{k: x for k, x in v.items() if k not in ('dur', 'views')} for v in videos]}
        z.writestr('videos.json', json.dumps(out_zip, ensure_ascii=False, indent=1))
        z.writestr('mentions.json', json.dumps(mentions_out, ensure_ascii=False, indent=1))
        z.writestr('DATA.md', open(os.path.join(here, 'DATA.md'), encoding='utf-8').read())
    print('video:', len(videos), '| con clinici:', sum(1 for v in videos if any(v['r'].get(k) for k in CLIN)),
          '| solo HN:', sum(1 for v in videos if set(v['r']) == {'hn'}), '| dibattuti:', sum(1 for v in videos if v['crit']))
    print('per categoria:', collections.Counter(c for v in videos for c in v['cat'][:1]).most_common())

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
