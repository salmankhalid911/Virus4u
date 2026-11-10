# Built, not printed (15s motion graphic)

Source for `reels/kickster-built-not-printed-15s.mp4`. HTML + GSAP timeline + three.js,
rendered frame by frame with Playwright, then encoded with ffmpeg.

```
npm i three@0.160.0 gsap@3.12.5
python3 -m http.server 8765 --bind 127.0.0.1 &
node render.js            # all 450 frames to ./frames (30 fps)
node render.js 0,4,13.9   # stills only
ffmpeg -framerate 30 -i frames/%05d.jpg -c:v libx264 -crf 17 -pix_fmt yuv420p out.mp4
```
Fonts: Big Shoulders Display and Bricolage Grotesque (SIL Open Font License, Google Fonts).
