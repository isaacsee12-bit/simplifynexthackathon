import React from 'react';
import './Footer.css';

const Footer = ({ onChangePage }) => {
  return (
    <footer className="footer-bar">
      <div className="container footer-container">
        <div className="footer-brand">
          <div className="footer-logo">
            <span>TRUTHLENS <span className="logo-accent">AI</span></span>
          </div>
          <span className="footer-tagline">Multimodal Content Verification</span>
        </div>
        
        <div className="footer-links">
          <a href="#" onClick={(e) => { e.preventDefault(); onChangePage('privacy'); }}>Privacy</a>
          <a href="#" onClick={(e) => { e.preventDefault(); onChangePage('terms'); }}>Terms</a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">API Documentation</a>
          <a href="https://www.linkedin.com/in/yash-vijay-b0a75937a?utm_source=share_via&utm_content=profile&utm_medium=member_android" target="_blank" rel="noopener noreferrer">LinkedIn</a>
          <a href="mailto:ktanayash@gmail.com">Contact</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
