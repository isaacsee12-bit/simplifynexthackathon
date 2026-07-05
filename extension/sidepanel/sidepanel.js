// Listen for messages from the service worker
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "START_ANALYSIS") {
    showLoading();
    
    // Call background script to fetch from API
    chrome.runtime.sendMessage(
      { action: "FETCH_ANALYSIS", type: request.type, content: request.content },
      (response) => {
        if (chrome.runtime.lastError || !response || !response.success) {
          showError((response && response.error) ? response.error : "Failed to connect to TruthLens API.");
        } else {
          showResults(response.result);
        }
      }
    );
  }
});

function showLoading() {
  document.getElementById('state-welcome').classList.add('hidden');
  document.getElementById('state-error').classList.add('hidden');
  document.getElementById('state-result').classList.add('hidden');
  document.getElementById('state-loading').classList.remove('hidden');
}

function showError(msg) {
  document.getElementById('state-loading').classList.add('hidden');
  document.getElementById('state-error').classList.remove('hidden');
  document.getElementById('error-message').textContent = msg;
}

function showResults(data) {
  document.getElementById('state-loading').classList.add('hidden');
  document.getElementById('state-result').classList.remove('hidden');
  
  // Parse data
  const authScore = Math.max(0, 100 - data.trust_score);
  
  // Set score
  const circle = document.getElementById('score-circle');
  document.getElementById('score-value').textContent = `${authScore}%`;
  
  if (authScore < 40) {
    circle.style.borderColor = '#ef4444'; // Red
    circle.style.color = '#ef4444';
  } else if (authScore < 70) {
    circle.style.borderColor = '#f59e0b'; // Amber
    circle.style.color = '#f59e0b';
  } else {
    circle.style.borderColor = '#10b981'; // Green
    circle.style.color = '#10b981';
  }
  
  // Set badge
  const riskBadge = document.getElementById('risk-badge');
  const riskIcon = document.getElementById('risk-icon');
  const riskLabel = document.getElementById('risk-label');
  
  const level = data.risk_level.toLowerCase();
  if (level === 'critical') {
    riskBadge.style.background = 'rgba(239, 68, 68, 0.2)';
    riskBadge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    riskBadge.style.color = '#ef4444';
    riskIcon.textContent = '⚠️';
    riskLabel.textContent = 'Critical Risk';
  } else if (level === 'high') {
    riskBadge.style.background = 'rgba(239, 68, 68, 0.1)';
    riskBadge.style.borderColor = 'rgba(239, 68, 68, 0.2)';
    riskBadge.style.color = '#fca5a5';
    riskIcon.textContent = '🔴';
    riskLabel.textContent = 'High Risk';
  } else if (level === 'medium') {
    riskBadge.style.background = 'rgba(245, 158, 11, 0.1)';
    riskBadge.style.borderColor = 'rgba(245, 158, 11, 0.2)';
    riskBadge.style.color = '#f59e0b';
    riskIcon.textContent = '🟡';
    riskLabel.textContent = 'Medium Risk';
  } else {
    riskBadge.style.background = 'rgba(16, 185, 129, 0.1)';
    riskBadge.style.borderColor = 'rgba(16, 185, 129, 0.2)';
    riskBadge.style.color = '#10b981';
    riskIcon.textContent = '🟢';
    riskLabel.textContent = 'Low Risk';
  }
  
  // Text content
  document.getElementById('result-title').textContent = data.is_authentic ? 'Likely Authentic' : 'Manipulation Detected';
  document.getElementById('result-summary').textContent = data.summary;
  
  // Details list
  const list = document.getElementById('details-list');
  list.innerHTML = '';
  
  if (data.details && data.details.length > 0) {
    data.details.forEach(d => {
      const item = document.createElement('div');
      item.className = 'detail-item';
      const icon = d.severity === 'critical' ? '⚠️' : d.severity === 'high' ? '🔴' : d.severity === 'medium' ? '⚡' : '✅';
      item.innerHTML = `<strong>${icon} [${d.category}]</strong><br/>${d.finding}`;
      list.appendChild(item);
    });
  } else {
    list.innerHTML = '<div class="detail-item">No specific anomalies detected.</div>';
  }
}
