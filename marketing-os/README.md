# Kickster Marketing OS

A marketing system that gets better every week. It learns from Kickster's own
results which choices bring in samples and bulk orders, and which don't.

```
   ┌──────────► MAKE ──────────► POST (Salman approves)
   │                                 │
 PLAN                             MEASURE   views, 3s hold, sends, follows,
   ▲                                 │      PRICE comments, DMs → samples → orders
   │                                 ▼
   └────────── LEARN ◄───────────────┘
        playbook.md: works / doesn't / testing / never tried
```

In Claude, say **"run the OS"** and the `kickster-os` skill walks through
the loop.

## How it learns

1. **Every post is tagged** with the six choices that went into it: hook
   formula (the 26 in `ig-reel/hooks.json`), format, length, theme, visual
   style and CTA.
2. **Every post gets a score** against Kickster's own typical post, not
   against some internet average. Score 0 means a typical post, +0.7 roughly
   twice as good, -0.7 half as good. The weights are set by the business
   goal:

   | signal | weight | why |
   |---|---:|---|
   | leads (PRICE comments, DMs, WhatsApp, quotes, samples, bulk) | 40% | the actual goal. A sample is worth 6 points, a bulk order 10 |
   | sends per reach | 20% | the strongest sign people value it |
   | 3-second hold | 15% | whether the hook worked |
   | follows per reach | 15% | whether the profile converted the attention |
   | views | 10% | mostly a function of follower count, so it counts least |

   A reel with 60,000 views and no leads scores below a reel with 4,000
   views that brought in a sample. There's a test for exactly that.
3. **Each choice's own effect** comes from a model that looks at all six
   choices at once. That way a winner gets the credit, not whatever happened
   to appear next to it. Evidence is shrunk toward a starting belief, so one
   lucky post doesn't rewrite the playbook. A choice is only called **WORKS**
   or **DOESN'T** after 3+ posts and a clear margin. Until then it is
   **TESTING**.
4. **The plan follows the evidence:** about 60% of slots use the current
   best choices (EXPLOIT). The rest copy the best recipe and change exactly
   one thing (EXPLORE), so every test teaches something clean. As evidence
   builds up, winners take over the plan and losers drop out.
5. **Lessons the numbers can't hold** go in `journal.md`.
   `data/history.csv` records what the OS believed each week, so you can see
   it change its mind.

The test suite simulates 12 weeks of an account with hidden winners. The OS
finds them, ignores a choice that only looked good because it kept appearing
next to a winner, and shifts its plan toward the winners:

```
python3 -m unittest discover -s marketing-os/tests
```

## Files

| file | what |
|---|---|
| `kos.py` | the engine (Python standard library only) |
| `config.json` | the allowed tags, starting beliefs (priors), score weights, posts per week |
| `data/posts.csv` | every post and its tags. **Source of truth** |
| `data/metrics.csv` | insights per post at each checkpoint (24h, 48h, 7d, 30d) |
| `data/leads.csv` | people who got past commenting, and how far they got |
| `data/history.csv` | the OS's beliefs, one snapshot per `learn` run |
| `playbook.md` | generated: what works, what doesn't, the scoreboard, the funnel |
| `plan.md` | generated: next week's slots |
| `journal.md` | written lessons |

## Commands

```
python3 marketing-os/kos.py status                       # what's missing, open leads
python3 marketing-os/kos.py add-post --id 2026-11-25-moq --first-line "..." \
    --hook 20 --format reel --length 15_30s --theme start_small_moq \
    --style factory_footage --cta comment_PRICE --file reels/x.mp4
python3 marketing-os/kos.py posted 2026-11-25-moq --date 2026-11-25 --url https://instagram.com/reel/...
python3 marketing-os/kos.py add-metrics 2026-11-25-moq --checkpoint 7d \
    --views 5200 --reach 4800 --hold3s 64 --shares 31 --follows 12 --keyword-comments 4
python3 marketing-os/kos.py add-lead --post 2026-11-25-moq --stage dm
python3 marketing-os/kos.py advance-lead L0001 --stage sample
python3 marketing-os/kos.py advance-lead L0001 --stage bulk --value 2400
python3 marketing-os/kos.py learn
python3 marketing-os/kos.py plan
```

## Growing it

- **More channels** (cold email through Apollo, Meta ads, TikTok): add a
  `format` value or a new dimension in `config.json`, and log those posts the
  same way. The engine doesn't care where a post ran.
- **Automatic metrics:** connect Instagram in Windsor.ai (`instagram_public`)
  and the skill pulls insights instead of asking for screenshots.
- **Change what "better" means** by editing `metric_weights`. That is a
  business decision, so make it deliberately.
