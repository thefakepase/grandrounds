"""Dopo un nuovo candidates.py: riusa le etichette già fatte (chiave: id commento + video)
e prepara blocchi solo per le menzioni ancora da etichettare.
Uso: python reuse_labels.py <work_dir> <old_cand.jsonl> <old_labels_dir> [per_blocco]"""
import json, sys, os, glob

W, old_cand, old_lab = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 350
k2key = {}
for l in open(old_cand, encoding='utf-8'):
    m = json.loads(l); k2key[m['k']] = (m['id'], m['vid'])
done = {}
for p in glob.glob(os.path.join(old_lab, '*.jsonl')):
    for l in open(p, encoding='utf-8'):
        if l.strip():
            d = json.loads(l)
            if d.get('k') in k2key: done[k2key[d['k']]] = d
os.makedirs(os.path.join(W, 'labels'), exist_ok=True)
os.makedirs(os.path.join(W, 'chunks2'), exist_ok=True)
todo, reused = [], 0
with open(os.path.join(W, 'labels', 'reused.jsonl'), 'w', encoding='utf-8') as f:
    for l in open(os.path.join(W, 'cand_mentions.jsonl'), encoding='utf-8'):
        m = json.loads(l)
        d = done.get((m['id'], m['vid']))
        if d:
            f.write(json.dumps({**d, 'k': m['k']}, ensure_ascii=False) + '\n'); reused += 1
        else:
            todo.append(m)
for i in range(0, len(todo), N):
    with open(os.path.join(W, 'chunks2', f'd{i // N:02d}.jsonl'), 'w', encoding='utf-8') as f:
        for m in todo[i:i + N]:
            f.write(json.dumps({'k': m['k'], 'vid': m['vid'], 'sub': m['sub'], 'role': m['role'], 'kind': m['kind'],
                                'score': m['score'], 'text': m['text'][:1000]}, ensure_ascii=False) + '\n')
print('riusate:', reused, '| da etichettare:', len(todo), '| blocchi:', (len(todo) + N - 1) // N)
