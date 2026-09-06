import { readAnalysisStream } from './analysisStream.js';

// API utility for communicating with the FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const isLocalSettingsHost = () =>
  typeof window !== 'undefined' && ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

const requestGeminiSettings = async (method, body, test = false) => {
  if (!isLocalSettingsHost()) throw new Error('API settings are available only on localhost, 127.0.0.1, or [::1].');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), test ? 40000 : 10000);
  try {
    // Never use the analysis API override or follow redirects with a secret.
    const response = await fetch(`/api/settings/gemini${test ? '/test' : ''}`, {
      method,
      headers: { 'X-VerifyAI-Settings': '1', ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      mode: 'same-origin', redirect: 'error', cache: 'no-store', signal: controller.signal,
    });
    if (!response.ok) throw new Error('Settings request failed');
    if (test) {
      const data = await response.json();
      if (typeof data.status !== 'string' || typeof data.message !== 'string' || typeof data.duration_ms !== 'number') throw new Error('Invalid test response');
      return data;
    }
    if (method === 'GET') {
      const data = await response.json();
      if (typeof data.configured !== 'boolean' || typeof data.model !== 'string') throw new Error('Invalid settings response');
      return { configured: data.configured, model: data.model };
    }
  } catch {
    throw new Error('Local API settings are unavailable. Start the backend with settings support and use the Vite dev server or backend-served frontend with same-origin /api routing, then retry.');
  } finally { clearTimeout(timeout); }
};

export const getGeminiSettings = () => requestGeminiSettings('GET');
export const saveGeminiSettings = ({ api_key, model }) =>
  requestGeminiSettings('PUT', { model, ...(api_key ? { api_key } : {}) });
export const clearGeminiSettings = () => requestGeminiSettings('DELETE');
export const testGeminiConnection = () => requestGeminiSettings('POST', undefined, true);

/**
 * Upload and analyze media files or text
 * @param {File|string} content - The file to upload or text string
 * @param {string} type - 'text', 'image', 'video', or 'audio'
 * @returns {Promise<Object>} Analysis result
 */
export const analyzeContent = async (content, type, { onEvent, signal } = {}) => {
  if (!['text', 'image', 'video', 'audio'].includes(type)) throw new Error('Unsupported content type.');
  const endpoint = `${API_BASE_URL}/analyze/${type}?stream=true`;
  
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

    const response = await fetch(endpoint, { ...options, signal, headers: { ...options.headers, Accept: 'application/x-ndjson' } });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    return await readAnalysisStream(response, { onEvent, signal });
  } catch (error) {
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
