import React from 'react';

const Footer = () => {
  return (
    <footer className="glass-panel" style={{ marginTop: '80px', padding: '40px 24px', borderRadius: '24px 24px 0 0', borderBottom: 'none' }}>
      <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '24px' }}>
        <div>
          <div className="navbar-logo" style={{ marginBottom: '8px' }}>
            <span className="logo-icon">🔍</span>
            <span className="logo-text">TruthLens <span className="text-gradient">AI</span></span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>See through the lies.</p>
        </div>
        
        <div style={{ display: 'flex', gap: '24px' }}>
          <a href="#" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Privacy</a>
          <a href="#" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Terms</a>
          <a href="#" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>API</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
