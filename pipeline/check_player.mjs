#!/usr/bin/env node
/**
 * Behavioural check for a generated course player page, driven by real Firefox.
 *
 * Written while adding the playback-speed control, to answer a question that
 * static inspection cannot: does the page still AUTO-ADVANCE, and does the
 * speed control actually move playbackRate in 0.05 steps? Point it at two
 * URLs -- one built before a change, one after -- and you have an A/B that
 * settles "did my change break the player?" with evidence instead of opinion.
 *
 *   node pipeline/check_player.mjs <player-page-url> [--next <substring>]
 *                                  [--rate 0.65] [--allow-autoplay] [--chromium]
 *
 * --next           expect auto-advance to a URL containing this substring
 * --rate           seed localStorage cw_rate first (tests persistence)
 * --allow-autoplay lift the browser's autoplay blocking, i.e. simulate a site
 *                  the user has granted "Allow Audio and Video". WITHOUT this,
 *                  a browser will refuse to start the NEXT video and that is
 *                  browser policy, not a bug in the page -- the distinction
 *                  cost real debugging time once, hence the flag.
 *
 * Exits non-zero if any assertion fails.
 *
 * Setup once:  cd pipeline && npm install
 */
let firefox, chromium;
try {
  ({ firefox, chromium } = await import('playwright'));
} catch {
  console.error('playwright not installed. Run:  cd pipeline && npm install');
  process.exit(2);
}

const args = process.argv.slice(2);
const url = args[0];
if (!url || url.startsWith('-')) {
  console.error('usage: check_player.mjs <url> [--next <substr>] [--rate N] [--allow-autoplay] [--chromium]');
  process.exit(2);
}
const flag = (n) => args.includes(n);
const val = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);
const expectNext = val('--next', null);
const seedRate = val('--rate', null);

let failures = 0;
const check = (name, got, want) => {
  const ok = String(got) === String(want);
  if (!ok) failures++;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  (got ${got}, want ${want})`}`);
};

const engine = flag('--chromium') ? chromium : firefox;
const browser = await engine.launch(
  flag('--allow-autoplay') && !flag('--chromium')
    ? { firefoxUserPrefs: { 'media.autoplay.default': 0, 'media.autoplay.blocking_policy': 0 } }
    : {});
const page = await (await browser.newContext()).newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e).slice(0, 200)));
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 200)); });

console.log(`\n${url}`);
await page.goto(url);
if (seedRate) { await page.evaluate((r) => localStorage.setItem('cw_rate', r), seedRate); await page.reload(); }

// --- the speed control -------------------------------------------------
const present = await page.evaluate(() => !!document.getElementById('sr'));
check('speed control present', present, true);
if (present) {
  const bounds = await page.evaluate(() => {
    const R = document.getElementById('sr');
    return { min: R.min, max: R.max, step: R.step };
  });
  check('slider min', bounds.min, '0.25');
  check('slider max', bounds.max, '2');
  check('slider step', bounds.step, '0.05');

  if (seedRate) check('rate restored from localStorage', await page.evaluate(() => document.querySelector('video').playbackRate), seedRate);

  const stepped = await page.evaluate(() => {
    const V = document.querySelector('video');
    const before = V.playbackRate;
    document.getElementById('su').click();
    return +(V.playbackRate - before).toFixed(4);
  });
  check('"+" steps by exactly 0.05', stepped, 0.05);

  const clamped = await page.evaluate(() => {
    const V = document.querySelector('video'), su = document.getElementById('su'), sd = document.getElementById('sd');
    for (let i = 0; i < 50; i++) su.click();
    const hi = V.playbackRate;
    for (let i = 0; i < 80; i++) sd.click();
    return { hi, lo: V.playbackRate };
  });
  check('clamps at 2x', clamped.hi, 2);
  check('clamps at 0.25x', clamped.lo, 0.25);

  // The native speed menu must be mirrored, not fought. Off-grid snaps.
  const mirrored = await page.evaluate(async () => {
    const V = document.querySelector('video');
    V.playbackRate = 1.23;
    await new Promise((r) => setTimeout(r, 200));
    return { rate: V.playbackRate, slider: document.getElementById('sr').value };
  });
  check('native rate snaps to grid', mirrored.rate, 1.25);
  check('slider mirrors native menu', mirrored.slider, '1.25');

  await page.evaluate(() => document.getElementById('sv').click());
  check('readout click resets to 1x', await page.evaluate(() => document.querySelector('video').playbackRate), 1);
}

// --- auto-advance ------------------------------------------------------
if (expectNext) {
  if (seedRate) await page.evaluate((r) => localStorage.setItem('cw_rate', r), seedRate);
  await page.click('video', { position: { x: 40, y: 40 } }).catch(() => {});
  await page.evaluate(async () => {
    const v = document.querySelector('video');
    if (v.readyState < 1) await new Promise((r) => v.addEventListener('loadedmetadata', r, { once: true }));
    v.currentTime = v.duration - 3;
    await new Promise((r) => setTimeout(r, 400));
    await v.play().catch((e) => e.name);
  });
  let advanced = false;
  try { await page.waitForURL(`**${expectNext}**`, { timeout: 30000 }); advanced = true; } catch {}
  check(`auto-advances to ${expectNext}`, advanced, true);
  if (advanced) {
    await new Promise((r) => setTimeout(r, 2500));
    const b = await page.evaluate(() => {
      const v = document.querySelector('video');
      return { playing: !v.paused, rate: v.playbackRate };
    });
    console.log(`  INFO  next video autoplaying=${b.playing} rate=${b.rate}` +
      (b.playing ? '' : '  <- browser autoplay policy, not a page bug (retry with --allow-autoplay)'));
    if (seedRate) check('rate carries to next section', b.rate, seedRate);
  }
}

check('no page JS errors', errors.length ? JSON.stringify(errors) : 0, 0);
await browser.close();
console.log(failures ? `\n${failures} FAILED\n` : '\nall checks passed\n');
process.exit(failures ? 1 : 0);
