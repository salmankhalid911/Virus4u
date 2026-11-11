# Garciago tracksuit reel (20s)

Source for `reels/kickster-garciago-20s.mp4`. Built on `../nine-styles` (all nine animation
styles) plus three phone clips and three photos of the client's garciago tracksuit.

Footage frames are not committed. To rebuild, extract them into `foot/A`, `foot/B`, `foot/C`
(clips, 60 fps, rotated and cropped to 1080x1920) and `foot/P/1..3.jpg` (photos) with:
`ffmpeg -i clip.mov -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.06:saturation=1.08" -q:v 3 foot/A/%03d.jpg`
then serve on port 8767 and run `node render.js` (600 frames at 30 fps).
