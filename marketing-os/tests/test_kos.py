"""Checks that the OS actually learns. Uses SYNTHETIC data in a temp dir only.

Run: python3 -m unittest discover -s marketing-os/tests
"""
import json
import os
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp())
shutil.copy(ROOT / "config.json", TMP / "config.json")
os.environ["KOS_HOME"] = str(TMP)
sys.path.insert(0, str(ROOT))
import kos  # noqa: E402

# The hidden truth of the simulated account.
TRUE_EFFECT = {
    ("visual_style", "factory_footage"): 0.9,
    ("visual_style", "text_only"): -0.9,
    ("hook_formula", "2"): 0.6,
    ("cta", "none"): -1.2,
}


def simulate(choices, rng):
    lift = sum(TRUE_EFFECT.get((d, v), 0.0) for d, v in choices.items())
    m = 2.718 ** (lift + rng.gauss(0, 0.3))
    return {"views": int(3000 * m), "reach": int(2800 * m), "hold_3s_pct": min(95, 50 * m ** 0.3),
            "shares": int(20 * m), "follows": int(8 * m), "keyword_comments": int(3 * m)}


class LearningLoop(unittest.TestCase):
    def setUp(self):
        for f in ("posts.csv", "metrics.csv", "leads.csv", "history.csv"):
            (TMP / "data" / f).unlink(missing_ok=True)

    def run_weeks(self, weeks):
        cfg = kos.load_config()
        rng = random.Random(7)
        posts, metrics = [], []
        dims = cfg["dimensions"]
        for w in range(weeks):
            scored = kos.score_posts(posts, metrics, [], cfg)
            learned = kos.learn_dimensions(posts, scored, cfg)
            # Early weeks: random content, like an account before the OS.
            slots = ([{"choices": {d: rng.choice(v) for d, v in dims.items()}} for _ in range(5)]
                     if w < 4 else kos.make_plan(learned, cfg, f"sim-W{w}"))
            for i, s in enumerate(slots):
                c = kos.normalise(dict(s["choices"]))
                pid = f"w{w}-{i}"
                posts.append({**{k: "" for k in kos.POST_FIELDS}, **c, "post_id": pid,
                              "status": "posted", "first_line": pid})
                metrics.append({**{k: "" for k in kos.METRIC_FIELDS}, "post_id": pid, "checkpoint": "7d",
                                **{k: str(v) for k, v in simulate(c, rng).items()}})
        return posts, metrics, cfg

    def test_finds_winners_and_losers(self):
        posts, metrics, cfg = self.run_weeks(12)
        learned = kos.learn_dimensions(posts, kos.score_posts(posts, metrics, [], cfg), cfg)
        self.assertEqual(learned["visual_style"]["factory_footage"]["verdict"], "WORKS")
        self.assertNotEqual(learned["visual_style"]["text_only"]["verdict"], "WORKS")
        self.assertGreater(learned["hook_formula"]["2"]["mean"], 0.2)
        self.assertEqual(learned["cta"]["none"]["verdict"], "DOESN'T")

    def test_plan_shifts_toward_winners(self):
        posts, metrics, cfg = self.run_weeks(12)
        early = [p for p in posts if p["post_id"] < "w4"]
        late = [p for p in posts if p["post_id"].startswith(("w10", "w11"))]
        share = lambda ps: sum(p["visual_style"] == "factory_footage" for p in ps) / len(ps)
        self.assertGreater(share(late), share(early) + 0.3)
        self.assertFalse(any(p["cta"] == "none" for p in late))

    def test_leads_outweigh_views(self):
        cfg = kos.load_config()
        base = {k: "" for k in kos.POST_FIELDS}
        posts = [{**base, "post_id": "viral", "status": "posted"}, {**base, "post_id": "sales", "status": "posted"},
                 {**base, "post_id": "mid", "status": "posted"}]
        mk = lambda pid, v, kw: {**{k: "" for k in kos.METRIC_FIELDS}, "post_id": pid, "checkpoint": "7d",
                                 "views": str(v), "reach": str(v), "shares": "10", "follows": "5",
                                 "keyword_comments": str(kw)}
        metrics = [mk("viral", 60000, 0), mk("sales", 4000, 6), mk("mid", 8000, 1)]
        leads = [{"lead_id": "L1", "source_post_id": "sales", "stage": "sample", "order_value": ""}]
        s = kos.score_posts(posts, metrics, leads, cfg)
        self.assertGreater(s["sales"]["score"], s["viral"]["score"])

    def test_cli_roundtrip_and_reports(self):
        kos.main(["add-post", "--id", "p1", "--first-line", "x", "--hook", "2", "--format", "reel",
                  "--length", "15_30s", "--theme", "scam_protection", "--style", "factory_footage",
                  "--cta", "comment_PRICE"])
        kos.main(["posted", "p1", "--date", "2026-11-01"])
        kos.main(["add-metrics", "p1", "--views", "1000", "--reach", "900", "--shares", "4"])
        kos.main(["add-lead", "--post", "p1", "--stage", "dm"])
        kos.main(["advance-lead", "L0001", "--stage", "sample"])
        kos.main(["learn"])
        kos.main(["plan", "--week", "2026-W48"])
        self.assertIn("Scoreboard", (TMP / "playbook.md").read_text())
        self.assertIn("Slot 1", (TMP / "plan.md").read_text())
        with self.assertRaises(SystemExit):
            kos.main(["add-post", "--id", "p2", "--first-line", "x", "--hook", "2", "--format", "reel",
                      "--theme", "not_a_theme", "--style", "mixed", "--cta", "dm"])


if __name__ == "__main__":
    unittest.main()
