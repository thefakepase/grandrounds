# Grand Rounds data

The data behind Grand Rounds: YouTube videos that people in medicine keep recommending to each
other on Reddit, plus the health and medicine picks of Hacker News (via HackerTube).

## For AI agents: start here

Two files, both plain JSON, both fit in memory.

| file | shape | key |
|---|---|---|
| `videos.json` | `{generated, stats, areas, videos[]}` | `videos[].vid` (11-char YouTube id) |
| `mentions.json` | `{vid: [note, ...]}` | `vid` → `videos[].vid` |

`videos[]` fields: `vid`, `t` title, `ch` channel, `s` summary, `w` one line on why clinicians point
others to it, `ct` content type, `lv` level, `shelf` (evergreen / dated / news), `cat` 1–3 category
ids from `areas[].cats[]`, `tags`, `sc` score, `r` distinct recommenders by role, `crit` critical
mentions (clinicians + HN), `y0`/`y1` years of the mentions, `rel` videos recommended by the same people,
no durations or view counts: YouTube's API terms do not allow redistributing them. Fetch them with
your own free YouTube Data API key (`videos.list`, 50 ids per request, 1 quota unit each).

Roles in `r` and in notes: `md` physician, `res` resident, `stu` med student, `rn` nurse, `rx`
pharmacist, `ems` EMS, `hn` Hacker News, `oth` everyone else. Roles come from self-reported Reddit
flair, or from the subreddit when there is no flair (r/Residency → resident; r/medicalschool,
r/step1, r/Step2, r/usmle, r/medicalschoolanki, r/medicalschooluk → student; r/nursing,
r/StudentNurse, r/NursingUK → nurse; r/pharmacy → pharmacist; r/Paramedics, r/ems → EMS;
r/doctorsUK → physician).

Each note: `role`, `sub`, `st` stance (`strong_rec`, `rec`, `reference`, `critical`, `joke`), `why`
(≤15 words), `q` a verbatim quote, `tx` the comment (cut at 500 chars), `url` the original comment,
`m` month. Usernames are deliberately left out.

`sc` = distinct months with a recommendation + 0.5 × months with a strong recommendation + 0.5 ×
distinct clinician recommenders (+ the HackerTube score for HN videos).

Thumbnails: `https://i.ytimg.com/vi/<vid>/hq2.jpg` (automatic frame from the middle of the video).
Player: `https://www.youtube-nocookie.com/embed/<vid>`.

## How it was made

1. Comments and posts from 39 medical subreddits, 2008–2024, from the Arctic Shift Reddit archive
   (top-40k subreddits dump, through 2024-12). Kept: those linking a YouTube video with at least 80
   characters of their own text (posts: any link post with a real title). Links in lists of more than
   3 videos dropped. On r/AskDocs only comments by flaired (verified) medical professionals count.
2. A video becomes a candidate when at least 2 different people link it. Up to 12 mentions per video.
3. Claude (Sonnet) labeled each mention's stance, a short "why" and a verbatim quote.
4. Claude wrote a card per video (summary, why, type, level, shelf life, categories) and dropped
   videos that are not about medicine or health.
5. Kept: videos with at least 2 distinct recommenders, still public and embeddable.
6. HN part: videos from the HackerTube export in health categories (and AI videos about medicine).

LLM labels are good, not perfect: expect a few percent of noise.

## License and attribution

Reddit comments remain the work of their authors; only short excerpts are included, with links.
HN part derived from HackerTube (https://hackertube.org), ODC-By, from the open-index/hacker-news
dataset. Video titles and channel names belong to their creators. Not affiliated with YouTube,
Reddit, Hacker News or HackerTube. Not medical advice.
