import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
const staticPreview = process.argv.includes('--static');
const command = staticPreview
  ? ['.venv/bin/python', '-m', 'http.server', '4318', '--bind', '127.0.0.1', '--directory', 'dist/preview']
  : ['.venv/bin/python', '-m', 'itchy.server'];
const server = Bun.spawn(command, { env: { ...process.env, PORT: '4318' }, stdout: 'ignore', stderr: 'inherit' });
let browser;
try {
  const url = 'http://127.0.0.1:4318';
  let ready = false;
  for (let i = 0; i < 100; i++) {
    try { ready = (await fetch(url)).ok; } catch {}
    if (server.exitCode !== null) throw new Error('Preview server exited');
    if (ready) break;
    await Bun.sleep(50);
  }
  if (!ready) throw new Error('Preview server failed to start');
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#status')?.textContent?.startsWith('Ready'), undefined, { timeout: 10000 });
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(200);
  await page.waitForFunction(() => window.scratchVM.runtime.targets.find(t => t.getName() === 'Player').x === 10);
  await page.keyboard.press('Space');
  await page.waitForFunction(() => Number(window.scratchVM.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 1);
  await page.click('#start');
  await page.waitForTimeout(200);
  await page.waitForFunction(() => {
    const vm = window.scratchVM;
    return vm.runtime.targets.find(t => t.getName() === 'Player').x === 0 && Number(vm.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 0;
  });
  const skinCount = await page.evaluate(() => Object.keys(window.scratchVM.runtime.renderer._allSkins).length);
  if (skinCount < 2) throw new Error('Costumes did not load');
  const download = await page.request.get(`${url}/game.sb3`);
  if (!download.ok() || (await download.body()).subarray(0, 2).toString() !== 'PK') throw new Error('Invalid export download');
  await page.selectOption('#game', '/logic.sb3');
  await page.waitForFunction(() => {
    const vm = window.scratchVM;
    return vm.runtime.targets.some(t => t.getName() === 'Coin' && t.visible) &&
      Number(vm.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 0;
  });
  for (let i = 0; i < 6; i++) { await page.keyboard.press('ArrowRight'); await page.waitForTimeout(50); }
  await page.waitForFunction(() => {
    const vm = window.scratchVM;
    return !vm.runtime.targets.find(t => t.getName() === 'Coin').visible &&
      Number(vm.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 1;
  });
  await page.waitForTimeout(200);
  const score = await page.evaluate(() => Number(window.scratchVM.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value));
  if (score !== 1) throw new Error('Hidden coin scored repeatedly');
  await page.click('#start');
  await page.waitForTimeout(200);
  await page.waitForFunction(() => {
    const vm = window.scratchVM;
    return vm.runtime.targets.some(t => t.getName() === 'Coin' && t.visible) &&
      Number(vm.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 0;
  });
  const decoded = await page.evaluate(() => window.scratchVM.runtime.targets.find(t => t.getName() === 'Coin').sprite.sounds[0]);
  if (!decoded.soundId || decoded.sampleCount <= 0) throw new Error('Embedded WAV did not decode');
  await page.selectOption('#game', '/hide-and-seek.sb3');
  await page.waitForFunction(() => window.scratchVM.runtime.targets.some(t => t.getName() === 'Target' && t.visible && (t.x !== 0 || t.y !== 0)));
  await page.evaluate(() => window.scratchVM.runtime.renderer.draw());
  const target = await page.evaluate(() => {
    const sprite = window.scratchVM.runtime.targets.find(t => t.getName() === 'Target');
    return { x: sprite.x, y: sprite.y };
  });
  const box = await page.locator('#stage').boundingBox();
  await page.mouse.click(box.x + (target.x + 240) / 480 * box.width, box.y + (180 - target.y) / 360 * box.height);
  await page.waitForFunction(() => Number(window.scratchVM.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 1);
  await page.click('#start');
  await page.waitForFunction(() => Number(window.scratchVM.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 0);
  if (errors.length) throw new Error(errors.join('\n'));
  await mkdir('dist', { recursive: true });
  await page.screenshot({ path: 'dist/preview.png' });
  console.log('Browser passed: costumes, arrow input, score, reset, export, collision, hide/show, Hide and Seek click/reset; dist/preview.png');
} finally {
  await browser?.close();
  server.kill();
  await server.exited;
}
