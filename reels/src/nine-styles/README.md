# Nine styles (21s)

Source for `reels/kickster-9-styles-21s.mp4`: one approved script, one style per beat
(synthwave, glow atom, 3D exploded view, isometric, paper-cut, maths diagram,
domino reveal, 3D data chart, cartoon). HTML + GSAP + three.js, rendered frame by
frame with Playwright, encoded with ffmpeg. Same build steps as `../built-not-printed`
(serve on port 8766, `node render.js`, 630 frames at 30 fps).

15s cut: `node render15.js` maps each scene onto a shorter window (450 frames) for `reels/kickster-9-styles-15s.mp4`.
