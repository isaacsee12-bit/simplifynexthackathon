import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import UploadZone from './components/UploadZone';
import AnalysisResult from './components/AnalysisResult';
import FeatureCards from './components/FeatureCards';
import Footer from './components/Footer';
import './index.css';

function App() {
  const [analysisResult, setAnalysisResult] = useState(null);

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
      
      <Navbar />
      
      <main>
        <Hero />
        <UploadZone onAnalysisComplete={handleAnalysisComplete} />
        {analysisResult && (
          <AnalysisResult result={analysisResult} onReset={handleReset} />
        )}
        <FeatureCards />
      </main>

      <Footer />
    </div>
  );
}

export default App;
