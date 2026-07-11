import React from 'react';
import './Hero.css';

const Hero = () => {
  return (
    <section className="hero container">
      <div className="hero-content animate-slide-up">
        <div className="section-stamp">
          Content Verification Engine
        </div>
        <h1 className="hero-title">
          SEE THROUGH THE <span className="text-gradient">LIES.</span>
        </h1>
        <p className="hero-subtitle">
          Advanced forensic AI that analyzes images, videos, audio, and text to spot deepfakes, synthetic speech, and phishing attempts.
        </p>
        <div className="hero-actions">
          <button className="btn btn-glow hero-btn" onClick={() => document.getElementById('upload-zone').scrollIntoView({ behavior: 'smooth' })}>
            ANALYZE CONTENT
          </button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
