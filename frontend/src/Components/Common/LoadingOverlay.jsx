import React from 'react';
import './LoadingOverlay.css'; // Create this CSS file

function LoadingOverlay({ message = "Loading..." }) {
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="spinner"></div> {/* Circular indicator */}
        <p>{message}</p>
      </div>
    </div>
  );
}

export default LoadingOverlay;