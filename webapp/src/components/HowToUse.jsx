import React from 'react';
import './HowToUse.css';

const HowToUse = () => {
  const steps = [
    {
      step: "01",
      title: "UPLOAD CONTENT",
      desc: "Drag and drop or select your media files (images, video, audio) or type in text claims to inspect."
    },
    {
      step: "02",
      title: "AI PROCESSING",
      desc: "The system runs parallel forensic neural networks and metadata evaluations in under 5 seconds."
    },
    {
      step: "03",
      title: "REVIEW FINDINGS",
      desc: "Get an authenticity score (0-100%) and a fully explained breakdown of detected anomalies."
    },
    {
      step: "04",
      title: "SHARE REPORT",
      desc: "Download the forensic verification log or copy a secure validation link for your records."
    }
  ];

  return (
    <section className="how-to-use-section container">
      <div className="features-header left-aligned-section">
        <div className="section-stamp">Instructional flow</div>
        <h2>HOW TO USE TRUTHLENS AI</h2>
        <p>
          Content verification is direct and simple. Follow this process to scan, analyze, and document authenticity status.
        </p>
      </div>

      <div className="steps-grid">
        {steps.map((item, idx) => (
          <div key={idx} className="glass-card step-card">
            <div className="step-number">{item.step}</div>
            <h3>{item.title}</h3>
            <p>{item.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

export default HowToUse;
