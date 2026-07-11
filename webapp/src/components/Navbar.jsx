import React from 'react';
import './Navbar.css';

const Navbar = ({ currentPage, onChangePage }) => {
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
