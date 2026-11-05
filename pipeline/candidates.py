"""Dalle menzioni grezze: ruolo di chi scrive (flair, poi subreddit), selezione dei video candidati
e file da etichettare a blocchi.
Uso: python candidates.py <mentions_raw.jsonl> <outdir> [min_autori]"""
import json, sys, os, re, collections, datetime

def role_of(flair, sub):
    f = (flair or '').lower()
    w = set(re.findall(r'[a-z0-9]+', f))
    if f:
        if 'layperson' in f or 'patient' in f or 'non-medical' in f or 'not a' in f: return 'oth'
        if 'premed' in f or 'pre-med' in f: return 'oth'
        if 'student' in f or w & {'m1', 'm2', 'm3', 'm4', 'ms1', 'ms2', 'ms3', 'ms4', 'ms', 'oms', 'oms1', 'oms2', 'oms3', 'oms4'}: return 'stu'
        if 'resident' in f or 'pgy' in f or w & {'intern', 'fellow', 'registrar', 'sho', 'fy1', 'fy2', 'r1', 'r2', 'r3', 'r4'}: return 'res'
        if 'pharm' in f or 'rph' in w: return 'rx'
        if w & {'emt', 'paramedic', 'ems', 'flight', 'aemt'} or 'paramedic' in f: return 'ems'
        if w & {'rn', 'np', 'bsn', 'lpn', 'lvn', 'crna', 'msn', 'cna', 'aprn', 'dnp'} or 'nurs' in f: return 'rn'
        if w & {'md', 'do', 'mbbs', 'mbchb', 'gp', 'dds', 'dmd'} or 'physician' in f or 'attending' in f or 'consultant' in f \
           or 'doctor' in f or 'surgeon' in f or 'hospitalist' in f or 'ologist' in f or 'medicine' in f or 'psychiatr' in f: return 'md'
    return {'Residency': 'res', 'medicalschool': 'stu', 'step1': 'stu', 'Step2': 'stu', 'usmle': 'stu',
            'medicalschoolanki': 'stu', 'medicalschooluk': 'stu', 'nursing': 'rn', 'StudentNurse': 'rn', 'NursingUK': 'rn',
            'pharmacy': 'rx', 'Paramedics': 'ems', 'ems': 'ems', 'doctorsUK': 'md'}.get(sub, 'oth')

def main(src, outdir, min_auth=2):
    os.makedirs(outdir, exist_ok=True)
    by = collections.defaultdict(list)
    for line in open(src, encoding='utf-8'):
        m = json.loads(line)
        m['role'] = role_of(m.get('flair'), m['sub'])
        if m['sub'] == 'AskDocs' and m['role'] == 'oth':
            continue  # su AskDocs scrivono i pazienti: contano solo i medici con flair verificata
        m['month'] = datetime.datetime.fromtimestamp(m['utc'], datetime.UTC).strftime('%Y-%m')
        by[m['vid']].append(m)
    # chi linka sempre lo stesso canale/video molte volte = autopromozione: un autore conta una volta per video
    cand = {}
    for vid, ms in by.items():
        authors = {m['author'] for m in ms}
        clin = {m['author'] for m in ms if m['role'] in ('md', 'res', 'rn', 'rx', 'ems', 'stu')}
        top_post = max((m['score'] or 0 for m in ms if m['kind'] == 'post'), default=0)
        if len(authors) >= min_auth or (top_post >= 50 and len(clin) >= 1):
            # al massimo 12 menzioni, autori diversi prima, poi punteggio
            seen, keep = set(), []
            for m in sorted(ms, key=lambda m: -(m['score'] or 0)):
                if m['author'] in seen: continue
                seen.add(m['author']); keep.append(m)
                if len(keep) == 12: break
            cand[vid] = keep
    rows = [m for ms in cand.values() for m in ms]
    print('video totali con link:', len(by))
    print('autori distinti per video:', collections.Counter(min(len({m['author'] for m in ms}), 6) for ms in by.values()))
    print('candidati:', len(cand), ' menzioni da etichettare:', len(rows))
    print('ruoli:', collections.Counter(m['role'] for m in rows))
    with open(os.path.join(outdir, 'cand_mentions.jsonl'), 'w', encoding='utf-8') as f:
        for k, m in enumerate(rows):
            m['k'] = k
            f.write(json.dumps(m, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
