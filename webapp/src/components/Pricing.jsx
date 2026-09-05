import React from 'react';
import './Pricing.css';

const Pricing = ({ onTryFree }) => {
  return (
    <div className="pricing-section container animate-fade-in">
      <div className="pricing-header">
        <div className="section-stamp">Unlimited Verification</div>
        <h2>PRICING PLANS</h2>
        <p className="lead-text">
          VerifyAI is a free tool designed to make media verification accessible to everyone.
          No subscription required, no hidden credit card captures.
        </p>
      </div>

      <div className="pricing-grid">
        {/* Free Plan Card */}
        <div className="glass-card pricing-card popular">
          <div className="card-badge">UNLIMITED · ACTIVE</div>
          <div className="plan-name">FREE TIER</div>
          <div className="price-tag">
            <span className="amount">$0</span>
            <span className="period">/ LIFETIME</span>
          </div>
          <p className="plan-desc">For journalists, teachers, and concerned citizens seeking truth.</p>
          <ul className="plan-features">
            <li>✓ Unlimited Image Forensic Audits</li>
            <li>✓ Unlimited Video Deepfake Scans</li>
            <li>✓ Unlimited Cloned Voice Checks</li>
            <li>✓ Unlimited Text Claim Verifications</li>
            <li>✓ Full PDF Forensic Report Generation</li>
            <li>✓ Credits never expire (Unlimited balance)</li>
          </ul>
          <button className="btn btn-glow plan-btn" onClick={onTryFree}>
            START SCANNING
          </button>
        </div>

        {/* Enterprise/Self-host Info Card */}
        <div className="glass-card pricing-card">
          <div className="plan-name">SELF-HOST / API</div>
          <div className="price-tag">
            <span className="amount">OPEN</span>
            <span className="period">SOURCE</span>
          </div>
          <p className="plan-desc">For developers and teams wishing to run VerifyAI locally.</p>
          <ul className="plan-features">
            <li>✓ Fully Local Execution</li>
            <li>✓ Swagger/OpenAPI Specs</li>
            <li>✓ HuggingFace & Librosa Pipelines</li>
            <li>✓ Groq Llama 3.3 Integration</li>
            <li>✓ MIT License</li>
            <li>✓ Zero Third-Party Data Tracking</li>
          </ul>
          <a 
            className="btn btn-secondary plan-btn" 
            href="https://github.com/yash23082007/TruthLensAi" 
            target="_blank" 
            rel="noopener noreferrer"
          >
            VIEW CODEBASE
          </a>
        </div>
      </div>

      {/* Trust banner */}
      <div className="glass-card billing-trust-card">
        <div className="trust-item">
          <span className="trust-icon">🔒</span>
          <div>
            <h4>Privacy-First Default</h4>
            <p>Your uploaded media is processed in memory and deleted immediately after analysis.</p>
          </div>
        </div>
        <div className="trust-item">
          <span className="trust-icon">🌐</span>
          <div>
            <h4>100% Free Coverage</h4>
            <p>No paywalls or premium tiers. Enjoy full API and UI feature access free.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
