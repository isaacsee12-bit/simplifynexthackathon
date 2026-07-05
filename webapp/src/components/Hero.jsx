import React from 'react';
import './Hero.css';

const Hero = () => {
  return (
    <section className="hero">
      <div className="hero-content animate-slide-up">
        <div className="hero-badge">
          <span className="badge-dot"></span>
          State-of-the-Art Content Verification
        </div>
        <h1 className="hero-title">
          See through <br/> the <span className="text-gradient">lies.</span>
        </h1>
        <p className="hero-subtitle">
          Advanced multimodal AI that detects deepfakes, generated images, synthesized voices, and phishing attempts with forensic precision.
        </p>
        <div className="hero-actions">
          <button className="btn btn-glow hero-btn" onClick={() => document.getElementById('upload-zone').scrollIntoView({ behavior: 'smooth' })}>
            Analyze Content
          </button>
          <a href="chrome://extensions" className="btn btn-secondary hero-btn">
            Get Extension
          </a>
        </div>
      </div>
      
      {/* Abstract background elements */}
      <div className="glow-orb orb-1"></div>
      <div className="glow-orb orb-2"></div>
    </section>
  );
};

export default Hero;
