import React from 'react';

const FeatureCards = () => {
  const features = [
    {
      title: 'Deepfake Forensics',
      desc: 'Frame-by-frame temporal analysis spotting face-swaps and lip-sync anomalies.',
      icon: '🎭'
    },
    {
      title: 'Voice Clone Detection',
      desc: 'Spectral analysis detecting synthetic speech and zero-crossing manipulation.',
      icon: '🎙️'
    },
    {
      title: 'Generative AI Vision',
      desc: 'Heuristics that identify pixel-level uniform noise and diffusion artifacts.',
      icon: '🖼️'
    },
    {
      title: 'Phishing NLP',
      desc: 'Advanced language models trained on the latest social engineering tactics.',
      icon: '🎣'
    },
    {
      title: 'RAG Claim Verification',
      desc: 'Cross-references statements against verified, constantly updated databases.',
      icon: '📚'
    },
    {
      title: 'Explainable AI',
      desc: 'No black boxes. We explain exactly why content was flagged with full transparency.',
      icon: '⚡'
    }
  ];

  return (
    <section id="features" className="container" style={{ padding: '100px 24px' }}>
      <div style={{ textAlign: 'center', marginBottom: '64px' }}>
        <h2 style={{ fontSize: '3rem', marginBottom: '16px' }}>Forensic AI Pipeline</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto', fontSize: '1.1rem' }}>
          TruthLens AI orchestrates multiple specialized models to evaluate truth across every dimension of digital media.
        </p>
      </div>

      <div className="bento-grid" style={{ gap: '20px' }}>
        {features.map((feat, idx) => (
          <div key={idx} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '32px' }}>
            <div style={{ 
              fontSize: '1.5rem', 
              background: 'var(--bg-primary)', 
              width: '48px', height: '48px', 
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: '12px', border: '1px solid var(--border-light)'
            }}>
              {feat.icon}
            </div>
            <h3 style={{ fontSize: '1.25rem', marginTop: '8px' }}>{feat.title}</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: '1.6' }}>{feat.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default FeatureCards;
