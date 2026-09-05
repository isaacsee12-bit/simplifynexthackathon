import React from 'react';
import './About.css';

const About = () => {
  return (
    <div className="about-section container animate-fade-in">
      <div className="about-header">
        <div className="section-stamp">Technical Documentation</div>
        <h2>SYSTEM ARCHITECTURE</h2>
        <p className="lead-text">
          VerifyAI is a high-performance, multimodal content verification system. 
          It orchestrates deep learning models, heuristic analyzers, and real-time retrieval-augmented generation (RAG) pipelines 
          to identify synthetic media, manipulation signatures, and phishing attacks.
        </p>
      </div>

      <div className="technical-grid">
        {/* Component 1: Text Forensics */}
        <div className="glass-card tech-card">
          <div className="tech-icon-header">
            <span className="tech-icon">📝</span>
            <h3>TEXT FORENSICS PIPELINE</h3>
          </div>
          <p>
            Scans text content using a combination of transformer-based neural nets, pattern heuristics, and real-time retrieval:
          </p>
          <ul className="tech-features">
            <li>
              <strong>RoBERTa OpenAI Detector</strong>: Executes token classification using a fine-tuned RoBERTa model to detect synthetic writing styles and AI-generated outputs.
            </li>
            <li>
              <strong>Scam & Phishing Heuristics</strong>: Analyzes syntactic features for high-pressure urgency tactics, prize baits, credential requests, and suspicious shortened links.
            </li>
            <li>
              <strong>Live Wikipedia RAG</strong>: Extracts fact claims from text and issues search queries live to the Wikipedia API, processing snippets to verify consensus context.
            </li>
          </ul>
        </div>

        {/* Component 2: Image Forensics */}
        <div className="glass-card tech-card">
          <div className="tech-icon-header">
            <span className="tech-icon">🖼️</span>
            <h3>IMAGE FORENSICS PIPELINE</h3>
          </div>
          <p>
            Checks for visual alteration, compression artifacts, and generative AI noise:
          </p>
          <ul className="tech-features">
            <li>
              <strong>MobileNetV2 Neural Classifier</strong>: Utilizes convolutional feature extraction to detect low object confidence flags, signaling anomalous textures typical of diffusion networks.
            </li>
            <li>
              <strong>EXIF & JFIF Metadata Audits</strong>: Inspects files for stripped headers, format extension mismatches, and Adobe Photoshop software signatures.
            </li>
            <li>
              <strong>Chi-Squared byte testing</strong>: Evaluates frequency distributions on pixel segments to recognize uniform byte noise introduced by generative decoders.
            </li>
          </ul>
        </div>

        {/* Component 3: Audio Forensics */}
        <div className="glass-card tech-card">
          <div className="tech-icon-header">
            <span className="tech-icon">🎙️</span>
            <h3>AUDIO FORENSICS PIPELINE</h3>
          </div>
          <p>
            Identifies synthetic speech cloning and splicing anomalies:
          </p>
          <ul className="tech-features">
            <li>
              <strong>Transition Smoothness Ratio</strong>: Measures zero-crossing rates. While natural human speech has highly chaotic signal transitions, cloned voices exhibit uniform transitions.
            </li>
            <li>
              <strong>Synthesizer Signature Scan</strong>: Checks binary footings for strings from major voice cloning engines like ElevenLabs, Coqui, bark, and Tortoise-TTS.
            </li>
            <li>
              <strong>Silence Gap Analysis</strong>: Flags silent periods that match splicing boundaries or audio stitching.
            </li>
          </ul>
        </div>

        {/* Component 4: Video Forensics */}
        <div className="glass-card tech-card">
          <div className="tech-icon-header">
            <span className="tech-icon">🎭</span>
            <h3>VIDEO DEEPFAKE PIPELINE</h3>
          </div>
          <p>
            Implements frame-by-frame forensics and temporal evaluations:
          </p>
          <ul className="tech-features">
            <li>
              <strong>Temporal Sampling</strong>: Extracts structural video frames dynamically using OpenCV (`cv2`) to sample sections without incurring high processing delays.
            </li>
            <li>
              <strong>Frame Classification</strong>: Feeds sampled frame arrays into the deep learning pipeline to compute probability values for face swap and lipsync anomalies.
            </li>
            <li>
              <strong>Metadata Containers</strong>: Identifies duplicate or multiple header blocks (`moov` atoms) indicating re-encoding and tampering.
            </li>
          </ul>
        </div>
      </div>

      <div className="glass-card trust-engine-card">
        <div className="trust-engine-header">
          <span className="tech-icon">⚡</span>
          <h3>UNIFIED TRUST & RISK ENGINE</h3>
        </div>
        <p className="spacer">
          Individual results from the NLP, Vision, and Audio analyzers are aggregated into a single, cohesive Trust Score and threat level categorization.
        </p>
        
        <div className="bento-inner-grid">
          <div className="inner-col">
            <h4>Category Weights</h4>
            <ul className="engine-weights">
              <li><span>Deepfake Detection</span> <span className="weight-badge">30%</span></li>
              <li><span>AI Generation</span> <span className="weight-badge">25%</span></li>
              <li><span>Manipulation</span> <span className="weight-badge">20%</span></li>
              <li><span>Scam / Phishing</span> <span className="weight-badge">15%</span></li>
              <li><span>Claim Verification</span> <span className="weight-badge">10%</span></li>
            </ul>
          </div>
          
          <div className="inner-col">
            <h4>Severity Calibration</h4>
            <p>
              Anomalies are calibrated based on their severity multipliers, preventing minor/low-risk detections from incorrectly triggering warnings:
            </p>
            <div className="severity-bar">
              <span className="sev-tag low">LOW (0.1x)</span>
              <span className="sev-tag med">MEDIUM (0.4x)</span>
              <span className="sev-tag high">HIGH (0.8x)</span>
              <span className="sev-tag crit">CRITICAL (1.0x)</span>
            </div>
            <p className="formula-text">
              <code>Category Risk = max(confidence * severity_multiplier)</code>
              <br />
              <code>Trust Score = Sum(Category Risk * Weight) * 100</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default About;
