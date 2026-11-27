// Render an explainer page to MP4 (30 fps, H.264) frame by frame. Default page: ab_test_flow.html (1080x1080).
// Usage: [PAGE=page.html] node render.js [out.mp4] [fps]  |  [PAGE=page.html] node render.js --stills dir t1 t2 ...
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// PAGE=ab_test_flow_onepage.html node render.js out.mp4  renders the one-page version
const page_url = 'file://' + path.join(__dirname, process.env.PAGE || 'ab_test_flow.html') + '?render=1';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(page_url);
  await page.evaluate(() => window.ready);

  const grab = async (t) => {
    const b64 = await page.evaluate((t) => { window.renderAt(t); return document.getElementById('c').toDataURL('image/png').split(',')[1]; }, t);
    return Buffer.from(b64, 'base64');
  };

  if (process.argv[2] === '--stills') {
    const dir = process.argv[3];
    fs.mkdirSync(dir, { recursive: true });
    for (const t of process.argv.slice(4).map(Number)) fs.writeFileSync(path.join(dir, `t${t.toFixed(1)}.png`), await grab(t));
    await browser.close();
    return;
  }

  const out = process.argv[2] || path.join(__dirname, 'ab_test_flow.mp4');
  const fps = Number(process.argv[3] || 30);
  const total = await page.evaluate(() => window.TOTAL);
  const frames = Math.round(total * fps);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < frames; i++) {
    const buf = await grab(i / fps);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${frames}`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
  console.log('wrote', out);
})();
