import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import UploadZone from './components/UploadZone';
import AnalysisResult from './components/AnalysisResult';
import FeatureCards from './components/FeatureCards';
import About from './components/About';
import Footer from './components/Footer';
import Privacy from './components/Privacy';
import Terms from './components/Terms';
import './index.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [analysisResult, setAnalysisResult] = useState(null);

  const handlePageChange = (page) => {
    setCurrentPage(page);
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
      
      <Navbar currentPage={currentPage} onChangePage={handlePageChange} />
      
      <main>
        {currentPage === 'home' && (
          <>
            <Hero />
            <UploadZone onAnalysisComplete={handleAnalysisComplete} />
            {analysisResult && (
              <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}
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

      <Footer onChangePage={handlePageChange} />
    </div>
  );
}

export default App;
