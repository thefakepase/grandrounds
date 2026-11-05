"""Estrae dai dump Reddit (.zst ndjson) i commenti e i post che linkano un video YouTube.
Uso: python extract.py <cartella_dump> <out.jsonl>
Regole prese da HackerTube: il commento deve avere almeno MIN_OWN caratteri di testo proprio."""
import json, re, sys, os, io, glob
import zstandard

MIN_OWN = 80
YT = re.compile(r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:[^\s)\]]*?&)?v=|embed/|live/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})')
URL = re.compile(r'https?://\S+|\[([^\]]*)\]\([^)]*\)')
BOTS = {'AutoModerator', '[deleted]', '[removed]'}

def lines(path):
    with open(path, 'rb') as fh:
        r = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(fh)
        for line in io.TextIOWrapper(r, encoding='utf-8', errors='replace'):
            yield line

def own_text(t):
    return URL.sub(lambda m: m.group(1) or '', t).strip()

def main(src, out):
    n = 0
    with open(out, 'w', encoding='utf-8') as fo:
        for path in sorted(glob.glob(os.path.join(src, '**', '*.zst'), recursive=True)):
            base = os.path.basename(path)
            kind = 'comment' if base.endswith('_comments.zst') else 'post'
            k = 0
            for line in lines(path):
                if 'youtu' not in line:
                    continue
                d = json.loads(line)
                if d.get('author') in BOTS:
                    continue
                if kind == 'comment':
                    text = d.get('body') or ''
                else:
                    text = (d.get('title') or '') + '\n' + (d.get('selftext') or '') + '\n' + (d.get('url') or '')
                vids = list(dict.fromkeys(YT.findall(text)))
                if not vids or len(vids) > 3:  # liste di link = playlist/spam, si scartano
                    continue
                own = own_text(text)
                if kind == 'comment' and len(own) < MIN_OWN:
                    continue
                if kind == 'post' and len(own) < 15:
                    continue
                for v in vids:
                    fo.write(json.dumps({
                        'vid': v, 'kind': kind, 'id': d.get('id'),
                        'sub': d.get('subreddit'), 'author': d.get('author'),
                        'flair': d.get('author_flair_text'),
                        'score': d.get('score'), 'utc': int(float(d.get('created_utc') or 0)),
                        'link_id': d.get('link_id'), 'permalink': d.get('permalink'),
                        'text': text[:1500],
                    }, ensure_ascii=False) + '\n')
                    k += 1
            n += k
            print(f'{base}: {k}', flush=True)
    print('totale', n)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
