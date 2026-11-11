const { chromium } = require('playwright');
// 15s cut: each new scene window maps onto the original 21s scene window
const OLD=[0,2,4,8,10,12,14,16.5,18.5,21], NEW=[0,1.6,3.2,6.0,7.3,8.6,9.9,11.7,13.2,15];
function warp(t){for(let k=0;k<NEW.length-1;k++){if(t<NEW[k+1]||k===NEW.length-2){const f=(t-NEW[k])/(NEW[k+1]-NEW[k]);return OLD[k]+f*(OLD[k+1]-OLD[k]);}}return 21;}
const path = require('path'), fs = require('fs');
(async () => {
  const dir = __dirname, frames = path.join(dir, 'frames15');
  const only = process.argv[2], fps = 30;
  if (!only) { fs.rmSync(frames, { recursive: true, force: true }); fs.mkdirSync(frames); }
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.goto('http://127.0.0.1:8766/index.html');
  await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  await p.evaluate(() => document.fonts.ready);
  if (only) {
    for (const s of only.split(',')) { await p.evaluate(t => renderAt(t), +s); await p.screenshot({ path: path.join(dir, `still_${s}.png`) }); }
  } else {
    const n = Math.round(15 * fps); const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await p.evaluate(t => renderAt(t), warp(i / fps));
      await p.screenshot({ path: path.join(frames, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 93 });
      if (i % 90 === 0) console.log('frame', i, ((Date.now() - t0) / 1000).toFixed(0) + 's');
    }
    console.log('frames', n);
  }
  await b.close();
})();
