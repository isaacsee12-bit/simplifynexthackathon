// Content Script injected into all pages
// Used to extract specific content from the DOM when requested by the extension

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_PAGE_TEXT") {
    // Extract main text content from the page (simplified)
    const text = document.body.innerText;
    
    // Send a subset to avoid huge payloads
    sendResponse({ 
      text: text.substring(0, 10000) 
    });
  }
  return true;
});
