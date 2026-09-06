import React, { useEffect, useRef, useState } from 'react';
import { analyzeContent, isLocalSettingsHost, getGeminiSettings, saveGeminiSettings, clearGeminiSettings, testGeminiConnection } from './utils/api';
import './reconstruction.css';

const modes = {
  image: { label: 'Image', formats: 'JPG, PNG, WEBP up to 15 MB', accept: 'image/*', icon: 'IMG' },
  video: { label: 'Video', formats: 'MP4, MOV, AVI, WEBM up to 50 MB', accept: 'video/*', icon: 'VID' },
  audio: { label: 'Voice', formats: 'MP3, WAV, M4A, OGG up to 20 MB', accept: 'audio/*', icon: 'AUD' },
  text: { label: 'Text', formats: 'Paste a message or article to verify', accept: '', icon: 'TXT' },
};

function ApiSettings() {
  const local = isLocalSettingsHost();
  const [configured, setConfigured] = useState(null);
  const [model, setModel] = useState('gemini-3.8-flash');
  const [apiKey, setApiKey] = useState('');
  const [pending, setPending] = useState(local ? 'loading' : '');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [connection, setConnection] = useState(null);

  useEffect(() => {
    if (!local) return;
    let active = true;
    getGeminiSettings().then((settings) => {
      if (active) { setConfigured(settings.configured); setModel(settings.model); }
    }).catch((err) => { if (active) setError(err.message); })
      .finally(() => { if (active) setPending(''); });
    return () => { active = false; };
  }, [local]);

  const updateSettings = async (action) => {
    setPending(action); setError(''); setSuccess(''); setConnection(null);
    let completed = false;
    try {
      if (action === 'testing') {
        setConnection(await testGeminiConnection());
      } else if (action === 'saving') {
        await saveGeminiSettings({ api_key: apiKey, model: model.trim() });
        setApiKey(''); setSuccess('Settings saved for this backend session.'); completed = true;
      } else if (action === 'clearing') {
        await clearGeminiSettings();
        setApiKey(''); setSuccess('Session key cleared. Any environment key remains unchanged.'); completed = true;
      }
      const settings = await getGeminiSettings();
      setConfigured(settings.configured); setModel(settings.model);
    } catch (err) {
      setConfigured(null);
      setError(completed ? 'The change succeeded, but status could not be refreshed. Check the local backend and retry loading status.' : err.message);
    } finally { setPending(''); }
  };

  return <section className="api-settings content-section" id="api" aria-labelledby="api-title">
    <div className="section-intro"><p className="eyebrow">03 / LOCAL API SETTINGS</p><h2 id="api-title">Your engine.<br />Your session.</h2><p>Configure Gemini for this local backend session. Your key is never retrieved or saved in browser storage, and environment files stay unchanged.</p><p>Session overrides reset when the backend restarts. Use a single backend worker.</p></div>
    <form className="verify-card settings-card" aria-busy={Boolean(pending)} onSubmit={(event) => { event.preventDefault(); if (local && !pending && model.trim()) updateSettings('saving'); }}>
      <div className="settings-heading"><h3>Gemini API</h3><span className="settings-status" role="status">{pending === 'loading' ? 'Loading status...' : configured === null ? 'Status unknown' : configured ? 'Configured' : 'Not configured'}</span></div>
      {!local && <p className="settings-notice">API settings are local-only. Open this app on localhost, 127.0.0.1, or [::1] with a local backend to make changes. No settings requests are sent from this host.</p>}
      <fieldset disabled={!local || Boolean(pending)}>
        <label htmlFor="gemini-key">Gemini API key</label>
        <input id="gemini-key" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" spellCheck={false} aria-describedby="gemini-key-help" placeholder="Enter a new key" />
        <p id="gemini-key-help" className="settings-help">Leave blank to keep the existing key. Cleared from this field after a successful save.</p>
        <label htmlFor="gemini-model">Model</label>
        <input id="gemini-model" type="text" value={model} onChange={(event) => setModel(event.target.value)} required placeholder="gemini-3.8-flash" autoComplete="off" spellCheck={false} />
        <div className="settings-actions"><button className="scan-button" type="submit" disabled={!model.trim()}>{pending === 'saving' ? 'Saving...' : 'Save settings'}</button><button className="outline-button" type="button" onClick={() => updateSettings('clearing')}>{pending === 'clearing' ? 'Clearing...' : 'Clear session key'}</button></div>
        <button className="outline-button" type="button" onClick={() => updateSettings('testing')}>{pending === 'testing' ? 'Testing connection...' : 'Test Gemini Connection'}</button>
      </fieldset>
      <p className="settings-help">Configured means a key is present, not that it works. Save changes before testing. The test sends a minimal text request to the saved model and may incur provider usage; it does not verify media capability.</p>
      {connection && <p className={connection.status === 'completed' ? 'settings-success' : 'settings-notice'} role="status">{connection.provider} / {connection.model}: {connection.status.replaceAll('_', ' ')} ({Math.round(connection.duration_ms)} ms). {connection.message}</p>}
      <p className="settings-help">Clearing disables Gemini for this session. Environment files stay unchanged and are loaded again on backend restart.</p>
      {success && <p className="settings-success" role="status">{success}</p>}
      {error && <div><p className="error-message" role="alert">{error}</p><button className="outline-button" type="button" disabled={!local || Boolean(pending)} onClick={() => updateSettings('loading')}>{pending === 'loading' ? 'Loading...' : 'Retry loading status'}</button></div>}
    </form>
  </section>;
}

function AnalysisReport({ result }) {
  const title = result.verdict === 'suspicious' ? 'Suspicious indicators observed.'
    : result.verdict === 'no_indicators' ? 'No indicators in the analyzed sample.'
    : result.verdict === 'inconclusive' ? 'Inconclusive.' : 'Review the reported indicators.';
  const findings = result.details.filter((detail) => detail.category.toLowerCase().replaceAll(' ', '_') !== 'system_error');
  const unavailable = result.details.filter((detail) => detail.category.toLowerCase().replaceAll(' ', '_') === 'system_error');
  return <section className="result-section analysis-report" aria-live="polite">
    <div><p className="eyebrow">Analysis report / {result.content_type}</p><h2>{title}</h2><p>{result.summary}</p><p>{result.explanation}</p></div>
    <div className="result-meta"><span>Processed in {Math.round(result.processing_time_ms)} ms</span><span>No calibrated authenticity confidence is available.</span>{result.trust_score != null && <span>Legacy indicator score: {result.trust_score}/100 (not a probability)</span>}</div>
    {result.provenance?.map((source, index) => <article className="source-report" key={index}>
      <h3>{source.provider}{source.model && ` / ${source.model}`}</h3>
      <p><strong>{source.status.replaceAll('_', ' ')}</strong> / {Math.round(source.duration_ms)} ms / {source.coverage.submitted ? 'Provider request attempted' : 'No provider request sent'}</p>
      <p>{source.message}</p><h4>Coverage</h4><p>{source.coverage.description}</p>
      {source.coverage.media_duration_seconds != null && <p>Source duration: {source.coverage.media_duration_seconds} seconds.</p>}
      {source.coverage.analyzed_duration_seconds != null && <p>Sample duration: {source.coverage.analyzed_duration_seconds} seconds.</p>}
      {source.coverage.total_frames != null && <p>{source.coverage.media_parts} prepared frames out of {source.coverage.total_frames} source frames.</p>}
      {source.coverage.frame_timestamps_seconds?.length > 0 && <p>Frame timestamps (seconds): {source.coverage.frame_timestamps_seconds.join(', ')}.</p>}
      {source.observations.length > 0 && <><h4>Provider observations</h4><ul>{source.observations.map((item, i) => <li key={i}>{item}</li>)}</ul></>}
      {source.limitations.length > 0 && <><h4>Limitations</h4><ul>{source.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul></>}
    </article>)}
    <div className="source-report"><h3>{result.verdict ? 'Supplementary local and extracted-text findings' : 'Reported findings'}</h3><p>These indicators can have benign explanations. Legacy severity labels and heuristic confidence values are not calibrated forensic conclusions.</p>
      {findings.length ? <ul>{findings.map((detail, index) => <li key={index}><strong>{detail.category} / {detail.severity}:</strong> {detail.finding}</li>)}</ul> : <p>No supplementary findings.</p>}
      {unavailable.length > 0 && <><h4>Unavailable checks (not content risk)</h4><ul>{unavailable.map((detail, index) => <li key={index}>{detail.finding}</li>)}</ul></>}
      {result.extracted_text && <><h4>Text analyzed</h4><p>{result.extracted_text}</p></>}
    </div>
  </section>;
}

export default function Reconstruction() {
  const [mode, setMode] = useState('image');
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const analysisId = useRef(0);
  const selectedMode = modes[mode];

  const chooseMode = (nextMode) => { analysisId.current += 1; setMode(nextMode); setFile(null); setText(''); setResult(null); setError(''); setStatus('idle'); };
  const runAnalysis = async () => {
    const content = mode === 'text' ? text.trim() : file;
    if (!content) return;
    const id = ++analysisId.current;
    setStatus('analyzing'); setError(''); setResult(null);
    try { const response = await analyzeContent(content, mode); if (id === analysisId.current) { setResult(response); setStatus('complete'); } }
    catch (analysisError) { if (id === analysisId.current) { setError(analysisError.message || 'The analysis service is unavailable.'); setStatus('error'); } }
  };
  const changeContent = (value) => {
    analysisId.current += 1; setResult(null); setError(''); setStatus('idle');
    if (mode === 'text') setText(value); else setFile(value);
  };
  const onFileChange = (event) => { const selectedFile = event.target.files?.[0]; if (selectedFile) changeContent(selectedFile); };

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#top" aria-label="VerifyAI home"><span className="brand-mark">VA</span><span>VerifyAI</span></a><nav className="nav-links" aria-label="Primary navigation"><a href="#verify">Verify</a><a href="#how-it-works">How it works</a><a href="#trust">Why VerifyAI</a><a href="#api">API</a></nav><a className="nav-privacy" href="#privacy">Private by design <span>-&gt;</span></a></header>
    <main id="top">
      <section className="hero" id="verify"><div className="hero-copy"><p className="eyebrow"><span className="status-dot" /> Multimodal content verification</p><h1>Know what you are <em>really</em> looking at.</h1><p className="hero-lede">VerifyAI uses explainable AI to check images, video, voice, and text for signs of manipulation, so you can pause before you trust or share.</p><div className="hero-proof"><strong>50,000+</strong><span>files analyzed<br />with clear reports</span></div></div>
        <div className="verify-card"><div className="card-heading"><div><span className="mini-label">01 / VERIFY A FILE</span><h2>What would you like to check?</h2></div><span className="live-pill"><span className="status-dot" /> Live engine</span></div>
          <div className="mode-tabs" role="tablist" aria-label="Content type">{Object.entries(modes).map(([key, item]) => <button key={key} role="tab" aria-selected={mode === key} className={mode === key ? 'active' : ''} onClick={() => chooseMode(key)}><span className="mode-icon">{item.icon}</span>{item.label}</button>)}</div>
          {mode === 'text' ? <textarea className="text-entry" value={text} onChange={(event) => changeContent(event.target.value)} placeholder="Paste a suspicious message, claim, or article here..." aria-label="Text to verify" /> : <><input ref={inputRef} className="sr-only" type="file" accept={selectedMode.accept} onChange={onFileChange} /><button className={`drop-area ${file ? 'has-file' : ''}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); changeContent(event.dataTransfer.files?.[0] || null); }}><span className="upload-symbol">{file ? 'OK' : '+'}</span><strong>{file ? file.name : 'Drop your file here'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB ready to scan` : 'or click to browse your device'}</span></button></>}
          <div className="card-footer"><span className="format-note">{selectedMode.formats}</span><button className="scan-button" disabled={status === 'analyzing' || !(mode === 'text' ? text.trim() : file)} onClick={runAnalysis}>{status === 'analyzing' ? 'Analyzing...' : 'Analyze now  ->'}</button></div>{error && <p className="error-message" role="alert">{error}</p>}{status === 'analyzing' && <div className="progress-line"><span /></div>}
        </div>
      </section>
      <p className="settings-notice">When Gemini is configured, image previews, sampled video frames, or up to 60 seconds of decoded audio are sent to Google for analysis. Extracted-text claim checks may use external search services. Do not upload sensitive media without permission. Provider data policies apply.</p>
      {result && <AnalysisReport result={result} />}
      <section className="signal-strip" id="trust"><div><span className="signal-number">01</span><strong>Human-readable results</strong><span>Observations, coverage, and limitations.</span></div><div><span className="signal-number">02</span><strong>Four ways to verify</strong><span>Image, video, voice, and text.</span></div><div id="privacy"><span className="signal-number">03</span><strong>Know where data goes</strong><span>No upload archive in this app. Provider policies apply.</span></div></section>
      <section className="content-section" id="how-it-works"><div className="section-intro"><p className="eyebrow">02 / THE PROCESS</p><h2>A second opinion for the digital world.</h2><p>Fast enough for a scroll. Thoughtful enough for a newsroom. VerifyAI turns hard-to-see signals into a report you can act on.</p></div><div className="steps"><div><span>01</span><h3>Upload</h3><p>Choose a file or paste text. No account required.</p></div><div><span>02</span><h3>Analyze</h3><p>Our multimodal pipeline checks the content for anomalies.</p></div><div><span>03</span><h3>Understand</h3><p>Review the observations, their sources, and what remains unknown.</p></div></div></section>
      <ApiSettings />
      <section className="closing-section"><p className="eyebrow">Verification belongs to everyone</p><h2>Before you forward it,<br /><em>run it through VerifyAI.</em></h2><a className="outline-button" href="#verify">Start a free check  -&gt;</a></section>
    </main><footer><a className="brand" href="#top"><span className="brand-mark">VA</span><span>VerifyAI</span></a><span>Built for clearer decisions in an AI-shaped world.</span><span>© 2026 VerifyAI</span></footer>
  </div>;
}
