import React, { useState } from 'react';
import './DifferentDeepfakes.css';

const DifferentDeepfakes = () => {
  const [activeIndex, setActiveIndex] = useState(0);

  const samples = [
    {
      title: "Social Media Profile",
      percentage: "89%",
      type: "Deepfake",
      label: "Profile Pic swap detected",
      description: "AI-generated profile image mimicking a real user identity to conduct organic outreach.",
      badgeColor: "var(--status-danger)",
      emoji: "👤"
    },
    {
      title: "Parade Images",
      percentage: "45%",
      type: "Manipulated",
      label: "Pixel edits & splicing",
      description: "Edited photograph with cloned background segments to exaggerate crowd sizes.",
      badgeColor: "var(--status-warning)",
      emoji: "📸"
    },
    {
      title: "Financial Document",
      percentage: "31%",
      type: "Low Risk",
      label: "Consistent signature scan",
      description: "Scanned document showing mild compression anomalies but clean content integrity.",
      badgeColor: "var(--status-success)",
      emoji: "📊"
    },
    {
      title: "Video Calls",
      percentage: "67%",
      type: "High Risk",
      label: "Lip-sync anomaly found",
      description: "Sample frames show blurred facial boundaries matching real-time face-swap pipelines.",
      badgeColor: "var(--status-danger)",
      emoji: "🎥"
    },
    {
      title: "News Media",
      percentage: "15%",
      type: "Authentic",
      label: "Original EXIF headers intact",
      description: "Unmodified press release graphic with complete metadata lineage and camera signatures.",
      badgeColor: "var(--status-success)",
      emoji: "📰"
    },
    {
      title: "Scam Calls",
      percentage: "94%",
      type: "Deepfake",
      label: "TTS Speech cloned",
      description: "Synthesized audio clip with flat pitch profiles matching advanced neural voice generators.",
      badgeColor: "var(--status-danger)",
      emoji: "📞"
    }
  ];

  const handleNext = () => {
    setActiveIndex((prev) => (prev + 3 >= samples.length ? 0 : prev + 3));
  };

  const handlePrev = () => {
    setActiveIndex((prev) => (prev - 3 < 0 ? samples.length - 3 : prev - 3));
  };

  return (
    <section className="different-deepfakes-section container">
      <div className="features-header left-aligned-section">
        <div className="section-stamp">Visual Verification</div>
        <h2>DIFFERENT DEEPFAKE SCANS</h2>
        <p>
          Whether for research, profile verification, or security checks, here is how the TruthLens AI detection pipeline identifies various forms of synthetic manipulation.
        </p>
      </div>

      <div className="carousel-wrapper">
        <button className="carousel-arrow prev" onClick={handlePrev} aria-label="Previous samples">
          ◀
        </button>

        <div className="carousel-grid">
          {samples.slice(activeIndex, activeIndex + 3).map((item, idx) => (
            <div key={idx} className="glass-card sample-card animate-fade-in">
              <div className="sample-card-header">
                <span className="sample-icon">{item.emoji}</span>
                <span className="sample-badge" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', color: item.badgeColor, border: `1px solid ${item.badgeColor}` }}>
                  {item.percentage} {item.type}
                </span>
              </div>
              <h3>{item.title}</h3>
              <div className="sample-label">{item.label}</div>
              <p>{item.description}</p>
            </div>
          ))}
        </div>

        <button className="carousel-arrow next" onClick={handleNext} aria-label="Next samples">
          ▶
        </button>
      </div>

      <div className="carousel-dots">
        <button 
          className={`dot ${activeIndex === 0 ? 'active' : ''}`}
          onClick={() => setActiveIndex(0)}
        ></button>
        <button 
          className={`dot ${activeIndex === 3 ? 'active' : ''}`}
          onClick={() => setActiveIndex(3)}
        ></button>
      </div>
    </section>
  );
};

export default DifferentDeepfakes;
