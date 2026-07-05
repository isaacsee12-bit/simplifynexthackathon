import React from 'react';
import './AnalysisResult.css';

const RiskBadge = ({ riskLevel }) => {
  const getRiskStyles = (level) => {
    switch (level?.toLowerCase()) {
      case 'low': return { icon: '🟢', class: 'risk-low', label: 'Low Risk' };
      case 'medium': return { icon: '🟡', class: 'risk-medium', label: 'Medium Risk' };
      case 'high': return { icon: '🔴', class: 'risk-high', label: 'High Risk' };
      case 'critical': return { icon: '⚠️', class: 'risk-critical', label: 'Critical Risk' };
      default: return { icon: '⚪', class: 'risk-unknown', label: 'Unknown' };
    }
  };

  const style = getRiskStyles(riskLevel);

  return (
    <div className={`risk-badge ${style.class}`}>
      <span className="risk-icon">{style.icon}</span>
      <span className="risk-label">{style.label}</span>
    </div>
  );
};

export default RiskBadge;
