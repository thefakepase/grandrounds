"""Metadati dei video. Senza chiave: oEmbed (titolo, canale, esiste/embeddabile).
Con YOUTUBE_API_KEY (variabile d'ambiente o ~/.config/medtube/.env): durata, visualizzazioni, data.
Cache incrementale: non richiede mai due volte lo stesso video.
Uso: python meta.py <vids.json> <cache.jsonl>"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

def key():
    k = os.environ.get('YOUTUBE_API_KEY')
    p = os.path.expanduser('~/.config/medtube/.env')
    if not k and os.path.exists(p):
        for line in open(p, encoding='utf-8'):
            if line.strip().startswith('YOUTUBE_API_KEY='):
                k = line.split('=', 1)[1].strip().strip('"\'')
    return k or None

def oembed(vid):
    u = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(f'https://www.youtube.com/watch?v={vid}')
    for attempt in range(3):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'grandrounds-builder'}), timeout=20))
            return {'vid': vid, 'src': 'oembed', 'ok': True, 'title': d.get('title'), 'channel': d.get('author_name')}
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404):
                return {'vid': vid, 'src': 'oembed', 'ok': False, 'code': e.code}
            time.sleep(2 + attempt * 3)
        except Exception:
            time.sleep(2 + attempt * 3)
    return None  # riprova al prossimo giro

def iso_dur(s):
    import re
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    if not m: return None
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se

def api(vids, k):
    out = []
    for i in range(0, len(vids), 50):
        ids = vids[i:i + 50]
        q = urllib.parse.urlencode({'part': 'snippet,contentDetails,statistics,status', 'id': ','.join(ids), 'key': k})
        items = json.load(urllib.request.urlopen(f'https://www.googleapis.com/youtube/v3/videos?{q}', timeout=30))['items']
        got = {it['id']: it for it in items}
        for v in ids:
            it = got.get(v)
            if not it:
                out.append({'vid': v, 'src': 'api', 'ok': False}); continue
            out.append({'vid': v, 'src': 'api', 'ok': it['status'].get('embeddable', True) and it['status'].get('privacyStatus') != 'private',
                        'title': it['snippet']['title'], 'channel': it['snippet']['channelTitle'],
                        'published': it['snippet'].get('publishedAt', '')[:10],
                        'dur': iso_dur(it['contentDetails'].get('duration')),
                        'views': int(it['statistics'].get('viewCount', 0) or 0)})
        time.sleep(0.2)
    return out

def main(vids_path, cache):
    vids = json.load(open(vids_path))
    done = {}
    if os.path.exists(cache):
        for line in open(cache, encoding='utf-8'):
            d = json.loads(line); done[d['vid']] = d
    k = key()
    with open(cache, 'a', encoding='utf-8') as f:
        if k:
            todo = [v for v in vids if done.get(v, {}).get('src') != 'api']
            for d in api(todo, k):
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
            print('API:', len(todo), 'video')
        else:
            todo = [v for v in vids if v not in done]
            with ThreadPoolExecutor(8) as ex:
                for n, d in enumerate(ex.map(oembed, todo)):
                    if d: f.write(json.dumps(d, ensure_ascii=False) + '\n')
                    if n % 500 == 0: print(n, '/', len(todo), flush=True)
            print('oEmbed:', len(todo), 'video (nessuna chiave API: niente durata/visualizzazioni)')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
