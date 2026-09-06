import test from 'node:test';
import assert from 'node:assert/strict';
import { readAnalysisStream } from './analysisStream.js';

const event = { sequence: 1, phase: 'search', message: 'Caf\u00e9 \ud83d\udd0e', elapsed_ms: 12 };
const result = { summary: 'Reviewed', investigation: null, recommended_action: 'Review sources', uncertainties: [] };
const traceLine = JSON.stringify({ type: 'trace', event });
const resultLine = JSON.stringify({ type: 'result', result });
const response = (chunks) => new Response(new ReadableStream({ start(controller) {
  for (const chunk of chunks) controller.enqueue(typeof chunk === 'string' ? new TextEncoder().encode(chunk) : chunk);
  controller.close();
} }));

test('decodes every possible UTF-8 and JSON chunk boundary, CRLF and blank lines', async () => {
  const bytes = new TextEncoder().encode(`\r\n${traceLine}\r\n\n${resultLine}\n`);
  for (let i = 1; i < bytes.length; i++) {
    const events = [];
    assert.deepEqual(await readAnalysisStream(response([bytes.slice(0, i), bytes.slice(i)]), { onEvent: (e) => events.push(e) }), result);
    assert.deepEqual(events, [event]);
  }
});

test('one-byte chunks and terminal line without newline', async () => {
  const bytes = new TextEncoder().encode(`${traceLine}\n${resultLine}`);
  assert.deepEqual(await readAnalysisStream(response([...bytes].map((b) => Uint8Array.of(b)))), result);
});

test('delivers trace before terminal response arrives', async () => {
  let controller;
  const events = [];
  const stream = new ReadableStream({ start(c) { controller = c; } });
  const pending = readAnalysisStream(new Response(stream), { onEvent: (e) => events.push(e) });
  controller.enqueue(new TextEncoder().encode(`${traceLine}\n`));
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(events, [event]);
  controller.enqueue(new TextEncoder().encode(resultLine));
  controller.close();
  assert.deepEqual(await pending, result);
});

test('requires terminal result and rejects malformed protocol', async () => {
  for (const content of ['', `${traceLine}\n`, '{', '{"type":"unknown"}', '{"type":"result","result":null}', '{"type":"trace","event":{}}']) {
    await assert.rejects(readAnalysisStream(response([content])));
  }
  await assert.rejects(readAnalysisStream(response([Uint8Array.of(255)])));
});

test('propagates service errors, including after traces', async () => {
  await assert.rejects(readAnalysisStream(response([`${traceLine}\n{"type":"error","message":"Provider unavailable"}\n`])), /Provider unavailable/);
});

test('rejects HTTP failures and absent response bodies', async () => {
  await assert.rejects(readAnalysisStream(new Response('failure', { status: 503 })), /503/);
  await assert.rejects(readAnalysisStream(new Response(null)), /no stream/);
});

test('aborts pending reads and cancels the stream', async () => {
  const controller = new AbortController();
  let cancelled = false;
  const pending = readAnalysisStream(new Response(new ReadableStream({ cancel() { cancelled = true; } })), { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.equal(cancelled, true);
});

test('already aborted signal emits no events', async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(readAnalysisStream(response([`${traceLine}\n${resultLine}`]), { signal: controller.signal, onEvent: () => assert.fail('stale event') }), { name: 'AbortError' });
});

test('network interruption cannot become a successful partial result', async () => {
  await assert.rejects(readAnalysisStream(new Response(new ReadableStream({ start(c) { c.error(new Error('Connection lost')); } }))), /Connection lost/);
});

test('terminal result cancels an open response and releases its lock', async () => {
  let cancelled = false;
  const stream = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode(`${resultLine}\n`)); }, cancel() { cancelled = true; } });
  assert.deepEqual(await readAnalysisStream(new Response(stream)), result);
  assert.equal(cancelled, true);
  assert.equal(stream.locked, false);
});
