import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import UploadZone from './components/UploadZone';
import AnalysisResult from './components/AnalysisResult';
import FeatureCards from './components/FeatureCards';
import DifferentDeepfakes from './components/DifferentDeepfakes';
import HowToUse from './components/HowToUse';
import UseCases from './components/UseCases';
import FAQ from './components/FAQ';
import About from './components/About';
import Footer from './components/Footer';
import Privacy from './components/Privacy';
import Terms from './components/Terms';
import './index.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [preselectedType, setPreselectedType] = useState(null);

  const handlePageChange = (page) => {
    setCurrentPage(page);
    setAnalysisResult(null);
    window.scrollTo({ top: 0 });
  };

  const handleSelectTool = (toolType) => {
    setAnalysisResult(null);
    if (toolType === 'image') {
      setCurrentPage('image-detect');
    } else if (toolType === 'video') {
      setCurrentPage('video-detect');
    } else if (toolType === 'audio') {
      setCurrentPage('voice-detect');
    } else {
      setCurrentPage('home');
      setPreselectedType('text');
    }
    window.scrollTo({ top: 0 });
  };

  const handleAnalysisComplete = (result) => {
    setAnalysisResult(result);
    setTimeout(() => {
      document.getElementById('results-view')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleReset = () => {
    setAnalysisResult(null);
    document.getElementById('upload-zone')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      <div className="aurora-bg"></div>
      
      <Navbar 
        currentPage={currentPage} 
        onChangePage={handlePageChange} 
        onSelectTool={handleSelectTool} 
      />
      
      <main style={{ paddingTop: '64px' }}>
        {/* HOMEPAGE VIEW */}
        {currentPage === 'home' && (
          <>
            <Hero />
            <UploadZone 
              onAnalysisComplete={handleAnalysisComplete} 
              preselectedType={preselectedType}
              setPreselectedType={setPreselectedType}
              routeType="home"
            />
            {analysisResult && (
              <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}
            
            <DifferentDeepfakes />
            <HowToUse />
            <UseCases />
            <FAQ type="home" />
          </>
        )}

        {/* IMAGE DETECT PAGE */}
        {currentPage === 'image-detect' && (
          <>
            <section className="hero container animate-slide-up">
              <div className="hero-content">
                <div className="section-stamp">Visual Verification</div>
                <h1 className="hero-title">DEEPFAKE IMAGE DETECTION</h1>
                <p className="hero-subtitle">
                  Verify image authenticity instantly. Checks for localized pixel manipulation, ELA compression consistency, face texture smoothness, and GAN checkerboard artifacts.
                </p>
              </div>
            </section>
            
            <UploadZone 
              onAnalysisComplete={handleAnalysisComplete} 
              routeType="image"
            />
            
            {analysisResult && (
              <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}

            <DifferentDeepfakes />
            <FAQ type="image" />
          </>
        )}

        {/* VIDEO DETECT PAGE */}
        {currentPage === 'video-detect' && (
          <>
            <section className="hero container animate-slide-up">
              <div className="hero-content">
                <div className="section-stamp">Motion Analysis</div>
                <h1 className="hero-title">DEEPFAKE VIDEO DETECTION</h1>
                <p className="hero-subtitle">
                  Scan videos frame-by-frame for deepfake face swaps. Checks temporal consistency, tracks face bounding box jitter, and audits container atoms.
                </p>
              </div>
            </section>
            
            <UploadZone 
              onAnalysisComplete={handleAnalysisComplete} 
              routeType="video"
            />
            
            {analysisResult && (
              <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}

            <FAQ type="video" />
          </>
        )}

        {/* VOICE DETECT PAGE */}
        {currentPage === 'voice-detect' && (
          <>
            <section className="hero container animate-slide-up">
              <div className="hero-content">
                <div className="section-stamp">Spectral Auditing</div>
                <h1 className="hero-title">DEEPFAKE VOICE DETECTION</h1>
                <p className="hero-subtitle">
                  Detect voice clones and text-to-speech. Analyzes Mel-Frequency Cepstral Coefficients (MFCC), pitch consistency, and silence interval pause timings.
                </p>
              </div>
            </section>
            
            <UploadZone 
              onAnalysisComplete={handleAnalysisComplete} 
              routeType="audio"
            />
            
            {analysisResult && (
              <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}

            <FAQ type="audio" />
          </>
        )}
        
        {currentPage === 'features' && (
          <FeatureCards />
        )}
        
        {currentPage === 'about' && (
          <About />
        )}

        {currentPage === 'privacy' && (
          <Privacy />
        )}

        {currentPage === 'terms' && (
          <Terms />
        )}
      </main>

      <Footer 
        onChangePage={handlePageChange} 
        onSelectTool={handleSelectTool} 
      />
    </div>
  );
}

export default App;
