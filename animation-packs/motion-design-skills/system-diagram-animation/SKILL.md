---
name: system-diagram-animation
description: Animated system and architecture diagrams that build node by node on one stage - boxes pop in, connectors draw on, data packets travel along edges, failures get a red cross, the camera reframes as the diagram grows - rendered to MP4 at 9:16 or 16:9 with HyperFrames, SVG and GSAP. Use whenever someone wants to explain how a system, API, pipeline, protocol, request flow, AI agent or architecture works as a video, or asks for an engineering or system-design explainer. Not for statistics and trends (use data-story-charts) or character stories (use hand-drawn-cartoon).
license: MIT
compatibility: HyperFrames (Node 22+, FFmpeg) with GSAP and inline SVG. Fonts from Google Fonts.
---

# System Diagram Animation

One dark stage. A diagram assembles itself in the order the story is told: a box lands, an arrow draws to the next box, a glowing packet travels along it, and the caption names what just happened. It never needs to cut, and it feels fast because something new lands every 1–2 seconds.

## Options

| Option | Default | Notes |
|---|---|---|
| format | vertical 1080×1920 | or landscape 1920×1080 (diagrams fit landscape more naturally) |
| duration | 20 s | 15–60 s; about 1 node per 1.5 s |
| tone | clean | `clean` (default), `punchy` (faster reveals, more packets, a shake on errors), `calm` (longer holds, no shake) |
| theme | dark | or light (paper white with navy lines) |

## Brief (answer before planning)

1. What system or flow, in one sentence?
2. What is the one path to follow (request → … → response)? List the nodes in order (at most 8 on screen at once).
3. Where is the interesting moment: a failure, a bottleneck, a cache hit, a retry?
4. What should the viewer remember at the end (one line)?

Then write the beat list: for each beat, the node or connector that appears, the packet that moves, and the caption text.

## Reads sheet (write it with the beat list)

For every beat, write the one thing the viewer must understand ("the robot can't fly", "the cache missed") and how long it stays readable. One read at a time. Text floors: a label stays at least 0.8 s, a sentence about 0.3 s per word once fully on screen. If the text won't fit the time, cut words rather than speed up.

## Motion discipline

- Motion is causal: every move has a reason on screen (a click, a fall, a packet arriving), and the next move follows from it.
- Pick one main direction of travel for the whole video and keep it. Use the other directions for meaning: up for success or conclusion, a zoom out for "here's the whole picture".
- A scene's exit sets up the next entry: same axis, same direction, similar speed. Carry one object across the change instead of crossfading.
- No idle filler motion (floating, breathing, wobbling) on diagrams, charts or text. If nothing should move, hold still; one deliberate camera drift is enough.
- Easing: smooth ease-out for entries (`power2.out` to `power4.out`), quicker ease-in for exits (about 75% of the entry time). Entries at most 0.8 s. Total stagger for a group at most 0.5 s. Overshoot (`back.out`) only for small pops; no elastic or bounce.
- One thing moves at a time when it matters; the eye can follow only one.
- Add a 0.3–0.75 s beat of stillness right before the payoff.

## Style rules (always)

1. One stage, no cuts. The diagram grows; when it outgrows the frame, the camera reframes (scale and move the whole diagram group).
2. Reveal order is story order. Nothing appears before it is mentioned.
3. Connectors draw on (stroke-dashoffset) before anything travels along them. Arrowheads appear only when their line has finished drawing.
4. Every 1–2 s something new lands: a node, a connector, a packet or a caption change.
5. One highlight colour for the active path. One red for failures. Everything else is neutral.
6. Labels are short: a function name, a service name or a 2–4 word phrase. Monospace for code-like names.

## Defaults and overrides

Precedence: the user's brand or spec, then the explicit request, then these defaults.

- Dark: stage `#0f1724`, dot grid `#1f2b3d`, node fill `#1c2a3d`, lines `#8aa4c2`, active `#38d6e0`, highlight `#ffd166`, error `#ef476f`, text `#f2f5f9`.
- Light: stage `#f7f8fb`, node fill `#ffffff`, lines `#5b6b82`, active `#0b7285`, highlight `#e8a100`, error `#d6336c`, text `#16213a`.
- Fonts: Inter 700–800 for names and captions, JetBrains Mono 600 for code labels. Node labels 40–52 px, captions 56–64 px in 9:16.

## Setup (once)

```bash
node -v && ffmpeg -version
npx hyperframes init my-video --non-interactive --resolution portrait && cd my-video   # landscape for 16:9
```

## Route

| Need | SVG + GSAP in HyperFrames (default) | Remotion |
|---|:-:|:-:|
| Nodes, connectors, packets, camera | yes | yes |
| Runs with only Node and FFmpeg | yes | yes |
| Licence | free | free up to 3 people |

## Layout

- **9:16:** the diagram flows top to bottom between y 290 and y 1080; captions sit at y 1110–1250. Use two columns at most (x 120–960). Node width 280–480 px.
- **16:9:** the diagram flows left to right between x 120 and x 1800, y 150–850; captions sit along the bottom at y 880–1000.
- Place nodes on a grid (multiples of 40 px) so connectors are straight or one smooth curve. Leave 80 px or more between nodes.
- Failed branches: show the red cross and an error tag, hold for 1 s, then fade the failed branch fully out before the new path appears (dimmed text fails contrast checks).

## Move vocabulary

| Move | How (GSAP + SVG) |
|---|---|
| Node in | `fromTo(node, {opacity:0, scale:0.6, transformOrigin:"50% 50%"}, {opacity:1, scale:1, duration:0.35, ease:"back.out(1.8)"})` |
| Connector draw | set `strokeDasharray` and `strokeDashoffset` to the path length and `opacity:0`; at time t show it and tween the offset to 0 over 0.35–0.6 s, `power2.inOut`; add the `marker-end` arrowhead only when the draw finishes |
| Packet | a glowing circle moved along the connector with `path.getPointAtLength(k * L)` in a tween's `onUpdate`, 0.4–0.7 s, linear |
| Active path | connector stroke to the active colour, plus a 0.2 s pulse on the node |
| Failure | a red cross scales in from 2.2 with `back.out(3)`, the source node shakes (`x` ±10 px, 3 times), an error tag pops |
| Upgrade | the node border turns to the highlight colour with a soft glow filter; its sub-label changes text |
| Success | the final node pops (scale 1.08 yoyo) and 2 rings expand and fade behind it |
| Camera | tween a wrapper group's `scale` (with `transformOrigin` in px) by 0.04–0.2; never more than every 3 s |
| Caption swap | old line out `y:-12, opacity:0` (0.15 s), new line in `y:14 → 0` (0.2 s) |

## Make it eye-catching

- The hook frame already shows the first node, big and centred, plus a caption that asks the question.
- Packets glow (a Gaussian-blur merge filter) and there are always one or two in motion during flow beats.
- The failure moment is the most dramatic beat: the cross, the shake, the red tag. Don't skip it if the story has one.
- The finale lights the whole working path in the active colour, with a burst behind the final node.
- A subtle dot grid and a slow camera drift keep the background alive.
- Every frozen frame should explain something on its own.

## Starter

```html
<div id="root" data-composition-id="main" data-start="0" data-duration="8" data-width="1080" data-height="1920" style="background:#0f1724">
<svg viewBox="0 0 1080 1920" width="1080" height="1920">
  <defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#8aa4c2"/></marker>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
  <g id="cam">
    <path id="c1" d="M540 470 L540 600" fill="none" stroke="#8aa4c2" stroke-width="6"/>
    <g id="n1"><rect x="300" y="330" width="480" height="140" rx="30" fill="#1c2a3d" stroke="#8aa4c2" stroke-width="5"/>
      <text x="540" y="415" text-anchor="middle" font-family="Inter" font-weight="800" font-size="50" fill="#f2f5f9">client</text></g>
    <g id="n2"><rect x="300" y="600" width="480" height="140" rx="30" fill="#1c2a3d" stroke="#8aa4c2" stroke-width="5"/>
      <text x="540" y="685" text-anchor="middle" font-family="JetBrains Mono" font-size="46" fill="#f2f5f9">GET /users</text></g>
    <circle id="pk" r="13" fill="#38d6e0" filter="url(#glow)" opacity="0"/>
  </g>
</svg>
<div id="cap" style="position:absolute;left:60px;right:120px;top:1110px;text-align:center;font:800 60px Inter,sans-serif;color:#f2f5f9">A request starts here</div>
</div>
<script>
const tl = gsap.timeline({ paused: true });
const draw = (id, t, d = 0.45) => { const p = document.querySelector(id), L = p.getTotalLength();
  gsap.set(p, { strokeDasharray: L, strokeDashoffset: L, opacity: 0 }); tl.set(p, { opacity: 1 }, t).to(p, { strokeDashoffset: 0, duration: d, ease: "power2.inOut" }, t)
    .set(p, { attr: { "marker-end": "url(#arr)" } }, t + d); };   // arrowhead only once the line has arrived
const pop = (id, t) => tl.fromTo(id, { opacity: 0, scale: 0.6, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.8)" }, t);
const packet = (pk, pathId, t, d = 0.6) => { const p = document.querySelector(pathId), L = p.getTotalLength(), o = { k: 0 };
  tl.set(pk, { opacity: 1 }, t).to(o, { k: 1, duration: d, ease: "none", onUpdate: () => { const q = p.getPointAtLength(o.k * L); pk.setAttribute("cx", q.x); pk.setAttribute("cy", q.y); } }, t).set(pk, { opacity: 0 }, t + d); };
gsap.set("#n2", { opacity: 0 });
pop("#n1", 0.2); draw("#c1", 1.4); pop("#n2", 1.8); packet(document.getElementById("pk"), "#c1", 2.0);
tl.set({}, {}, 8);
window.__timelines["main"] = tl;
</script>
```

Add a `<head>` with GSAP (`https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js`), Google Fonts for Inter and JetBrains Mono, and `html,body{margin:0;width:1080px;height:1920px;overflow:hidden}`. Grow the diagram beat by beat with `pop`, `draw` and `packet`.

## Parameters to expose

`format` · `duration` · `tone` · `theme` · `nodes` (id, label, position) · `edges` (from, to) · `beats` (time, action, caption) · `colors`.

## Avoid

- Every number on screen must come from the user's data or a cited source. Keep a small facts list (number, source) next to the composition. Anything illustrative is labelled as such on screen.
- Showing the whole diagram at once, then highlighting. Build it in story order.
- More than 8 nodes on screen in 9:16 (12 in 16:9). Split into two stages instead.
- Arrowheads visible before their line arrives (add the marker when the draw ends).
- Long labels and paragraphs inside boxes.
- Cuts and slide transitions. Reframe the camera instead.
- Dimmed leftovers with low-contrast text. Fade dead branches out completely.

## Failure modes

| Looks like | Cause | Fix |
|---|---|---|
| Arrowheads float ahead of their lines | SVG markers render at the path end even while it is being drawn | leave `marker-end` off in the markup and set it with `tl.set` when the draw ends |
| Rings or effects visible from frame 0 | `fromTo` renders its start values immediately | add `immediateRender:false` to tweens that start late |
| Diagram tiny in a tall frame | layout designed for landscape | use the full y 290–1080 band, bigger nodes, two columns at most |
| Text overflows a box | label longer than the box | shorten it, or widen the box (about 0.6 × font size per character for mono) |
| Feels static | nothing moves between reveals | keep 1–2 packets in motion; caption changes every beat |
| Contrast check fails on faded nodes | dimmed text below 3:1 | fade them fully out instead of dimming |

## Validate

```bash
npx hyperframes check
npx hyperframes snapshot --at <one time per beat, plus one mid-draw and one mid-reframe>
npx hyperframes render -o renders/<name>.mp4
```

- [ ] nodes appear in story order; nothing appears early
- [ ] every connector is drawn before a packet travels on it
- [ ] all labels fit inside their boxes and are readable at phone size
- [ ] captions inside the safe area and never over the diagram
- [ ] the final frame shows the whole working path

## Self-critique before the final render

Score the snapshot sheet 1–10 on: hook (first second), readability at phone width, motion quality, composition, accuracy, and the "muted test" (can a viewer summarise it in one sentence with no sound?). Fix only what scores 7 or below, re-snapshot, and repeat until everything is 8 or above. If you can, have a separate read-only pass do the scoring, so you aren't grading your own work.

| Don't | Instead |
|---|---|
| Crossfade between two busy layouts | exit the old content, then bring in the new, or carry one object across |
| Make several things move at once | stagger, one focus per moment |
| Fill pauses with floating or wobble | hold still, or let the character act |
| Add particles, rainbow gradients or 3D flips for "energy" | add a stronger event: a reveal, a hit, a camera move |
| Rush text to fit the time | cut words |

## Deliver

- Poster: the settled full-diagram frame (`ffmpeg -ss <t> -i renders/<name>.mp4 -frames:v 1 poster.jpg`), baked in as frame 0: `ffmpeg -i renders/<name>.mp4 -i poster.jpg -filter_complex "[0:v][1:v]overlay=enable='eq(n,0)'" -c:a copy renders/<name>-final.mp4`.
- A 1–2 sentence caption that says what the viewer will understand ("How one request reaches the database and back").
- Tell the user the beat list and which beat to change for a revision.

## Study these

- @alexxubyte (ByteByteGo), "How SSH Works", the canonical look: https://x.com/alexxubyte/status/2105666471326331207
- @bytebytego, "How the JVM Actually Works", a layered stack built tier by tier: https://x.com/bytebytego/status/2094800917908570575
- @deedydas, an AI-made SQLite code-map explainer with a "life of a query" trace: https://x.com/deedydas/status/2104391577091407965
- Primal Video, a Claude Code + Remotion animated diagram Short: https://www.youtube.com/shorts/jXI00KnPwDE
- Ideas adapted (not copied) from the HyperFrames motion doctrine and faceless-explainer skills, JohnHeibel/ClaudeAnimationBase's animation guide, howseen-ai/claude-motion-design's critique loop, and latent-spaces/brag.
