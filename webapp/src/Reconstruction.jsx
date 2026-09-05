import React, { useRef, useState } from 'react';
import { analyzeContent } from './utils/api';
import './reconstruction.css';

const modes = {
  image: { label: 'Image', formats: 'JPG, PNG, WEBP up to 15 MB', accept: 'image/*', icon: 'IMG' },
  video: { label: 'Video', formats: 'MP4, MOV, AVI, WEBM up to 50 MB', accept: 'video/*', icon: 'VID' },
  audio: { label: 'Voice', formats: 'MP3, WAV, M4A, OGG up to 20 MB', accept: 'audio/*', icon: 'AUD' },
  text: { label: 'Text', formats: 'Paste a message or article to verify', accept: '', icon: 'TXT' },
};

export default function Reconstruction() {
  const [mode, setMode] = useState('image');
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const selectedMode = modes[mode];

  const chooseMode = (nextMode) => { setMode(nextMode); setFile(null); setText(''); setResult(null); setError(''); setStatus('idle'); };
  const runAnalysis = async () => {
    const content = mode === 'text' ? text.trim() : file;
    if (!content) return;
    setStatus('analyzing'); setError('');
    try { setResult(await analyzeContent(content, mode)); setStatus('complete'); }
    catch (analysisError) { setError(analysisError.message || 'The analysis service is unavailable.'); setStatus('error'); }
  };
  const onFileChange = (event) => { const selectedFile = event.target.files?.[0]; if (selectedFile) setFile(selectedFile); };
  const authenticity = result ? Math.max(0, Math.round(100 - result.trust_score)) : null;

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#top" aria-label="VerifyAI home"><span className="brand-mark">SG</span><span>VerifyAI</span></a><nav className="nav-links" aria-label="Primary navigation"><a href="#verify">Verify</a><a href="#how-it-works">How it works</a><a href="#trust">Why VerifyAI</a></nav><a className="nav-privacy" href="#privacy">Private by design <span>-&gt;</span></a></header>
    <main id="top">
      <section className="hero" id="verify"><div className="hero-copy"><p className="eyebrow"><span className="status-dot" /> Singapore digital trust</p><h1>Pause. Check. Then <em>share.</em></h1><p className="hero-lede">VerifyAI checks images, video, voice, and text for signs of manipulation before misinformation travels further.</p><div className="hero-proof"><strong>4 modes</strong><span>one clear verification report<br />for everyday digital content</span></div></div>
        <div className="verify-card"><div className="card-heading"><div><span className="mini-label">01 / CONTENT CHECK</span><h2>What would you like to verify?</h2></div><span className="live-pill"><span className="status-dot" /> SG online</span></div>
          <div className="mode-tabs" role="tablist" aria-label="Content type">{Object.entries(modes).map(([key, item]) => <button key={key} role="tab" aria-selected={mode === key} className={mode === key ? 'active' : ''} onClick={() => chooseMode(key)}><span className="mode-icon">{item.icon}</span>{item.label}</button>)}</div>
          {mode === 'text' ? <textarea className="text-entry" value={text} onChange={(event) => setText(event.target.value)} placeholder="Paste a suspicious message, claim, or article here..." aria-label="Text to verify" /> : <><input ref={inputRef} className="sr-only" type="file" accept={selectedMode.accept} onChange={onFileChange} /><button className={`drop-area ${file ? 'has-file' : ''}`} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setFile(event.dataTransfer.files?.[0] || null); }}><span className="upload-symbol">{file ? 'OK' : '+'}</span><strong>{file ? file.name : 'Drop your file here'}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(1)} MB ready to scan` : 'or click to browse your device'}</span></button></>}
          <div className="card-footer"><span className="format-note">{selectedMode.formats}</span><button className="scan-button" disabled={status === 'analyzing' || !(mode === 'text' ? text.trim() : file)} onClick={runAnalysis}>{status === 'analyzing' ? 'Analyzing...' : 'Verify content  ->'}</button></div>{error && <p className="error-message" role="alert">{error}</p>}{status === 'analyzing' && <div className="progress-line"><span /></div>}
        </div>
      </section>
      {result && <section className="result-section" aria-live="polite"><div><p className="eyebrow">Analysis complete</p><h2>{result.is_authentic ? 'This looks authentic.' : 'Suspicious indicators found.'}</h2><p>{result.summary}</p></div><div className="score"><strong>{authenticity}%</strong><span>authenticity<br />confidence</span></div><div className="result-meta"><span>Risk level <b className={`risk-${result.risk_level}`}>{result.risk_level}</b></span><span>Processed in {Math.round(result.processing_time_ms)} ms</span></div></section>}
      <section className="signal-strip" id="trust"><div><span className="signal-number">01</span><strong>Human-readable results</strong><span>Every score comes with the why.</span></div><div><span className="signal-number">02</span><strong>Four ways to verify</strong><span>Image, video, voice, and text.</span></div><div id="privacy"><span className="signal-number">03</span><strong>Privacy first</strong><span>Your files are processed, then deleted.</span></div></section>
      <section className="content-section" id="how-it-works"><div className="section-intro"><p className="eyebrow">02 / THE PROCESS</p><h2>A digital second opinion for everyday Singapore.</h2><p>Fast enough for a group chat. Clear enough to act on. VerifyAI turns hard-to-see signals into a report you can understand before you forward.</p></div><div className="steps"><div><span>01</span><h3>Upload</h3><p>Choose a file or paste text. No account required.</p></div><div><span>02</span><h3>Analyze</h3><p>Our multimodal pipeline checks the content for anomalies.</p></div><div><span>03</span><h3>Understand</h3><p>Get a confidence score and the evidence behind it.</p></div></div></section>
      <section className="closing-section"><p className="eyebrow">A clearer digital public square</p><h2>Before you forward it,<br /><em>verify it.</em></h2><a className="outline-button" href="#verify">Start a free check  -&gt;</a></section>
    </main><footer><a className="brand" href="#top"><span className="brand-mark">SG</span><span>VerifyAI</span></a><span>Designed for clearer digital decisions in Singapore.</span><span>© 2026 VerifyAI</span></footer>
  </div>;
}
