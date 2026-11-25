const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const page = process.argv[2], only = process.argv[3], fps = 30, dir = __dirname;
  const frames = path.join(dir, 'frames_' + page);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  await p.goto(`http://127.0.0.1:8769/${page}.html`);
  await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  fs.writeFileSync(path.join(dir, `events_${page}.json`), JSON.stringify(await p.evaluate(() => ({ dur: window.DURATION, sfx: window.SFX, hits: window.HITS, music: window.MUSIC }))));
  if (only) {
    for (const s of only.split(',')) { await p.evaluate(t => renderAt(t), +s); await p.screenshot({ path: path.join(dir, `still_${page}_${s}.png`) }); }
  } else {
    fs.rmSync(frames, { recursive: true, force: true }); fs.mkdirSync(frames);
    const n = Math.round(await p.evaluate(() => window.DURATION) * fps);
    for (let i = 0; i < n; i++) { await p.evaluate(t => renderAt(t), i / fps); await p.screenshot({ path: path.join(frames, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 92 }); }
    console.log('frames', n);
  }
  await b.close();
})();
