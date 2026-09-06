export async function readAnalysisStream(response, { onEvent, signal } = {}) {
  if (!response.ok) throw new Error(`Analysis request failed (HTTP ${response.status}).`);
  if (!response.body) throw new Error('Analysis response has no stream.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '';
  const checkAbort = () => { if (signal?.aborted) throw new DOMException('Analysis cancelled.', 'AbortError'); };
  const abort = () => { void reader.cancel().catch(() => {}); };
  signal?.addEventListener('abort', abort, { once: true });
  const parse = (line) => {
    if (!line.trim()) return;
    let data;
    try { data = JSON.parse(line); } catch { throw new Error('Invalid JSON in analysis stream.'); }
    if (data?.type === 'error') throw new Error(typeof data.message === 'string' ? data.message : 'Analysis failed.');
    if (data?.type === 'result') {
      if (!data.result || typeof data.result !== 'object' || Array.isArray(data.result)) throw new Error('Invalid analysis result.');
      return data.result;
    }
    if (data?.type !== 'trace' || !data.event || !Number.isFinite(data.event.sequence) ||
        typeof data.event.phase !== 'string' || typeof data.event.message !== 'string' || !Number.isFinite(data.event.elapsed_ms)) {
      throw new Error('Invalid analysis stream event.');
    }
    onEvent?.(data.event);
  };
  try {
    while (true) {
      checkAbort();
      const { value, done } = await reader.read();
      checkAbort();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let newline;
      while ((newline = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        const result = parse(line);
        checkAbort();
        if (result) return result;
      }
      if (done) {
        const result = parse(buffer);
        checkAbort();
        if (result) return result;
        throw new Error('Analysis stream ended before a terminal result. Please retry.');
      }
    }
  } finally {
    signal?.removeEventListener('abort', abort);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
