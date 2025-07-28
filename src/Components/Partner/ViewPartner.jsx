import React from 'react';
import './ViewPartner.css';

const API_BASE_URL = 'http://localhost:5000';
const DEFAULT_FRONTEND_ICON_PATH = '/icons/default_partner_icon.svg';

function ViewPartner({ partner, onClose }) {

  if (!partner) {
    return (
      <div className="modal-overlay">
        <div className="view-partner-modal-content">
          <p>No partner selected for viewing.</p>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  let logoSrc;
  if (partner.logo && partner.logo !== '/icons/default_partner.svg') {
    logoSrc = `${API_BASE_URL}${partner.logo}`;
  } else {
    logoSrc = DEFAULT_FRONTEND_ICON_PATH;
  }

  return (
    <div className="modal-overlay">
      <div className="view-partner-modal-content">
        <div className="modal-header">
          <h2>Partner Details: {partner.name}</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="partner-icon-display">
            <img src={logoSrc} alt={`${partner.name} icon`} className="partner-view-icon" />
          </div>
          <div className="partner-details-display">
            <p><strong>Name:</strong> {partner.name}</p>
            <p><strong>Detection Settings:</strong> {partner.detection && partner.detection.length > 0 ? partner.detection.join(', ') : 'None selected'}</p>
          </div>
        </div>
        <div className="modal-footer">
          <button className="close-button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default ViewPartner;