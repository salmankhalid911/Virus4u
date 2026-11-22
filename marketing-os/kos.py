#!/usr/bin/env python3
"""Kickster Marketing OS: log -> measure -> learn -> plan.

Every post is tagged with the choices that went into it (hook formula, format,
length, theme, visual style, CTA). Every post is scored against the account's
own typical post, with leads and orders weighted far above views. Each choice
then builds up a track record, gets a verdict (WORKS / DOESN'T / TESTING /
UNTESTED), and next week's plan is drawn from those track records: most slots
use what is winning, and the rest each change one variable to test something.

Standard library only. Data lives in CSV files under data/ so it can be read,
edited and versioned by hand.

    python3 kos.py status
    python3 kos.py add-post --id 2026-11-25-moq --first-line "..." --hook 20 \
        --format reel --length 15_30s --theme start_small_moq \
        --style factory_footage --cta comment_PRICE
    python3 kos.py posted 2026-11-25-moq --date 2026-11-25 --url https://...
    python3 kos.py add-metrics 2026-11-25-moq --checkpoint 7d --views 5200 \
        --reach 4800 --hold3s 64 --shares 31 --follows 12 --keyword-comments 4
    python3 kos.py add-lead --post 2026-11-25-moq --stage dm
    python3 kos.py advance-lead L0001 --stage sample
    python3 kos.py learn      # rewrites playbook.md
    python3 kos.py plan       # rewrites plan.md
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path

HOME = Path(os.environ.get("KOS_HOME", Path(__file__).resolve().parent))
DATA = HOME / "data"
HOOKS_FILE = Path(__file__).resolve().parent.parent / ".claude/skills/ig-reel/hooks.json"

POST_FIELDS = ["post_id", "created", "status", "posted_date", "url", "file", "first_line",
               "hook_formula", "format", "length_bucket", "theme", "visual_style", "cta", "notes"]
METRIC_FIELDS = ["post_id", "checkpoint", "recorded", "views", "reach", "non_follower_pct",
                 "hold_3s_pct", "avg_watch_s", "likes", "comments", "saves", "shares",
                 "follows", "profile_visits", "keyword_comments"]
LEAD_FIELDS = ["lead_id", "created", "updated", "source_post_id", "stage", "order_value", "note"]
HISTORY_FIELDS = ["run_date", "dimension", "value", "n", "score", "verdict"]

CHECKPOINT_ORDER = {"24h": 1, "48h": 2, "7d": 3, "30d": 4}
STAGE_ORDER = ["dm", "whatsapp", "quote", "sample", "bulk", "lost"]


# ---------------------------------------------------------------- storage

def load_config() -> dict:
    return json.loads((HOME / "config.json").read_text())


def read_csv(name: str, fields: list[str]) -> list[dict]:
    path = DATA / name
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return [{k: (row.get(k) or "") for k in fields} for row in csv.DictReader(f)]


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def today() -> str:
    return dt.date.today().isoformat()


def num(x) -> float | None:
    try:
        return float(x) if x not in ("", None) else None
    except ValueError:
        return None


def hook_names() -> dict[str, str]:
    try:
        return {str(h["id"]): h["name"] for h in json.loads(HOOKS_FILE.read_text())["hooks"]}
    except (OSError, KeyError, ValueError):
        return {}


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


# ---------------------------------------------------------------- scoring

def latest_metrics(metrics: list[dict]) -> dict[str, dict]:
    """The most mature checkpoint recorded for each post."""
    best: dict[str, dict] = {}
    for m in metrics:
        rank = CHECKPOINT_ORDER.get(m["checkpoint"], 0)
        cur = best.get(m["post_id"])
        if cur is None or rank >= CHECKPOINT_ORDER.get(cur["checkpoint"], 0):
            best[m["post_id"]] = m
    return best


def lead_points(post_id: str, metric: dict | None, leads: list[dict], cfg: dict) -> float:
    pts = cfg["lead_stage_points"]
    total = (num(metric.get("keyword_comments")) or 0) * pts["keyword_comment"] if metric else 0.0
    for lead in leads:
        if lead["source_post_id"] == post_id and lead["stage"] in pts:
            total += pts[lead["stage"]]
    return total


def raw_signals(metric: dict, leads_pts: float) -> dict[str, float]:
    """Per-post raw values for each weighted signal. Rates are per 1,000 reach."""
    out: dict[str, float] = {}
    views, reach = num(metric.get("views")), num(metric.get("reach"))
    if views is not None:
        out["views"] = views
    if num(metric.get("hold_3s_pct")) is not None:
        out["hold_3s_pct"] = num(metric["hold_3s_pct"])
    base = reach or views
    if base:
        if num(metric.get("shares")) is not None:
            out["sends_per_reach"] = 1000 * num(metric["shares"]) / base
        if num(metric.get("follows")) is not None:
            out["follows_per_reach"] = 1000 * num(metric["follows"]) / base
    out["leads"] = leads_pts
    return out


def score_posts(posts, metrics, leads, cfg) -> dict[str, dict]:
    """Score = weighted mean of log(value / account median). 0 = a typical post."""
    latest = latest_metrics(metrics)
    signals = {}
    for p in posts:
        if p["status"] == "posted" and p["post_id"] in latest:
            m = latest[p["post_id"]]
            signals[p["post_id"]] = raw_signals(m, lead_points(p["post_id"], m, leads, cfg))
    if not signals:
        return {}
    weights = cfg["metric_weights"]
    medians = {}
    for key in weights:
        vals = [s[key] for s in signals.values() if key in s]
        if vals:
            medians[key] = statistics.median(vals)
    scored = {}
    for pid, sig in signals.items():
        parts, wsum = {}, 0.0
        for key, w in weights.items():
            if key in sig and key in medians:
                parts[key] = max(-3.0, min(3.0, math.log((sig[key] + 1) / (medians[key] + 1))))
                wsum += w
        score = sum(weights[k] * v for k, v in parts.items()) / wsum if wsum else 0.0
        scored[pid] = {"score": score, "parts": parts, "signals": sig}
    return scored


# ---------------------------------------------------------------- learning

def _invert(a: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan inverse of a small symmetric positive-definite matrix."""
    n = len(a)
    m = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        d = m[c][c]
        m[c] = [x / d for x in m[c]]
        for r in range(n):
            if r != c and m[r][c]:
                f = m[r][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [row[n:] for row in m]


def learn_dimensions(posts, scored, cfg) -> dict[str, dict[str, dict]]:
    """Estimate every choice's own effect at once (ridge regression on one-hot tags).

    Fitting all dimensions together separates choices that tend to appear
    together: if factory footage always ships with the PRICE CTA, the model
    can still tell which of the two is doing the work (given a few posts that
    vary one and not the other - which is what EXPLORE slots are for).
    The ridge pulls each effect toward its prior, so thin evidence stays humble.
    """
    lc = cfg["learning"]
    k, min_n, margin = lc["prior_strength"], lc["min_posts_for_verdict"], lc["verdict_margin"]
    priors = cfg.get("priors", {})
    by_id = {p["post_id"]: p for p in posts}
    feats = [(d, v) for d, vals in cfg["dimensions"].items() for v in vals]
    index = {f: i for i, f in enumerate(feats)}
    prior_vec = [priors.get(d, {}).get(v, 0.0) for d, v in feats]

    rows, ys, counts = [], [], [0] * len(feats)
    for pid, sc in scored.items():
        active = [index[(d, by_id[pid].get(d, ""))] for d in cfg["dimensions"]
                  if (d, by_id[pid].get(d, "")) in index]
        rows.append(active)
        ys.append(sc["score"])
        for i in active:
            counts[i] += 1
    n_obs, p = len(ys), len(feats)
    # Column p is an unpenalised intercept (the account's baseline post).
    P = p + 1
    xtx = [[0.0] * P for _ in range(P)]
    xty = [k * prior_vec[i] for i in range(p)] + [0.0]
    for active, y in zip(rows, ys):
        cols = active + [p]
        for i in cols:
            xty[i] += y
            for j in cols:
                xtx[i][j] += 1.0
    for i in range(p):
        xtx[i][i] += k
    xtx[p][p] += 1e-6
    inv = _invert(xtx)
    full = [sum(inv[i][j] * xty[j] for j in range(P)) for i in range(P)]
    beta, intercept = full[:p], full[p]

    if n_obs >= 8:
        resid = [y - intercept - sum(beta[i] for i in a) for a, y in zip(rows, ys)]
        sigma = math.sqrt(sum(r * r for r in resid) / max(1, n_obs - 1))
    else:
        sigma = 0.7
    sigma = max(sigma, 0.2)

    result: dict[str, dict[str, dict]] = {}
    for d, vals in cfg["dimensions"].items():
        stats = {}
        for v in vals:
            i = index[(d, v)]
            n, mean, se = counts[i], beta[i], sigma * math.sqrt(inv[i][i])
            if n == 0:
                verdict = "UNTESTED"
            elif n >= min_n and mean - se > margin:
                verdict = "WORKS"
            elif n >= min_n and mean + se < -margin:
                verdict = "DOESN'T"
            else:
                verdict = "TESTING"
            stats[v] = {"n": n, "mean": mean, "se": se, "verdict": verdict}
        result[d] = stats
    return result


def label(dim: str, value: str, hooks: dict[str, str]) -> str:
    if dim == "hook_formula" and value in hooks:
        return f"#{value} {hooks[value]}"
    return value


# ---------------------------------------------------------------- planning

def thompson(stats: dict[str, dict], rng: random.Random, pool: list[str]) -> str:
    return max(pool, key=lambda v: rng.gauss(stats[v]["mean"], stats[v]["se"]))


def best_combo(learned) -> dict[str, str]:
    combo = {}
    for dim, stats in learned.items():
        tested = [v for v, s in stats.items() if s["n"] > 0 and s["verdict"] != "DOESN'T"]
        pool = tested or [v for v, s in stats.items() if s["verdict"] != "DOESN'T"]
        combo[dim] = max(pool, key=lambda v: (stats[v]["mean"], stats[v]["n"]))
    return combo


def normalise(slot: dict[str, str]) -> dict[str, str]:
    if slot.get("format") != "reel":
        slot["length_bucket"] = "n/a"
    return slot


def pick_drafts(drafts: list[dict], limit: int) -> list[dict]:
    """Oldest first, but never two drafts with the same hook+theme in one week."""
    chosen, seen = [], set()
    for d in sorted(drafts, key=lambda d: d["post_id"]):
        key = (d["hook_formula"], d["theme"])
        if key not in seen and len(chosen) < limit:
            chosen.append(d)
            seen.add(key)
    return chosen


def make_plan(learned, cfg, week: str, n_drafts: int = 0) -> list[dict]:
    rng = random.Random(week)
    pc = cfg["planning"]
    total = max(1, pc["posts_per_week"] - n_drafts)
    n_explore = max(1, round(total * pc["explore_share"])) if total > 1 else 0
    n_exploit = total - n_explore
    variety = set(pc.get("variety_dimensions", ["hook_formula", "theme"]))
    theme_count: dict[str, int] = {}
    slots: list[dict] = []

    def theme_ok(s):
        return theme_count.get(s["theme"], 0) < 2

    # Exploit: sample from what has evidence (Thompson sampling over tested values).
    for _ in range(n_exploit):
        for _attempt in range(30):
            s = {}
            for dim, stats in learned.items():
                alive = [v for v, st in stats.items() if st["verdict"] != "DOESN'T"]
                tested = [v for v in alive if stats[v]["n"] > 0]
                if dim in variety:
                    s[dim] = thompson(stats, rng, alive)      # content should vary week to week
                elif tested:
                    s[dim] = thompson(stats, rng, tested)     # follow the evidence
                else:
                    s[dim] = max(alive, key=lambda v: stats[v]["mean"])  # strongest starting belief
            if theme_ok(s):
                break
        s = normalise(s)
        theme_count[s["theme"]] = theme_count.get(s["theme"], 0) + 1
        slots.append({"kind": "EXPLOIT", "choices": s, "changed": None})

    # Explore: take the current best recipe and change exactly ONE thing, so the
    # result says something clean about that one thing.
    base = best_combo(learned)
    dims = sorted(learned, key=lambda d: sum(st["n"] for st in learned[d].values()))
    for i in range(n_explore):
        dim = dims[i % len(dims)]
        stats = learned[dim]
        candidates = [v for v, st in stats.items()
                      if v != base[dim] and st["verdict"] in ("UNTESTED", "TESTING")]
        if not candidates:
            continue
        # Prefer the least-tested values; break ties with an optimistic sample.
        fewest = min(stats[v]["n"] for v in candidates)
        pool = [v for v in candidates if stats[v]["n"] <= fewest + 1]
        s = dict(base)
        s[dim] = thompson(stats, rng, pool)
        s = normalise(s)
        theme_count[s["theme"]] = theme_count.get(s["theme"], 0) + 1
        slots.append({"kind": "EXPLORE", "choices": s, "changed": dim})
    return slots


# ---------------------------------------------------------------- reports

def fmt_pct(x):
    return "-" if x is None else f"{x:.0f}%"


def write_playbook(posts, metrics, leads, cfg) -> str:
    scored = score_posts(posts, metrics, leads, cfg)
    learned = learn_dimensions(posts, scored, cfg)
    hooks = hook_names()
    by_id = {p["post_id"]: p for p in posts}
    posted = [p for p in posts if p["status"] == "posted"]
    L = [f"# {cfg['brand']} Playbook", "",
         f"_Generated by `kos.py learn` on {today()}. Do not edit by hand: change the data and re-run._", "",
         f"**Goal:** {cfg['goal']}", "",
         f"**Evidence:** {len(scored)} measured posts, {len(posted)} posted, "
         f"{len([p for p in posts if p['status'] == 'draft'])} drafts, {len(leads)} leads.", ""]
    if len(scored) < 10:
        L += ["> **Early days.** With fewer than 10 measured posts every verdict below is a hunch, "
              "not a finding. The system says TESTING until a choice has at least "
              f"{cfg['learning']['min_posts_for_verdict']} posts and a clear margin.", ""]

    if scored:
        ranked = sorted(scored.items(), key=lambda kv: kv[1]["score"], reverse=True)
        L += ["## Scoreboard", "",
              "Post score 0 = a typical post for this account. +0.7 is roughly twice as good; -0.7 half.", "",
              "| score | post | hook | theme | style | views | hold@3s | sends/1k | follows/1k | lead pts |",
              "|---:|---|---|---|---|---:|---:|---:|---:|---:|"]
        for pid, s in ranked:
            p, sig = by_id[pid], s["signals"]
            L.append(f"| {s['score']:+.2f} | {p['first_line'][:48] or pid} | "
                     f"{label('hook_formula', p['hook_formula'], hooks)} | {p['theme']} | {p['visual_style']} | "
                     f"{sig.get('views', 0):,.0f} | {fmt_pct(sig.get('hold_3s_pct'))} | "
                     f"{sig.get('sends_per_reach', 0):.1f} | {sig.get('follows_per_reach', 0):.1f} | "
                     f"{sig.get('leads', 0):.0f} |")
        L.append("")

    for verdict, title, blurb in [
        ("WORKS", "What works", "Keep doing these. They beat the account's typical post with enough posts behind them."),
        ("DOESN'T", "What doesn't work", "Stop these. They underperform with enough posts behind them."),
        ("TESTING", "Still testing", "Some evidence, not enough to call. Sorted by how promising they look."),
    ]:
        rows = [(dim, v, st) for dim, stats in learned.items() for v, st in stats.items() if st["verdict"] == verdict]
        rows.sort(key=lambda r: r[2]["mean"], reverse=True)
        L += [f"## {title}", "", blurb, ""]
        if rows:
            L += ["Effect = this choice's own contribution to a post's score, with every other choice held "
                  "constant, shrunk toward the starting belief while evidence is thin.", "",
                  "| dimension | choice | posts | effect | ± |", "|---|---|---:|---:|---:|"]
            L += [f"| {d} | {label(d, v, hooks)} | {st['n']} | {st['mean']:+.2f} | {st['se']:.2f} |" for d, v, st in rows]
        else:
            L.append("_Nothing yet._")
        L.append("")

    untested = {d: [label(d, v, hooks) for v, st in s.items() if st["verdict"] == "UNTESTED"] for d, s in learned.items()}
    L += ["## Never tried", ""]
    L += [f"- **{d}:** {', '.join(vs)}" for d, vs in untested.items() if vs]
    L.append("")

    # Funnel
    stages: dict[str, int] = {}
    for lead in leads:
        stages[lead["stage"]] = stages.get(lead["stage"], 0) + 1
    kw = sum(num(m["keyword_comments"]) or 0 for m in latest_metrics(metrics).values())
    revenue = sum(num(l["order_value"]) or 0 for l in leads if l["stage"] == "bulk")
    L += ["## Funnel", "",
          f"keyword comments {kw:.0f} → " + " → ".join(f"{s} {stages.get(s, 0)}" for s in STAGE_ORDER[:-1])
          + f" (lost {stages.get('lost', 0)})", ""]
    if revenue:
        L += [f"Bulk order value attributed to posts: {revenue:,.0f}", ""]

    gaps = data_gaps(posts, metrics)
    if gaps:
        L += ["## Data gaps", "", "These posts are old enough to measure but have no numbers yet. "
              "The system cannot learn from them until they do.", ""]
        L += [f"- `{pid}`: needs {cp} metrics" for pid, cp in gaps]
        L.append("")

    (HOME / "playbook.md").write_text("\n".join(L))
    hist = read_csv("history.csv", HISTORY_FIELDS)
    hist = [h for h in hist if h["run_date"] != today()]
    for dim, stats in learned.items():
        for v, st in stats.items():
            if st["n"]:
                hist.append({"run_date": today(), "dimension": dim, "value": v, "n": st["n"],
                             "score": f"{st['mean']:.3f}", "verdict": st["verdict"]})
    write_csv("history.csv", HISTORY_FIELDS, hist)
    return "\n".join(L)


def data_gaps(posts, metrics) -> list[tuple[str, str]]:
    have = {(m["post_id"], m["checkpoint"]) for m in metrics}
    out = []
    for p in posts:
        if p["status"] != "posted" or not p["posted_date"]:
            continue
        age = (dt.date.today() - dt.date.fromisoformat(p["posted_date"])).days
        if age >= 7 and (p["post_id"], "7d") not in have:
            out.append((p["post_id"], "7d"))
        elif 1 <= age < 7 and not any(pid == p["post_id"] for pid, _ in have):
            out.append((p["post_id"], "24h"))
    return out


def write_plan(posts, metrics, leads, cfg, week: str) -> str:
    scored = score_posts(posts, metrics, leads, cfg)
    learned = learn_dimensions(posts, scored, cfg)
    hooks = hook_names()
    drafts = [p for p in posts if p["status"] == "draft"]
    this_week = pick_drafts(drafts, cfg["planning"].get("max_drafts_per_week", 2))
    backlog = [d for d in drafts if d not in this_week]
    slots = make_plan(learned, cfg, week, len(this_week))
    L = [f"# Plan for {week}", "",
         f"_Generated by `kos.py plan` on {today()} from {len(scored)} measured posts._", ""]
    if not scored:
        L += ["> No measured posts yet, so the new slots below come from starting beliefs in "
              "`config.json` (priors), not evidence. Post, measure, and the plan will start following the data.", ""]

    def draft_line(p):
        return (f"- `{p['post_id']}`: \"{p['first_line']}\" "
                f"({label('hook_formula', p['hook_formula'], hooks)}, {p['theme']}, {p['visual_style']})"
                + (f" → `{p['file']}`" if p["file"] else ""))
    if this_week:
        L += ["## Already made: post these this week", "",
              "Finished and unposted. Posting them is the cheapest way to get evidence. "
              "When you post one: `kos.py posted <id> --date YYYY-MM-DD --url <link>`.", ""]
        L += [draft_line(p) for p in this_week] + [""]
    if backlog:
        L += ["## Draft backlog (later weeks)", "",
              "Held back so the week does not repeat the same hook and theme. "
              "If two drafts are near-duplicates (e.g. a 15s and 21s cut), post one, or post both "
              "weeks apart as a deliberate length test.", ""]
        L += [draft_line(p) for p in backlog] + [""]
    L += ["## New slots", "",
          "**EXPLOIT** slots use what the evidence favours. **EXPLORE** slots copy the best recipe "
          "and change exactly one thing, so the result teaches us something clean.", ""]
    for i, s in enumerate(slots, 1):
        c = s["choices"]
        why = ("Uses current best-evidence choices." if s["kind"] == "EXPLOIT"
               else f"Test: **{s['changed']} = {label(s['changed'], c[s['changed']], hooks)}** "
                    f"(posts so far: {learned[s['changed']][c[s['changed']]]['n']}). Everything else is the current best recipe.")
        L += [f"### Slot {i} · {s['kind']}", "",
              f"- Hook formula: {label('hook_formula', c['hook_formula'], hooks)}",
              f"- Format: {c['format']}" + (f", {c['length_bucket']}" if c["length_bucket"] != "n/a" else ""),
              f"- Theme: {c['theme']}",
              f"- Visual style: {c['visual_style']}",
              f"- CTA: {c['cta']}",
              f"- Why: {why}", ""]
    L += ["## Rules that do not change", "",
          "- Every slot still goes through `voice.md`: proof list only, no fake urgency, no invented numbers.",
          "- Nothing is posted without Salman's approval.",
          "- Log each post with `kos.py add-post` the moment it is made, and tag it honestly. "
          "A wrong tag teaches the system the wrong lesson.", ""]
    (HOME / "plan.md").write_text("\n".join(L))
    return "\n".join(L)


# ---------------------------------------------------------------- commands

def validate_choice(cfg, dim, value):
    if value and value != "n/a" and value not in cfg["dimensions"][dim]:
        die(f"{dim} '{value}' is not in config.json. Allowed: {', '.join(cfg['dimensions'][dim])}")


def cmd_add_post(a, cfg):
    posts = read_csv("posts.csv", POST_FIELDS)
    if any(p["post_id"] == a.id for p in posts):
        die(f"post '{a.id}' already exists")
    row = {"post_id": a.id, "created": today(), "status": a.status, "posted_date": a.date or "",
           "url": a.url or "", "file": a.file or "", "first_line": a.first_line,
           "hook_formula": a.hook, "format": a.format, "length_bucket": a.length if a.format == "reel" else "n/a",
           "theme": a.theme, "visual_style": a.style, "cta": a.cta, "notes": a.notes or ""}
    for dim in cfg["dimensions"]:
        validate_choice(cfg, dim, row[dim])
    posts.append(row)
    write_csv("posts.csv", POST_FIELDS, posts)
    print(f"added {a.id} ({a.status})")


def cmd_posted(a, cfg):
    posts = read_csv("posts.csv", POST_FIELDS)
    for p in posts:
        if p["post_id"] == a.post_id:
            p["status"], p["posted_date"] = "posted", a.date or today()
            if a.url:
                p["url"] = a.url
            write_csv("posts.csv", POST_FIELDS, posts)
            print(f"{a.post_id} marked posted on {p['posted_date']}")
            return
    die(f"no post '{a.post_id}'")


def cmd_add_metrics(a, cfg):
    posts = read_csv("posts.csv", POST_FIELDS)
    if not any(p["post_id"] == a.post_id for p in posts):
        die(f"no post '{a.post_id}'")
    metrics = [m for m in read_csv("metrics.csv", METRIC_FIELDS)
               if not (m["post_id"] == a.post_id and m["checkpoint"] == a.checkpoint)]
    row = {"post_id": a.post_id, "checkpoint": a.checkpoint, "recorded": today()}
    for f in METRIC_FIELDS[3:]:
        v = getattr(a, f)
        row[f] = "" if v is None else v
    metrics.append(row)
    write_csv("metrics.csv", METRIC_FIELDS, metrics)
    print(f"recorded {a.checkpoint} metrics for {a.post_id}")


def cmd_add_lead(a, cfg):
    leads = read_csv("leads.csv", LEAD_FIELDS)
    lid = f"L{len(leads) + 1:04d}"
    leads.append({"lead_id": lid, "created": today(), "updated": today(), "source_post_id": a.post or "",
                  "stage": a.stage, "order_value": a.value or "", "note": a.note or ""})
    write_csv("leads.csv", LEAD_FIELDS, leads)
    print(f"added lead {lid} at stage {a.stage}")


def cmd_advance_lead(a, cfg):
    leads = read_csv("leads.csv", LEAD_FIELDS)
    for lead in leads:
        if lead["lead_id"] == a.lead_id:
            lead["stage"], lead["updated"] = a.stage, today()
            if a.value:
                lead["order_value"] = a.value
            if a.note:
                lead["note"] = (lead["note"] + " | " if lead["note"] else "") + a.note
            write_csv("leads.csv", LEAD_FIELDS, leads)
            print(f"{a.lead_id} → {a.stage}")
            return
    die(f"no lead '{a.lead_id}'")


def load_all():
    return (read_csv("posts.csv", POST_FIELDS), read_csv("metrics.csv", METRIC_FIELDS),
            read_csv("leads.csv", LEAD_FIELDS))


def cmd_learn(a, cfg):
    write_playbook(*load_all(), cfg)
    print(f"wrote {HOME / 'playbook.md'}")


def cmd_plan(a, cfg):
    week = a.week or "{}-W{:02d}".format(*dt.date.today().isocalendar()[:2])
    write_plan(*load_all(), cfg, week)
    print(f"wrote {HOME / 'plan.md'}")


def cmd_status(a, cfg):
    posts, metrics, leads = load_all()
    counts: dict[str, int] = {}
    for p in posts:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    print(f"posts: {counts or 'none'} · metric rows: {len(metrics)} · leads: {len(leads)}")
    for pid, cp in data_gaps(posts, metrics):
        print(f"  needs {cp} metrics: {pid}")
    open_leads = [l for l in leads if l["stage"] not in ("bulk", "lost")]
    for l in open_leads:
        print(f"  open lead {l['lead_id']} at {l['stage']} (from {l['source_post_id'] or '?'}) {l['note']}")


def main(argv=None):
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add-post", help="log a post (draft or posted) with its tags")
    p.add_argument("--id", required=True)
    p.add_argument("--first-line", required=True)
    p.add_argument("--hook", required=True, help="hook formula id from ig-reel/hooks.json")
    p.add_argument("--format", required=True)
    p.add_argument("--length", default="n/a")
    p.add_argument("--theme", required=True)
    p.add_argument("--style", required=True)
    p.add_argument("--cta", required=True)
    p.add_argument("--status", default="draft", choices=["draft", "posted", "dropped"])
    p.add_argument("--date")
    p.add_argument("--url")
    p.add_argument("--file")
    p.add_argument("--notes")
    p.set_defaults(fn=cmd_add_post)

    p = sub.add_parser("posted", help="mark a draft as posted")
    p.add_argument("post_id")
    p.add_argument("--date")
    p.add_argument("--url")
    p.set_defaults(fn=cmd_posted)

    p = sub.add_parser("add-metrics", help="record insights for a post at a checkpoint")
    p.add_argument("post_id")
    p.add_argument("--checkpoint", default="7d", choices=list(CHECKPOINT_ORDER))
    for f, flag in [("views", "--views"), ("reach", "--reach"), ("non_follower_pct", "--nonfollower"),
                    ("hold_3s_pct", "--hold3s"), ("avg_watch_s", "--watch"), ("likes", "--likes"),
                    ("comments", "--comments"), ("saves", "--saves"), ("shares", "--shares"),
                    ("follows", "--follows"), ("profile_visits", "--profile-visits"),
                    ("keyword_comments", "--keyword-comments")]:
        p.add_argument(flag, dest=f, type=float)
    p.set_defaults(fn=cmd_add_metrics)

    p = sub.add_parser("add-lead", help="a person who got past commenting (DM onwards)")
    p.add_argument("--post", help="post_id that brought them in")
    p.add_argument("--stage", default="dm", choices=STAGE_ORDER)
    p.add_argument("--value")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_add_lead)

    p = sub.add_parser("advance-lead", help="move a lead to a new stage")
    p.add_argument("lead_id")
    p.add_argument("--stage", required=True, choices=STAGE_ORDER)
    p.add_argument("--value")
    p.add_argument("--note")
    p.set_defaults(fn=cmd_advance_lead)

    sub.add_parser("learn", help="score everything and rewrite playbook.md").set_defaults(fn=cmd_learn)
    p = sub.add_parser("plan", help="rewrite plan.md for the week")
    p.add_argument("--week")
    p.set_defaults(fn=cmd_plan)
    sub.add_parser("status", help="counts, missing metrics, open leads").set_defaults(fn=cmd_status)

    a = ap.parse_args(argv)
    a.fn(a, cfg)


if __name__ == "__main__":
    main()
