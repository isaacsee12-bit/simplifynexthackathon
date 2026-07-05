document.getElementById('btn-open-panel').addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: "OPEN_SIDE_PANEL" });
  window.close();
});

document.getElementById('btn-analyze-page').addEventListener('click', async () => {
  // First open the side panel
  chrome.runtime.sendMessage({ action: "OPEN_SIDE_PANEL" });
  
  // Then get the page text
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  
  chrome.tabs.sendMessage(tab.id, { action: "GET_PAGE_TEXT" }, (response) => {
    if (response && response.text) {
      // Send text to background to start analysis
      chrome.runtime.sendMessage({
        action: "START_ANALYSIS",
        type: "text",
        content: response.text
      });
    }
  });
  
  window.close();
});
