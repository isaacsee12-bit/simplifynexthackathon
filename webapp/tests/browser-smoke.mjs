// Run directly with node, optionally setting PLAYWRIGHT_MODULE to an external
// playwright/index.mjs and PLAYWRIGHT_BROWSERS_PATH to a temporary browser cache.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

async function main() {
  const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
    ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : 'playwright');
  const root = dirname(dirname(fileURLToPath(import.meta.url)));
  const artifacts = process.env.BROWSER_SMOKE_OUTPUT || join(tmpdir(), 'opencode', 'browser-smoke');
  await mkdir(artifacts, { recursive: true });
  const requests = [];
  const errors = [];
  const unexpected = [];
  let pending;
  let browser;
  let vite;
  let viteLog = '';
  const mock = createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', '*');
    if (req.method === 'OPTIONS') { res.end(); return; }
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    requests.push({ url: req.url, method: req.method, headers: req.headers, body: Buffer.concat(chunks).toString() });
    res.writeHead(200, { 'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store' });
    const send = (data) => res.write(`${JSON.stringify(data)}\n`);
    pending = { res, send };
    send({ type: 'trace', event: { sequence: 1, phase: 'retrieval', elapsed_ms: 12, message: 'Smoke: retrieving independent evidence.' } });
  });
  try {
    await new Promise((resolve) => mock.listen(0, '127.0.0.1', resolve));
    const mockOrigin = `http://127.0.0.1:${mock.address().port}`;
    const port = process.env.BROWSER_SMOKE_PORT || '4178';
    const origin = `http://127.0.0.1:${port}`;
    vite = spawn(process.execPath, [join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', port, '--strictPort'], {
      cwd: root, env: { ...process.env, VITE_API_URL: '/api' }, stdio: ['ignore', 'pipe', 'pipe'],
    });
    vite.stdout.on('data', (chunk) => { viteLog += chunk; });
    vite.stderr.on('data', (chunk) => { viteLog += chunk; });
    let spawnError;
    vite.on('error', (error) => { spawnError = error; });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (spawnError) throw spawnError;
      if (vite.exitCode !== null) throw new Error(`Vite exited: ${viteLog}`);
      // Wait for this subprocess, rather than accepting a pre-existing server.
      if (viteLog.includes('ready in')) {
        try { ready = (await fetch(origin)).ok; } catch { /* Startup in progress. */ }
      }
      if (ready) break;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    assert.ok(ready, `Vite did not become ready: ${viteLog}`);
    browser = await chromium.launch({ headless: true });
    for (const [name, viewport] of [['desktop', { width: 1440, height: 1000 }], ['mobile', { width: 390, height: 844 }]]) {
      const context = await browser.newContext({ viewport, isMobile: name === 'mobile', hasTouch: name === 'mobile', serviceWorkers: 'block' });
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      page.on('pageerror', (error) => errors.push(`${name}: ${error.message}`));
      page.on('console', (message) => { if (message.type() === 'error') errors.push(`${name}: ${message.text()}`); });
      let configured = false;
      let model = 'gemini-smoke-model';
      const settingsCalls = [];
      await context.route('**/*', async (route) => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.pathname.startsWith('/api/settings/gemini')) {
          settingsCalls.push(request.method());
          assert.equal(request.headers()['x-verifyai-settings'], '1');
          let data = {};
          if (url.pathname.endsWith('/test')) {
            data = { provider: 'Mock Gemini', model, status: 'completed', duration_ms: 8, message: 'Smoke connection verified.' };
          } else if (request.method() === 'PUT') {
            const body = request.postDataJSON();
            assert.equal(body.api_key, 'synthetic-browser-smoke-key');
            model = body.model; configured = true;
          } else if (request.method() === 'DELETE') configured = false;
          else data = { configured, model };
          await route.fulfill({ json: data });
        } else if (/^\/api\/analyze\/(text|image|video|audio)$/.test(url.pathname)) {
          // route.fulfill buffers the body; continue to real HTTP to test streaming.
          await route.continue({ url: `${mockOrigin}${url.pathname}${url.search}` });
        } else if (['https://fonts.googleapis.com', 'https://fonts.gstatic.com'].includes(url.origin)) await route.continue();
        else if (url.origin === origin && !url.pathname.startsWith('/api/')) await route.continue();
        else { unexpected.push(request.url()); await route.abort(); }
      });
      const visible = (text) => page.getByText(text, { exact: true }).waitFor({ state: 'visible' });
      const noOverflow = async (stage) => {
        const size = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth }));
        assert.ok(size.document <= size.width && size.body <= size.width, `${name}/${stage}: horizontal overflow ${JSON.stringify(size)}`);
      };
      const shot = (stage) => page.screenshot({ path: join(artifacts, `${name}-${stage}.png`), fullPage: true });
      const choose = (label) => page.getByRole('group', { name: 'Content type' }).getByRole('button', { name: new RegExp(label) }).click();
      const start = async () => {
        pending = undefined;
        await page.getByRole('button', { name: /Analyze now/ }).click();
        await visible('Smoke: retrieving independent evidence.');
        assert.ok(pending);
        assert.equal(await page.getByRole('region', { name: 'Analysis report' }).count(), 0, 'Report must not appear before terminal event');
        await visible('Analysis in progress.');
      };
      const finish = async (type) => {
        pending.send({ type: 'result', result: {
          content_type: type, verdict: 'inconclusive', summary: 'Smoke report: independent review required.', explanation: 'Synthetic deterministic browser fixture.',
          processing_time_ms: 42, details: [], uncertainties: ['Smoke uncertainty: source coverage is incomplete.'],
          recommended_action: 'Smoke action: consult the original publisher before sharing.',
          investigation: { claims: [{ id: 'claim-1', text: 'Smoke claim for verification.', verdict: 'insufficient_evidence', reasoning: 'Only one synthetic source was retrieved.',
            uncertainties: ['Smoke claim uncertainty: no independent corroboration.'], evidence: [{ id: 'E1', url: 'https://example.com/smoke-evidence', title: 'Smoke evidence source', publisher: 'Example publisher', retrieved_at: '2026-01-01T00:00:00Z', excerpt: 'Synthetic evidence excerpt.', stances: ['supported'], cited_quotes: ['Synthetic validated quotation.'] }] }] },
          provenance: [{ provider: 'Smoke provider', model: 'mock-model', status: 'completed', duration_ms: 20, message: 'Smoke provider request completed.', coverage: { submitted: true, description: 'Smoke coverage: submitted sample only.' }, observations: ['Smoke observation: limited sample.'], limitations: ['Smoke limitation: not an authenticity guarantee.'] }],
        } });
        pending.res.end();
        await page.getByRole('region', { name: 'Analysis report' }).waitFor();
        await visible('Analysis complete. Report available below.');
      };
      try {
        await page.goto(origin);
        await page.evaluate(() => document.fonts.ready);
        await page.getByRole('heading', { level: 1 }).waitFor();
        await visible('Not configured');
        await noOverflow('initial');
        await shot('initial');
        await choose('Text');
        await page.getByRole('textbox', { name: 'Text to verify' }).fill('A synthetic claim to check.');
        await start();
        assert.deepEqual(JSON.parse(requests.at(-1).body), { text: 'A synthetic claim to check.' });
        assert.equal(requests.at(-1).url, '/api/analyze/text?stream=true');
        assert.equal(requests.at(-1).headers.accept, 'application/x-ndjson');
        pending.send({ type: 'trace', event: { sequence: 2, phase: 'assessment', elapsed_ms: 24, message: 'Smoke: comparing source quotations.' } });
        await visible('Smoke: comparing source quotations.');
        assert.equal(await page.getByRole('log').locator('li').count(), 2);
        assert.equal(await page.getByRole('region', { name: 'Analysis report' }).count(), 0);
        await noOverflow('stream');
        await shot('stream');
        await finish('text');
        for (const text of ['Smoke uncertainty: source coverage is incomplete.', 'Smoke action: consult the original publisher before sharing.', 'Smoke coverage: submitted sample only.', 'Smoke limitation: not an authenticity guarantee.', 'Synthetic evidence excerpt.', 'Smoke claim uncertainty: no independent corroboration.']) await visible(text);
        const evidence = page.getByRole('link', { name: 'Smoke evidence source' });
        assert.equal(await evidence.getAttribute('href'), 'https://example.com/smoke-evidence');
        assert.equal(await evidence.getAttribute('rel'), 'noopener noreferrer');
        await noOverflow('report');
        await shot('report');
        await start();
        await page.getByRole('button', { name: 'Cancel analysis' }).click();
        await visible('Analysis cancelled. No final result is available.');
        // Attempt a late result on the cancelled response; it must never reappear.
        pending.send({ type: 'result', result: { summary: 'STALE RESULT MUST NOT RENDER' } });
        pending.res.end();
        await page.waitForTimeout(150);
        assert.equal(await page.getByRole('region', { name: 'Analysis report' }).count(), 0);
        assert.equal(await page.getByRole('alert').count(), 0);
        assert.ok(await page.getByRole('button', { name: /Analyze now/ }).isEnabled());
        await noOverflow('cancel');
        await shot('cancel');
        for (const [label, type, extension, mime, accept] of [
          ['Image', 'image', 'png', 'image/png', '.jpg,.jpeg,.png,.webp'],
          ['Video', 'video', 'mp4', 'video/mp4', '.mp4,.mov,.avi,.webm'],
          ['Voice', 'audio', 'wav', 'audio/wav', '.mp3,.wav,.m4a,.ogg'],
        ]) {
          await choose(label);
          const input = page.getByLabel(`Choose ${label.toLowerCase()} file`);
          assert.equal(await input.getAttribute('accept'), accept);
          assert.ok(await page.getByRole('button', { name: /Analyze now/ }).isDisabled());
          await input.setInputFiles({ name: `synthetic.${extension}`, mimeType: mime, buffer: Buffer.from('Synthetic upload; no real media or personal data.') });
          await visible(`synthetic.${extension}`);
          await start();
          assert.equal(requests.at(-1).method, 'POST');
          assert.equal(requests.at(-1).url, `/api/analyze/${type}?stream=true`);
          assert.match(requests.at(-1).headers['content-type'], /multipart\/form-data; boundary=/);
          assert.ok(requests.at(-1).body.includes(`filename="synthetic.${extension}"`));
          await finish(type);
          await noOverflow(type);
        }
        await page.getByLabel('Gemini API key', { exact: true }).fill('synthetic-browser-smoke-key');
        await page.getByLabel('Model', { exact: true }).fill('smoke-custom-model');
        await page.getByRole('button', { name: 'Save settings', exact: true }).click();
        await visible('Settings saved for this backend session.');
        await visible('Configured');
        assert.equal(await page.getByLabel('Gemini API key', { exact: true }).inputValue(), '');
        await page.getByRole('button', { name: 'Test Gemini Connection', exact: true }).click();
        await page.getByText(/Smoke connection verified\./).waitFor();
        await noOverflow('settings');
        await shot('settings');
        await page.getByRole('button', { name: 'Clear session key', exact: true }).click();
        await visible('Not configured');
        assert.ok(['GET', 'PUT', 'POST', 'DELETE'].every((method) => settingsCalls.includes(method)));
        assert.equal(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }).includes('synthetic-browser-smoke-key')), false);
        console.log(`PASS ${name} ${viewport.width}x${viewport.height}: load, overflow, incremental stream, evidence/provenance, uncertainty/action, cancel, four input modes, settings`);
      } catch (error) {
        await shot('failure').catch(() => {});
        errors.push(`${name}: ${error.stack}`);
      } finally { await context.close(); }
    }
    assert.deepEqual(unexpected, [], 'Unexpected network requests (external access blocked)');
    assert.deepEqual(errors, [], 'Browser smoke failures');
    console.log(`Screenshots: ${artifacts}`);
  } finally {
    await browser?.close();
    mock.closeAllConnections();
    await new Promise((resolve) => mock.close(resolve));
    if (vite && vite.exitCode === null) {
      const exited = new Promise((resolve) => vite.once('exit', resolve));
      vite.kill();
      await exited;
    }
  }
}

// Node also discovers .mjs inside tests/; keep transport-test runs browser-free.
if (!process.env.NODE_TEST_CONTEXT) {
  main().catch((error) => { console.error(error); process.exitCode = 1; });
}
