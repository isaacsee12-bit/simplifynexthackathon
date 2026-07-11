import React, { useState } from 'react';
import './Navbar.css';

const Navbar = ({ currentPage, onChangePage, onSelectTool }) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleToolClick = (toolType) => {
    setDropdownOpen(false);
    if (onSelectTool) {
      onSelectTool(toolType);
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo" onClick={() => onChangePage('home')} style={{ cursor: 'pointer' }}>
          <span className="logo-text">TRUTHLENS <span className="logo-accent">AI</span></span>
        </div>
        <div className="navbar-links">
          <button 
            className={`nav-btn ${currentPage === 'home' ? 'active' : ''}`}
            onClick={() => onChangePage('home')}
          >
            HOME
          </button>

          {/* Replicating the tools dropdown from deepfakedetection.io */}
          <div 
            className="dropdown-wrapper"
            onMouseEnter={() => setDropdownOpen(true)}
            onMouseLeave={() => setDropdownOpen(false)}
          >
            <button className="nav-btn dropdown-trigger">
              DETECTION TOOLS <span className="arrow-indicator">▼</span>
            </button>
            {dropdownOpen && (
              <div className="dropdown-menu">
                <button className="dropdown-item" onClick={() => handleToolClick('image')}>
                  📷 Image Detection
                </button>
                <button className="dropdown-item" onClick={() => handleToolClick('video')}>
                  🎥 Video Detection
                </button>
                <button className="dropdown-item" onClick={() => handleToolClick('audio')}>
                  🎙️ Audio Detection
                </button>
                <button className="dropdown-item" onClick={() => handleToolClick('text')}>
                  📝 Text Verification
                </button>
              </div>
            )}
          </div>

          <button 
            className={`nav-btn ${currentPage === 'features' ? 'active' : ''}`}
            onClick={() => onChangePage('features')}
          >
            FEATURES
          </button>
          <button 
            className={`nav-btn ${currentPage === 'about' ? 'active' : ''}`}
            onClick={() => onChangePage('about')}
          >
            ABOUT
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
