# Same design. Different factory. (33.6 s documentary-trailer reel)

Source for `reels/kickster-same-design-34s.mp4`. Fully animated: no real footage, no
photos, no AI imagery, no voice. HTML + SVG + GSAP rendered frame by frame with
Playwright, original score synthesised in Python, encoded with FFmpeg.

```
npm i gsap@3.12.5
python3 -m http.server 8768 --bind 127.0.0.1 &
node render.js 9.0,22.6     # stills only
node render.js              # all 1008 frames (30 fps) to ./frames
node dump.js                # needle drop times -> drops.json (sound sync)
python3 audio.py            # -> mix_raw.wav (48 kHz stereo)
ffmpeg -framerate 30 -i frames/%05d.jpg -i mix_raw.wav \
  -af loudnorm=I=-14:TP=-1:LRA=11 -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p \
  -profile:v high -r 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest out.mp4
```

Timeline sits on a 75 BPM grid (beat = 0.8 s) so cuts, labels and hits land on the music.

## Audio credits
- Score and most sound design: original, synthesised in `audio.py` (owned by Kickster).
- Mixkit SFX (Mixkit Sound Effects Free License), traceable entries only:
  `impact-cine` (Cinematic whoosh deep impact), `whoosh-fast` (Fast whoosh transition),
  `transition-snap` (Fast transitions swoosh), `swoosh-quick` (Fast small sweep transition),
  `transition-soft` (Air zoom vacuum). Source list: `editing-packs/video-shotcraft/template/public/audio/ATTRIBUTION.md`.

Fonts: Big Shoulders Display and Bricolage Grotesque (SIL Open Font License).
