// API utility for communicating with the FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Upload and analyze media files or text
 * @param {File|string} content - The file to upload or text string
 * @param {string} type - 'text', 'image', 'video', or 'audio'
 * @returns {Promise<Object>} Analysis result
 */
export const analyzeContent = async (content, type) => {
  const endpoint = `${API_BASE_URL}/analyze/${type}`;
  
  try {
    let options = {};
    
    if (type === 'text') {
      options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: content }),
      };
    } else {
      const formData = new FormData();
      formData.append('file', content);
      
      options = {
        method: 'POST',
        // Fetch automatically sets the correct multipart/form-data boundary
        body: formData,
      };
    }

    const response = await fetch(endpoint, options);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Analysis failed:', error);
    throw error;
  }
};

/**
 * Check backend health status
 */
export const checkHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  } catch (error) {
    console.error('Health check failed:', error);
    return { status: 'offline' };
  }
};
