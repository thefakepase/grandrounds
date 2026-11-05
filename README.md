# Grand Rounds

YouTube videos that people in medicine keep recommending to each other on Reddit, with Hacker News
(via HackerTube) as an extra signal. Static site, no accounts, state in the browser.

- `docs/`: the site, served by GitHub Pages (open `docs/index.html` through any static server; deploy the folder as is)
- `pipeline/`: how the data was made
  1. `extract.py`: YouTube links from Arctic Shift subreddit dumps (.zst)
  2. `candidates.py`: role from flair/subreddit, candidate videos (2+ distinct people)
  3. labeling with Claude Sonnet: `prompt_label.md`
  4. `meta.py`: oEmbed (no key) or YouTube Data API (`YOUTUBE_API_KEY` or `~/.config/medtube/.env`)
  5. `cards_input.py` + cards with Claude Sonnet: `prompt_card.md`, `taxonomy.json`
  6. `build.py`: `docs/data/videos.json`, `mentions.json`, `grandrounds-data.zip`

Local preview: `python -m http.server 8765 --directory docs`

## Credits

Idea and method from [HackerTube](https://hackertube.org) by Andrej Karpathy
([post](https://karpathy.bearblog.dev/hacker-tube/)). Reddit data from the
[Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift) archive; Hacker News part from the
HackerTube data export (ODC-By). Titles, durations and view counts from the YouTube Data API.
Comments remain the work of their authors; usernames are not stored. Not affiliated with YouTube,
Reddit, Hacker News or HackerTube. Not medical advice.
