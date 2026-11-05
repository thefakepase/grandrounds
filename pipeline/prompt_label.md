You are labeling Reddit comments from medical subreddits that link a YouTube video.
Input: a JSONL file, one mention per line, with fields `k` (id), `vid`, `sub`, `role`, `kind`
(comment or post), `score`, `text` (the comment, or for posts: title + body + url).

For EVERY line, write one JSON line to the output file with exactly these fields:
- `k`: same id
- `st`: one of
  - `strong_rec`: enthusiastic recommendation ("best explanation I've ever seen", "every resident should watch this")
  - `rec`: points people to the video as worth watching or useful
  - `reference`: cites it neutrally, as a source or an example, without recommending it
  - `critical`: criticizes, debunks or warns against the video or its creator
  - `joke`: meme, punchline, music, comedy reaction with no learning value claimed (a medical comedy sketch recommended as great satire is `rec`)
  - `promo`: self-promotion of one's own channel or product
  - `other`: patient asking for help, off-topic, unclear, video not the point
- `why`: at most 15 words on what a viewer gets from the video according to this comment (empty for joke/promo/other/critical; for critical: what is wrong with it)
- `q`: a short verbatim excerpt (max 30 words) copied exactly from `text` that best shows the stance; empty if none fits. Never include usernames or personal details about patients.

Rules: judge the stance toward THE VIDEO, not the topic. The video id is in `vid`; if a comment links
several videos, judge only this one. Be strict: a plain link with no endorsement is `reference`.
Output valid JSONL only, one line per input line, same order. Do not skip lines.
