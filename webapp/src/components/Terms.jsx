import React from 'react';
import './Legal.css';

const Terms = () => {
  return (
    <div className="legal-section animate-fade-in">
      <h2>TERMS OF SERVICE</h2>
      <p>Last updated: October 2023</p>
      
      <h3>1. Acceptance of Terms</h3>
      <p>By accessing or using TruthLens AI, you agree to be bound by these Terms of Service. If you disagree with any part of the terms, you may not access our services.</p>

      <h3>2. Use License</h3>
      <p>Permission is granted to temporarily use TruthLens AI for personal or commercial content verification. You may not:</p>
      <ul>
        <li>Use the service for any illegal or unauthorized purpose</li>
        <li>Attempt to decompile or reverse engineer any software contained on the platform</li>
        <li>Transfer the materials to another person or "mirror" the materials on any other server</li>
      </ul>

      <h3>3. Disclaimer</h3>
      <p>The materials on TruthLens AI are provided on an 'as is' basis. While our AI models are highly accurate, they are not infallible. TruthLens AI makes no warranties, expressed or implied, regarding the absolute accuracy of the verification results.</p>

      <h3>4. Limitations</h3>
      <p>In no event shall TruthLens AI or its suppliers be liable for any damages (including, without limitation, damages for loss of data or profit) arising out of the use or inability to use the materials on the platform.</p>
    </div>
  );
};

export default Terms;
