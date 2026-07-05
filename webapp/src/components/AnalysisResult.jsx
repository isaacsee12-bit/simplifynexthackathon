import React from 'react';
import TrustScoreGauge from './TrustScoreGauge';
import RiskBadge from './RiskBadge';
import './AnalysisResult.css';

const AnalysisResult = ({ result, onReset }) => {
  if (!result) return null;

  return (
    <div id="results-view" className="results-section container animate-fade-in">
      <div className="results-header">
        <h2>Analysis Result</h2>
        <button className="btn btn-secondary" onClick={onReset}>New Scan</button>
      </div>

      <div className="results-grid">
        {/* Left Column: Summary */}
        <div className="glass-card result-summary">
          <div className="score-container">
            <TrustScoreGauge score={result.trust_score} />
          </div>
          
          <div className="status-container">
            <RiskBadge riskLevel={result.risk_level} />
            <h3 className="status-title">
              {result.is_authentic ? 'Likely Authentic' : 'Manipulation Detected'}
            </h3>
            <p className="status-summary">{result.summary}</p>
          </div>
        </div>

        {/* Right Column: Detailed Explanation */}
        <div className="glass-card result-details">
          <div className="details-header">
            <h3>Detailed Findings</h3>
            <span className="content-badge">{result.content_type} Analysis</span>
          </div>
          
          <div className="explanation-text">
            <p className="spacer">{result.explanation.split('\n')[0]}</p>
            
            <div className="findings-list">
              {result.details && result.details.length > 0 ? (
                result.details.map((detail, idx) => {
                  const icon = detail.severity === 'critical' ? '⚠️' : 
                               detail.severity === 'high' ? '🔴' : 
                               detail.severity === 'medium' ? '⚡' : '✅';
                  return (
                    <div key={idx} className="finding-item">
                      <span className="finding-icon">{icon}</span>
                      <div className="finding-content">
                        <strong>{detail.category}</strong>
                        <span>{detail.finding} (Confidence: {Math.round(detail.confidence * 100)}%)</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="finding-item">
                  <span className="finding-icon">✅</span>
                  <div className="finding-content">
                    <strong>Clear</strong>
                    <span>No specific anomalies or manipulation detected.</span>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <div className="metadata-footer">
            <span>Processed in {result.processing_time_ms}ms via Fast API</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisResult;
