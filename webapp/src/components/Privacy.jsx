import React from 'react';
import './Legal.css';

const Privacy = () => {
  return (
    <div className="legal-section animate-fade-in">
      <h2>PRIVACY POLICY</h2>
      <p>Last updated: October 2023</p>
      
      <h3>1. Information We Collect</h3>
      <p>We collect information that you provide directly to us when you use the VerifyAI platform. This may include uploaded media files, text inputs, and usage logs required for verification analysis.</p>

      <h3>2. How We Use Your Information</h3>
      <p>We use the information we collect primarily to provide, maintain, and improve our multimodal content verification services. Uploaded content is processed temporarily for analysis and is not stored permanently unless explicitly opted-in by the user for model training.</p>

      <h3>3. Data Security</h3>
      <p>We implement appropriate technical and organizational measures to protect the security of your personal information. However, please note that no method of transmission over the Internet is 100% secure.</p>

      <h3>4. Contact Us</h3>
      <p>If you have any questions about this Privacy Policy, please contact us at <a href="mailto:ktanayash@gmail.com" style={{color: 'var(--accent-cyan)'}}>ktanayash@gmail.com</a>.</p>
    </div>
  );
};

export default Privacy;
