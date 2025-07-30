import React, { useState } from 'react';
import './ViewPartner.css';

const API_BASE_URL = 'http://localhost:5000';
const DEFAULT_FRONTEND_ICON_PATH = '/icons/question-mark.png';

const reverseDetectionSettingMap = {
  PERSON: 'Person',
  IC_NUMBER: 'IC Number',
  US_PASSPORT: 'Passport',
  EMAIL_ADDRESS: 'Email',
  LOCATION: 'Address / Geographic',
  US_BANK_NUMBER: 'Bank Number',
  PHONE_NUMBER: 'Phone Number',
  CREDIT_CARD: 'Credit Card',
};

function ViewPartner({ partner, onClose }) {
  const [showEncryptionKey, setShowEncryptionKey] = useState(false);
  const [showFilePassword, setShowFilePassword] = useState(false);

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
  if (partner.logo && partner.logo !== '/icons/question-mark.png') {
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
            <p><strong>Name: </strong>{partner.name}</p>
            <p><strong>Detection Settings: </strong>
            {partner.detection_settings && partner.detection_settings.length > 0
              ? partner.detection_settings.map(code => reverseDetectionSettingMap[code] || code).join(', ')
              : 'None selected'}
            </p>

            <div>
              <strong>Data Encryption Key:</strong>
              <input
                type={showEncryptionKey ? 'text' : 'password'}
                value="hahahaha123"
                readOnly
                className="password-field"
              />
              <label>
                <br />
                <input
                  type="checkbox"
                  checked={showEncryptionKey}
                  onChange={() => setShowEncryptionKey(!showEncryptionKey)}
                /> Show Encryption Key
              </label>
            </div>

            <div>
              <strong>File Password:</strong>
              <input
                type={showFilePassword ? 'text' : 'password'}
                value="abc123"
                readOnly
                className="password-field"
              />
              <label>
                <br/>
                <input
                  type="checkbox"
                  checked={showFilePassword}
                  onChange={() => setShowFilePassword(!showFilePassword)}
                /> Show Password
              </label>
            </div>
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
