# motion-design-skills

**Five animation styles as Claude skills.** Pick a look, describe your idea, and Claude builds the video in code and renders an MP4, vertical or horizontal.

| 3D toy character | Kinetic typography | Hand-drawn cartoon | System diagram | Data story charts |
|:-:|:-:|:-:|:-:|:-:|
| ![3d-toy-character](examples/3d-toy-character.gif) | ![kinetic-typography](examples/kinetic-typography.gif) | ![hand-drawn-cartoon](examples/hand-drawn-cartoon.gif) | ![system-diagram-animation](examples/system-diagram-animation.gif) | ![data-story-charts](examples/data-story-charts.gif) |
| [MP4](examples/3d-toy-character.mp4) | [MP4](examples/kinetic-typography.mp4) | [MP4](examples/hand-drawn-cartoon.mp4) | [MP4](examples/system-diagram-animation.mp4) | [MP4](examples/data-story-charts.mp4) |

Every example above is the same 15-second story, "A tiny robot learns to fly", made from one SKILL.md each.

## The skills

| Skill | What it makes | Engine |
|---|---|---|
| [`3d-toy-character`](3d-toy-character/SKILL.md) | Soft vinyl-toy 3D characters with studio lighting, contact shadows and squash-and-stretch acting | HyperFrames + Three.js (Blender optional) |
| [`kinetic-typography`](kinetic-typography/SKILL.md) | Big words that slam, stack and stretch on the beat, with colour flips | HyperFrames + GSAP |
| [`hand-drawn-cartoon`](hand-drawn-cartoon/SKILL.md) | Storybook cartoons with boiling ink lines, paper grain and crayon hatching | HyperFrames + SVG + GSAP |
| [`system-diagram-animation`](system-diagram-animation/SKILL.md) | Architecture and flow diagrams that build node by node, with data packets travelling along the edges | HyperFrames + SVG + GSAP |
| [`data-story-charts`](data-story-charts/SKILL.md) | Charts that tell a story: lines that draw, counters that tick, axes that rescale on the surprise | HyperFrames + SVG + GSAP |

## How the skills work

Each skill is **one self-contained `SKILL.md`**. It works when copied into a skills folder, and also when you paste its text straight into a chat. Every skill has the same sections:

1. **Options:** format (9:16, 16:9, 1:1), duration, tone presets, with defaults.
2. **Brief:** the few questions to answer before planning, and a beat list.
3. **Reads sheet:** the one thing each beat must get across, plus minimum reading times for text.
4. **Motion discipline:** causal motion, one main direction, exits that set up entries, and timing caps. Character styles get extra rules: idle acting and no "twinning" (mirrored limbs).
5. **Style rules:** what makes the look, each rule with its reason. Plus defaults and overrides: your brand colours and characters always win.
6. **Setup and route:** which engine to use for which need.
7. **Visual language and move vocabulary:** exact eases and durations.
8. **Make it eye-catching:** what separates a postable video from a test render.
9. **Starter:** a short, tested code example.
10. **Avoid, and failure modes:** each with symptom, cause and fix.
11. **Validate and self-critique:** snapshots per beat, plus mid-transition stills and a scored review loop.
12. **Deliver:** a poster frame baked in as the thumbnail, plus a ready-to-post caption.
13. **Study these:** credited reference posts.

## Install (Claude Code)

```bash
git clone https://github.com/PHANTOMTONYT/motion-design-skills.git
```

To use the skills in every project, copy them to `~/.claude/skills/`:

```bash
cp -r motion-design-skills/3d-toy-character motion-design-skills/kinetic-typography motion-design-skills/hand-drawn-cartoon motion-design-skills/system-diagram-animation motion-design-skills/data-story-charts ~/.claude/skills/
```

Or copy the folders into `.claude/skills/` inside one project. Then ask for a video ("make a 15-second vertical video explaining how a CDN works"), or call a skill directly:

```
/kinetic-typography 12-second ad for my coffee brand, punchy
/system-diagram-animation how OAuth login works, 20 seconds, vertical
```

Using Claude without Claude Code? Open a `SKILL.md`, paste its text into the chat, and describe your video.

### Requirements

- Node.js 22+
- FFmpeg
- [HyperFrames](https://github.com/heygen-com/hyperframes), run through `npx` with nothing to install. Check your setup with `npx hyperframes doctor`.
- Optional: Blender for the high-end 3D route.

Rendering runs locally in a headless browser, with no GPU required.

## How the examples were made

Each example came from one skill and the same brief:

> **A tiny robot learns to fly** (15 s, 1080×1920). Hook: the robot looks up at birds ("Can a tiny robot fly?"). It flaps, jumps, hangs in the air for a moment, then thuds down. Its antenna lights up with an idea, and it adds a propeller. Take-off is wobbly. Then it soars, and the camera follows. It lands, waves, and the end card reads "Keep trying."

Each style tells the story its own way:
- **3D toy:** a rooftop scene in Three.js.
- **Kinetic type:** slamming words ("THUD." / "IDEA!" / "UPPP!").
- **Hand-drawn:** boiling ink and dizzy stars.
- **System diagram:** `jump()` is blocked by gravity, then a propeller module plugs in.
- **Data story:** a live altitude chart that rescales when the robot takes off.

Every frame is computed from time, so renders are repeatable.

## References and credits

Each skill's "Study these" section links the public posts it learned from, credited to their creators. The skills also adapt ideas, in their own words, from:

- [HyperFrames](https://github.com/heygen-com/hyperframes): its rendering model, motion doctrine and explainer workflow
- [JohnHeibel/ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase): character animation principles for code
- [latent-spaces/brag](https://github.com/latent-spaces/brag): options, creative rules and poster-frame delivery
- [howseen-ai/claude-motion-design](https://github.com/howseen-ai/claude-motion-design): the scored self-critique loop

This repository contains no third-party video, footage or artwork; it only links to them.

## License

MIT, see [LICENSE](LICENSE). The example videos were made with these skills and are covered by the same licence.

This is an independent project, not affiliated with Anthropic, HeyGen or any creator referenced above.
