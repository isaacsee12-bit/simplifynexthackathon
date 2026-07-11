import React, { useState, useCallback, useEffect } from 'react';
import './UploadZone.css';
import { analyzeContent } from '../utils/api';

const UploadZone = ({ onAnalysisComplete, preselectedType, setPreselectedType, routeType = 'home' }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [activeTab, setActiveTab] = useState('file');
  const [error, setError] = useState('');

  // Auto-switch tabs based on routeType or preselectedType
  useEffect(() => {
    if (routeType === 'text') {
      setActiveTab('text');
    } else if (routeType !== 'home') {
      setActiveTab('file');
    }
  }, [routeType]);

  // Handle preselected tool redirection from Navbar/Footer
  useEffect(() => {
    if (preselectedType) {
      if (preselectedType === 'text') {
        setActiveTab('text');
      } else {
        setActiveTab('file');
      }
      setTimeout(() => {
        document.getElementById('upload-zone')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
      setPreselectedType(null);
    }
  }, [preselectedType, setPreselectedType]);

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

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

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

  // Mock demo results for interactive verification without actual file uploads
  const handleTriggerExample = (type, sampleIdx) => {
    setIsAnalyzing(true);
    setError('');

    setTimeout(() => {
      setIsAnalyzing(false);
      let mockResult = {};

      if (type === 'image') {
        if (sampleIdx === 1) {
          mockResult = {
            id: "mock-img-1",
            content_type: "image",
            timestamp: new Date().toISOString(),
            trust_score: 87.5,
            risk_level: "critical",
            is_authentic: false,
            summary: "⚠️ CRITICAL: Mismatched ELA compression and face anomalies detected.",
            explanation: "Visual Forensics Report:\n🔴 [AI Generation] Face detected with extreme symmetry (diff=1.2) and smooth texture.\n🔴 [Manipulation] Error Level Analysis (ELA) shows localized compression inconsistency (σ=142.1).\n⚡ [AI Generation] DCT frequency analysis shows GANcheckerboard spikes.",
            details: [
              { category: "AI Generation", finding: "Face shows unnaturally high symmetry (diff=1.2)", confidence: 0.92, severity: "critical" },
              { category: "Manipulation", finding: "ELA grid variance exceeds safety threshold (σ=142.1)", confidence: 0.88, severity: "high" },
              { category: "AI Generation", finding: "Frequency spectrum autolink checkerboard peaks detected", confidence: 0.76, severity: "medium" }
            ],
            processing_time_ms: 120
          };
        } else {
          mockResult = {
            id: "mock-img-2",
            content_type: "image",
            timestamp: new Date().toISOString(),
            trust_score: 12.0,
            risk_level: "low",
            is_authentic: true,
            summary: "🟢 LOW RISK: Image details appear natural and authentic.",
            explanation: "Visual Forensics Report:\n✅ [Manipulation] Camera EXIF metadata present: Apple iPhone 15 Pro.\n✅ [Manipulation] ELA compression variance is uniform (σ=12.4).\n✅ [Deepfake Detection] Skin texture Laplacian variance is realistic.",
            details: [
              { category: "Manipulation", finding: "Camera EXIF metadata present (Apple iPhone 15 Pro)", confidence: 0.95, severity: "low" },
              { category: "Manipulation", finding: "Uniform compression across all segments (σ=12.4)", confidence: 0.85, severity: "low" }
            ],
            processing_time_ms: 95
          };
        }
      } else if (type === 'video') {
        mockResult = {
          id: "mock-vid-1",
          content_type: "video",
          timestamp: new Date().toISOString(),
          trust_score: 92.4,
          risk_level: "critical",
          is_authentic: false,
          summary: "⚠️ CRITICAL: High-ratio frame deepfake and facial jitter detected.",
          explanation: "Video Forensics Report:\n🔴 [Deepfake Detection] 11 of 15 sampled frames flagged as AI-generated.\n🔴 [Deepfake Detection] Erratic face tracking positional jitter detected across adjacent frames.\n⚡ [Manipulation] Re-encoded container metadata blocks detected (moov atom duplicate).",
          details: [
            { category: "Deepfake Detection", finding: "11 of 15 frames classified as AI-generated by CNN model", confidence: 0.94, severity: "critical" },
            { category: "Deepfake Detection", finding: "Face position jitter variance exceeds threshold (CV=2.45)", confidence: 0.85, severity: "high" },
            { category: "Manipulation", finding: "Duplicate moov atoms detected in container", confidence: 0.60, severity: "medium" }
          ],
          total_frames: 450,
          deepfake_frames: 330,
          processing_time_ms: 250
        };
      } else if (type === 'audio') {
        mockResult = {
          id: "mock-aud-1",
          content_type: "audio",
          timestamp: new Date().toISOString(),
          trust_score: 94.0,
          risk_level: "critical",
          is_authentic: false,
          summary: "⚠️ CRITICAL: Voice cloning and flat pitch transitions detected.",
          explanation: "Audio Forensics Report:\n🔴 [AI Generation] Autocorrelation of pitch shows flat F0 variance (CV=0.015).\n🔴 [AI Generation] MFCC spectral shape reveals low variability (σ=4.12).\n⚡ [AI Generation] Pause distribution intervals are mathematically uniform (CV=0.12).",
          details: [
            { category: "AI Generation", finding: "Flat pitch envelope CV is below human threshold (CV=0.015)", confidence: 0.95, severity: "critical" },
            { category: "AI Generation", finding: "MFCC envelope shows unnaturally low spectral variance (σ=4.12)", confidence: 0.92, severity: "high" },
            { category: "AI Generation", finding: "TTS silence intervals are mathematically uniform", confidence: 0.78, severity: "medium" }
          ],
          processing_time_ms: 180
        };
      }

      onAnalysisComplete(mockResult);
    }, 1500);
  };

  // Determine accepted file formats and copy based on routeType
  const getUploadSpecs = () => {
    switch (routeType) {
      case 'image':
        return {
          accept: "image/*",
          title: "Drag & drop an image or click",
          desc: "PNG, JPG, WEBP formats supported up to 10MB",
          exampleLabel: "Or try with example images:",
          examples: [
            { label: "Example AI Profile", onClick: () => handleTriggerExample('image', 1) },
            { label: "Example Camera Photo", onClick: () => handleTriggerExample('image', 2) }
          ]
        };
      case 'video':
        return {
          accept: "video/*",
          title: "Drag & drop a video or click",
          desc: "MP4, MOV, WEBM formats supported up to 50MB",
          exampleLabel: "Or try with example videos:",
          examples: [
            { label: "Example AI Lipsync", onClick: () => handleTriggerExample('video', 1) }
          ]
        };
      case 'audio':
        return {
          accept: "audio/*",
          title: "Drag & drop an audio file or click",
          desc: "MP3, WAV, OGG, FLAC formats supported up to 20MB",
          exampleLabel: "Or try with example voices:",
          examples: [
            { label: "Example Cloned Voice", onClick: () => handleTriggerExample('audio', 1) }
          ]
        };
      default:
        return {
          accept: "image/*,video/*,audio/*",
          title: "DRAG & DROP",
          desc: "Images, Video, or Audio formats supported",
          exampleLabel: "Try quick forensic samples:",
          examples: [
            { label: "Test AI Face", onClick: () => handleTriggerExample('image', 1) },
            { label: "Test Cloned Speech", onClick: () => handleTriggerExample('audio', 1) }
          ]
        };
    }
  };

  const specs = getUploadSpecs();

  return (
    <div id="upload-zone" className="upload-section container animate-fade-in">
      <div className="upload-container">
        {routeType === 'home' && (
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
        )}

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
              accept={specs.accept}
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
                <h3>{specs.title}</h3>
                <p>{specs.desc}</p>
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
        
        {/* Render example files tailored to current section */}
        {!isAnalyzing && (
          <div className="example-picker-wrapper">
            <p className="example-label">{specs.exampleLabel}</p>
            <div className="example-buttons">
              {specs.examples.map((ex, idx) => (
                <button 
                  key={idx} 
                  className="btn btn-secondary btn-small"
                  onClick={ex.onClick}
                >
                  {ex.label}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {error && <div className="error-message" style={{position: 'absolute', bottom: '-75px', left: '50%', transform: 'translateX(-50%)', color: 'var(--status-danger)'}}>{error}</div>}
      </div>
    </div>
  );
};

export default UploadZone;
