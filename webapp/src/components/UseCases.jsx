import React from 'react';
import './UseCases.css';

const UseCases = () => {
  const cases = [
    {
      title: "Teachers Spotting Fake Historical Photos",
      description: "History educators utilize TruthLens AI to demonstrate digital verification methods in classrooms. By uploading viral historical pictures, students see how metadata checks and visual analysis separate authentic history from doctored representations, raising media literacy.",
      icon: "🎓"
    },
    {
      title: "Journalists Verifying Viral Videos",
      description: "Reporters run user-generated footage through the video forensic pipeline to verify clips before publication. Spotting frame inconsistencies and face-swap jitter protects publications from reporting fake incidents and spreading misinformation.",
      icon: "📰"
    },
    {
      title: "Creators Protecting Online Identity",
      description: "Streamers and online creators scan web uploads to track if their face or voice clones are being used to run unauthorized ads or promotional scams, enabling swift takedown actions to protect their reputation.",
      icon: "✨"
    },
    {
      title: "Families Checking Deepfake Scam Calls",
      description: "With synthetic voice cloning on the rise, parents use TruthLens AI to verify suspicious distress voice notes. Detecting unnatural voice spectral patterns offers families quick peace of mind against digital kidnapping scams.",
      icon: "🛡️"
    }
  ];

  return (
    <section className="use-cases-section container">
      <div className="features-header left-aligned-section">
        <div className="section-stamp">Real-World Utility</div>
        <h2>WHO BENEFITS FROM TRUTHLENS AI?</h2>
        <p>
          Generative AI tools are open to everyone, which means detection must be too. Here is how different groups stay safe and informed.
        </p>
      </div>

      <div className="use-cases-grid">
        {cases.map((item, idx) => (
          <div key={idx} className="glass-card use-case-card">
            <div className="use-case-icon">{item.icon}</div>
            <div className="use-case-content">
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default UseCases;
