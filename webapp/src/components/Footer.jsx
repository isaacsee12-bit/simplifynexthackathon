import React from 'react';
import './Footer.css';

const Footer = ({ onChangePage, onSelectTool }) => {
  return (
    <footer className="footer-bar">
      <div className="container footer-container">
        <div className="footer-brand">
          <div className="footer-logo">
            <span>TRUTHLENS <span className="logo-accent">AI</span></span>
          </div>
          <span className="footer-tagline">Multimodal Content Verification</span>
        </div>
        
        <div className="footer-links-grid">
          <div className="footer-col">
            <h4>Detection Tools</h4>
            <a href="#" onClick={(e) => { e.preventDefault(); onSelectTool('image'); }}>📷 Image Detection</a>
            <a href="#" onClick={(e) => { e.preventDefault(); onSelectTool('video'); }}>🎥 Video Detection</a>
            <a href="#" onClick={(e) => { e.preventDefault(); onSelectTool('audio'); }}>🎙️ Audio Detection</a>
            <a href="#" onClick={(e) => { e.preventDefault(); onSelectTool('text'); }}>📝 Text Verification</a>
          </div>

          <div className="footer-col">
            <h4>Company</h4>
            <a href="#" onClick={(e) => { e.preventDefault(); onChangePage('about'); }}>About Us</a>
            <a href="#" onClick={(e) => { e.preventDefault(); onChangePage('privacy'); }}>Privacy Policy</a>
            <a href="#" onClick={(e) => { e.preventDefault(); onChangePage('terms'); }}>Terms of Use</a>
          </div>

          <div className="footer-col">
            <h4>Developers</h4>
            <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">API Documentation</a>
            <a href="https://www.linkedin.com/in/yash-vijay-b0a75937a?utm_source=share_via&utm_content=profile&utm_medium=member_android" target="_blank" rel="noopener noreferrer">LinkedIn</a>
            <a href="mailto:ktanayash@gmail.com">Contact Support</a>
          </div>
        </div>
      </div>
      <div className="footer-bottom container">
        <p>© 2026 TruthLens AI. All rights reserved. Free content authenticity tool.</p>
      </div>
    </footer>
  );
};

export default Footer;
