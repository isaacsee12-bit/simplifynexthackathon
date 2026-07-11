import React, { useEffect, useState } from 'react';
import './AnalysisResult.css';

const TrustScoreGauge = ({ score }) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 1200; // ms
    const steps = 60;
    const stepTime = duration / steps;
    const increment = score / steps;
    let currentScore = 0;

    const timer = setInterval(() => {
      currentScore += increment;
      if (currentScore >= score) {
        setAnimatedScore(score);
        clearInterval(timer);
      } else {
        setAnimatedScore(Math.round(currentScore));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [score]);

  // Convert "Manipulation Score" (trust_score) to "Authenticity Score" for UX
  const authenticityScore = Math.round(Math.max(0, 100 - animatedScore));
  
  let colorClass = 'gauge-success';
  if (authenticityScore < 40) colorClass = 'gauge-danger';
  else if (authenticityScore < 70) colorClass = 'gauge-warning';

  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (authenticityScore / 100) * circumference;

  return (
    <div className="gauge-container">
      <svg className="gauge-svg" width="160" height="160" viewBox="0 0 160 160">
        <circle 
          className="gauge-bg" 
          cx="80" cy="80" r={radius} 
          strokeWidth="10" 
          fill="none" 
        />
        <circle 
          className={`gauge-progress ${colorClass}`} 
          cx="80" cy="80" r={radius} 
          strokeWidth="10" 
          fill="none" 
          strokeLinecap="round"
          style={{ 
            strokeDasharray: circumference, 
            strokeDashoffset: strokeDashoffset,
            transition: 'stroke-dashoffset 0.1s linear'
          }}
          transform="rotate(-90 80 80)"
        />
      </svg>
      <div className="gauge-text">
        <span className="gauge-value">{authenticityScore}%</span>
        <span className="gauge-label">Authentic</span>
      </div>
    </div>
  );
};

export default TrustScoreGauge;
