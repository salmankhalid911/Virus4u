---
name: kickster-os
description: >-
  Run the Kickster Marketing OS weekly learning loop: measure last week's
  posts and leads, learn what works and what doesn't, plan next week from the
  evidence, then make and log the content. Use when Salman says "run the OS",
  "weekly review", "what's working", "plan next week", "log this post",
  "record these insights", "I got a lead / sample / order from a reel", or
  pastes Instagram insights.
---

# kickster-os

The Marketing OS lives in `marketing-os/`. Its memory is the CSV files in
`marketing-os/data/`. `marketing-os/kos.py` does the maths. This skill is the
operator: it gathers the numbers, runs the maths, reads the result honestly
and turns it into next week's work.

**Source of truth:** `marketing-os/data/posts.csv`, not
`.claude/instagram/log.md`. Keep appending to `log.md` too, because the
`ig-*` skills read it.

## The loop (run weekly, same day each week)

### 1. Measure

```
python3 marketing-os/kos.py status
```

This lists every posted post that is missing its 24h or 7d numbers, plus
open leads.

- **Post metrics.** If the Windsor.ai connector has `instagram_public`
  connected, pull the per-media insights with `get_data`. Otherwise ask Salman
  for an Insights screenshot of each post. The numbers that matter are views,
  reach, % non-followers, 3-second hold, average watch time, shares (sends),
  saves, follows, and the count of **PRICE** comments. Record them with:
  `kos.py add-metrics <post_id> --checkpoint 7d --views .. --reach .. --hold3s .. --shares .. --follows .. --keyword-comments ..`
  Leave out what you don't have. Never guess a number.
- **Leads.** Ask: "Who DMed, moved to WhatsApp, asked for a quote, paid for a
  sample, or placed a bulk order this week, and which post brought them in?"
  New person: `kos.py add-lead --post <post_id> --stage dm`. Moved forward:
  `kos.py advance-lead <L000N> --stage sample` (bulk: add `--value`). Leads
  carry most of the score, because samples and orders are the goal. Don't
  write a client's name in the note unless Salman is fine with it.

### 2. Learn

```
python3 marketing-os/kos.py learn
```

Read `marketing-os/playbook.md` and report to Salman in plain words:

- What works, what doesn't, and what is promising but unproven, each with its
  post count. Say how sure the system is. Below 10 measured posts, everything
  is a hunch, so say exactly that.
- Separate **reach** problems from **conversion** problems (see `ig-audit`).
  Views with no PRICE comments is a CTA or offer problem. A good hook won't
  fix it.
- Then add 2-4 dated lines to `marketing-os/journal.md`. These are the things
  the numbers can't hold: questions people asked in comments, objections in
  DMs, what the best post did that the tags don't capture. When the same
  lesson shows up three times, suggest making it official: a new theme or
  style value in `config.json`, or a changed prior. Salman approves config
  changes.

### 3. Plan

```
python3 marketing-os/kos.py plan
```

`plan.md` gives finished drafts to post first, then new slots. **EXPLOIT**
slots use the best evidence. **EXPLORE** slots copy the best recipe and change
one thing. Turn each slot into a real angle using `ig-plan` (take it from
something that actually happened this week) and write the hook with `ig-reel`,
keeping to the slot's hook formula. If a slot clashes with `voice.md`, follow
`voice.md`, then say so and tag the post with what you actually made. For
example, #19 The Deadline needs a real deadline, never a made-up one.

### 4. Make and log

Make the content with the usual skills. The moment a piece exists, log it
with tags that describe **what it really is**, not what the slot asked for:

```
python3 marketing-os/kos.py add-post --id YYYY-MM-DD-slug --first-line "..." \
  --hook <id> --format reel --length 15_30s --theme <theme> \
  --style <style> --cta comment_PRICE --file reels/<file>.mp4
```

Allowed values are in `marketing-os/config.json`. The script rejects anything
else.

### 5. Post (only with approval)

Nothing gets posted without Salman's explicit approval. After it's live, run
`kos.py posted <id> --date YYYY-MM-DD --url <link>`.

## Guardrails

- Never invent metrics, leads or results, and never back-fill a number you
  are unsure of.
- An honest tag matters more than a complete one. A wrong tag teaches the
  system the wrong lesson.
- Don't change `metric_weights` or `priors` without Salman's say-so. Those
  settings define what "better" means.
- Commit the `marketing-os/` changes after each weekly run, so the history of
  what the OS believed stays in git.
