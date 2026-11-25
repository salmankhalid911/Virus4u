#!/bin/bash
set -e
cd "$(dirname "$0")"
for p in "$@"; do
  node render.js $p
  python3 sound.py $p
  ffmpeg -v error -y -framerate 30 -i frames_$p/%05d.jpg -i mix_$p.wav \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.82:level=false,aresample=48000" \
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest animatic_$p.mp4
  echo "done $p"
done
