import React from 'react';
import './Navbar.css';

const Navbar = () => {
  return (
    <nav className="navbar glass-panel">
      <div className="navbar-container">
        <div className="navbar-logo">
          <span className="logo-text">TruthLens <span className="text-gradient">AI</span></span>
        </div>
        <div className="navbar-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">Technology</a>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
            GitHub
          </a>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
