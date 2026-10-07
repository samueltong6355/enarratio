// Run against a started local server: node web/scripts/smoke.mjs http://127.0.0.1:8001
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8000';
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Verify the running reader needs no external network resources.
  await page.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin
    ? route.continue() : route.abort());
  await page.goto(base);
  await page.getByText('Local analysis ready; no internet required.').waitFor({ timeout: 90000 });
  await page.getByRole('textbox', { name: 'Latin passage' }).fill('Caesar imperavit ut milites venirent.');
  await page.getByRole('button', { name: 'Analyse', exact: true }).click();
  await page.getByRole('button', { name: 'Save reading', exact: true }).waitFor();
  await page.waitForFunction(() => ![...document.querySelectorAll('button')].find(b => b.textContent === 'Save reading')?.disabled);
  assert.match(await page.locator('body').innerText(), /Substantive Clause of Purpose/);
  await page.getByRole('button', { name: 'Save reading', exact: true }).click();
  await page.getByText('Saved readings (1)', { exact: true }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export analysis', exact: true }).click();
  assert.equal((await download).suggestedFilename(), 'enarratio-reading.json');
  await page.reload();
  await page.getByText('Saved readings (1)', { exact: true }).click();
  // Simulate a stopped API while keeping the loaded page usable.
  await page.route('**/api/**', route => route.abort());
  await page.getByRole('button', { name: /^Caesar imperavit ut milites venirent\./ }).click();
  assert.match(await page.locator('body').innerText(), /Substantive Clause of Purpose/);
  await page.getByRole('button', { name: 'Analyse', exact: true }).click();
  await page.getByText(/Cannot reach the local server/).waitFor();
  assert.match(await page.locator('body').innerText(), /Substantive Clause of Purpose/);
  assert.deepEqual(errors, []);
  console.log('Browser smoke passed: same-origin analysis, clause display, save/reload, export, server-loss recovery; no page errors.');
} finally {
  await browser.close();
}
