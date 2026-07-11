import React from 'react';
import './FeatureCards.css';

const FeatureCards = () => {
  const features = [
    {
      title: 'DEEPFAKE FORENSICS',
      desc: 'Frame-by-frame temporal analysis spotting face-swaps and lip-sync anomalies.',
      icon: '🎭'
    },
    {
      title: 'VOICE CLONE DETECTION',
      desc: 'Spectral analysis detecting synthetic speech and zero-crossing manipulation.',
      icon: '🎙️'
    },
    {
      title: 'GENERATIVE AI VISION',
      desc: 'Heuristics that identify pixel-level uniform noise and diffusion artifacts.',
      icon: '🖼️'
    },
    {
      title: 'PHISHING NLP',
      desc: 'Advanced language models trained on the latest social engineering tactics.',
      icon: '🎣'
    },
    {
      title: 'RAG CLAIM VERIFICATION',
      desc: 'Cross-references statements against verified, constantly updated databases.',
      icon: '📚'
    },
    {
      title: 'EXPLAINABLE AI',
      desc: 'No black boxes. We explain exactly why content was flagged with full transparency.',
      icon: '⚡'
    }
  ];

  return (
    <section id="features" className="container features-section">
      <div className="features-header">
        <div className="section-stamp">Forensic Capabilities</div>
        <h2>DETECTION PIPELINE</h2>
        <p>
          TruthLens AI orchestrates multiple specialized models to evaluate truth across every dimension of digital media.
        </p>
      </div>

      <div className="bento-grid">
        {features.map((feat, idx) => (
          <div key={idx} className="glass-card feature-card">
            <div className="feature-icon-wrapper">
              {feat.icon}
            </div>
            <h3>{feat.title}</h3>
            <p>{feat.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default FeatureCards;
