import React, { useState, useCallback } from 'react';
import './UploadZone.css';
import { analyzeContent } from '../utils/api';

const UploadZone = ({ onAnalysisComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [activeTab, setActiveTab] = useState('file');
  const [error, setError] = useState('');

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const processFile = async (file) => {
    if (!file) return;
    
    let type = 'image';
    if (file.type.startsWith('video/')) type = 'video';
    else if (file.type.startsWith('audio/')) type = 'audio';
    else if (file.type.startsWith('text/')) type = 'text';

    setIsAnalyzing(true);
    setError('');

    try {
      const result = await analyzeContent(file, type);
      onAnalysisComplete(result);
    } catch (err) {
      setError('Analysis failed. Ensure backend is running.');
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
      e.target.value = '';
    }
  };

  const handleTextAnalyze = async () => {
    if (!textInput.trim()) return;
    
    setIsAnalyzing(true);
    setError('');

    try {
      const result = await analyzeContent(textInput, 'text');
      onAnalysisComplete(result);
    } catch (err) {
      setError('Analysis failed. Ensure backend is running.');
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div id="upload-zone" className="upload-section container animate-fade-in">
      <div className="upload-container">
        <div className="upload-tabs">
          <button 
            className={`tab-btn ${activeTab === 'file' ? 'active' : ''}`}
            onClick={() => setActiveTab('file')}
          >
            UPLOAD MEDIA
          </button>
          <button 
            className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
            onClick={() => setActiveTab('text')}
          >
            VERIFY TEXT
          </button>
        </div>

        {activeTab === 'file' ? (
          <div 
            className={`drop-zone ${isDragging ? 'dragging' : ''} ${isAnalyzing ? 'analyzing' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input 
              type="file" 
              id="file-upload" 
              className="file-input" 
              onChange={handleFileInput}
              disabled={isAnalyzing}
              accept="image/*,video/*,audio/*"
            />
            
            {isAnalyzing ? (
              <div className="analyzing-state">
                <div className="spinner-rings"></div>
                <h3>ANALYZING CONTENT</h3>
                <p>Running multimodal verification models...</p>
              </div>
            ) : (
              <label htmlFor="file-upload" className="drop-content">
                <div className="upload-icon">📁</div>
                <h3>DRAG & DROP</h3>
                <p>Images, Video, or Audio formats supported</p>
                <div className="btn btn-secondary">SELECT FILE</div>
              </label>
            )}
          </div>
        ) : (
          <div className="text-zone">
            <textarea
              className="text-input"
              placeholder="Paste articles, claims, or emails here to detect misinformation and AI signatures..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              disabled={isAnalyzing}
            ></textarea>
            <div className="text-actions">
              <button 
                className="btn btn-primary" 
                onClick={handleTextAnalyze}
                disabled={isAnalyzing || !textInput.trim()}
              >
                {isAnalyzing ? 'PROCESSING...' : 'RUN ANALYSIS'}
              </button>
            </div>
          </div>
        )}
        
        {error && <div className="error-message" style={{position: 'absolute', bottom: '-40px', left: '50%', transform: 'translateX(-50%)', color: 'var(--status-danger)'}}>{error}</div>}
      </div>
    </div>
  );
};

export default UploadZone;
