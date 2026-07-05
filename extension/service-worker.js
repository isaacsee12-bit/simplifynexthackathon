// Extension Background Service Worker

const API_BASE_URL = 'http://localhost:8000/api';

// Create Context Menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "analyze_text",
    title: "Analyze Text with TruthLens AI",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "analyze_image",
    title: "Analyze Image with TruthLens AI",
    contexts: ["image"]
  });
});

// Handle Context Menu Clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  // Open the side panel first
  chrome.sidePanel.open({ tabId: tab.id });

  if (info.menuItemId === "analyze_text") {
    // Send selected text to side panel
    setTimeout(() => {
      chrome.runtime.sendMessage({
        action: "START_ANALYSIS",
        type: "text",
        content: info.selectionText
      });
    }, 500); // Give side panel time to load
  } 
  else if (info.menuItemId === "analyze_image") {
    // Send image URL to side panel
    setTimeout(() => {
      chrome.runtime.sendMessage({
        action: "START_ANALYSIS",
        type: "image_url",
        content: info.srcUrl
      });
    }, 500);
  }
});

// Handle messages from popup or content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "OPEN_SIDE_PANEL") {
    // Determine the current tab and open side panel
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      if (tabs.length > 0) {
        chrome.sidePanel.open({ tabId: tabs[0].id });
      }
    });
    sendResponse({ success: true });
    return true;
  }
  
  if (request.action === "FETCH_ANALYSIS") {
    analyzeContent(request.type, request.content)
      .then(result => sendResponse({ success: true, result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    
    // Return true to indicate asynchronous response
    return true;
  }
});

async function analyzeContent(type, content) {
  let endpoint = `${API_BASE_URL}/analyze/${type}`;
  let options = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  };

  if (type === 'text') {
    options.body = JSON.stringify({ text: content });
  } else if (type === 'image_url') {
    // We would ideally fetch the image and send as form data, 
    // but for this implementation we assume the backend handles it or we pass it as text to text analyzer
    // To keep it simple, we'll route to text analyzer if it's just a URL string or implement a specific endpoint
    throw new Error("Direct image URL analysis requires backend support. Please download and upload via Dashboard.");
  }

  const response = await fetch(endpoint, options);
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return await response.json();
}
