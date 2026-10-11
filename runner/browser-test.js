import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
const server = Bun.spawn(['.venv/bin/python', '-m', 'itchy.server'], { env: { ...process.env, PORT: '4318' }, stdout: 'ignore', stderr: 'inherit' });
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
  await page.waitForTimeout(2000);
  console.log('Load status', await page.locator('#status').textContent(), errors);
  await page.waitForFunction(() => document.querySelector('#status')?.textContent?.startsWith('Ready'), undefined, { timeout: 10000 });
  console.log('Runtime ready', await page.locator('#status').textContent());
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(200);
  console.log('After right', await page.locator('#status').textContent());
  await page.waitForFunction(() => window.scratchVM.runtime.targets.find(t => t.getName() === 'Player').x === 10);
  console.log('Movement passed');
  await page.keyboard.press('Space');
  await page.waitForFunction(() => Number(window.scratchVM.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 1);
  await page.click('#start');
  await page.waitForFunction(() => {
    const vm = window.scratchVM;
    return vm.runtime.targets.find(t => t.getName() === 'Player').x === 0 && Number(vm.runtime.getTargetForStage().lookupVariableByNameAndType('score', '').value) === 0;
  });
  const skinCount = await page.evaluate(() => Object.keys(window.scratchVM.runtime.renderer._allSkins).length);
  if (skinCount < 2) throw new Error('Costumes did not load');
  const download = await page.request.get(`${url}/game.sb3`);
  if (!download.ok() || (await download.body()).subarray(0, 2).toString() !== 'PK') throw new Error('Invalid export download');
  if (errors.length) throw new Error(errors.join('\n'));
  await mkdir('dist', { recursive: true });
  await page.screenshot({ path: 'dist/preview.png' });
  console.log('Browser passed: costumes, arrow input, score, reset, export; dist/preview.png');
} finally {
  await browser?.close();
  server.kill();
  await server.exited;
}
