const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const dir = __dirname, frames = path.join(dir, 'frames');
  const only = process.argv[2], fps = 30;
  if (!only) { fs.rmSync(frames, { recursive: true, force: true }); fs.mkdirSync(frames); }
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.goto('http://127.0.0.1:8767/index.html');
  await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  await p.evaluate(() => document.fonts.ready);
  if (only) {
    for (const s of only.split(',')) { await p.evaluate(t => renderAt(t), +s); await p.screenshot({ path: path.join(dir, `still_${s}.png`) }); }
  } else {
    const n = Math.round(20 * fps); const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await p.evaluate(t => renderAt(t), i / fps);
      await p.screenshot({ path: path.join(frames, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 93 });
      if (i % 90 === 0) console.log('frame', i, ((Date.now() - t0) / 1000).toFixed(0) + 's');
    }
    console.log('frames', n);
  }
  await b.close();
})();
