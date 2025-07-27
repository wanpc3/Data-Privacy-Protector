import React, { useState, useRef } from 'react';
import './AddPartner.css';

function AddPartner({ onClose, onCreatePartner }) {
  const [partnerName, setPartnerName] = useState('');
  const [dataEncryptionKey, setDataEncryptionKey] = useState('');
  const [filePassword, setFilePassword] = useState('');
  const [logo, setLogo] = useState(null);
  const fileInputRef = useRef(null);

  const [detectionSettings, setDetectionSettings] = useState({
    phoneNumber: true,
    icNumber: true,
    personCompanyName: true,
    email: true,
    addressGeographic: true,
    dateTime: true,
    ethnicityRaceNationality: true,
    creditCard: true,
  });

  const handleCheckboxChange = (e) => {
    const { name, checked } = e.target;
    setDetectionSettings(prevSettings => ({
      ...prevSettings,
      [name]: checked,
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogo(reader.result);
      };
      reader.readAsDataURL(file);
    } else {
        setLogo(null);
    }
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!partnerName.trim()) {
      alert('Partner name is required!');
      return;
    }

    onCreatePartner({
      name: partnerName,
      logo: logo || '/icons/default_partner.svg',
      dataEncryptionKey,
      filePassword,
      detectionSettings,
    });
  };

  return (
    <div className="modal-overlay">
      <div className="add-partner-modal-content">
        <div className="modal-header">
          <h2>Create partner profile</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          {/* Profile Upload Section */}
          <div className="profile-section">
            <div className="profile-logo-wrapper">
                <div className="profile-circle">
                    {logo ? (
                        <img src={logo} alt="Partner Logo Preview" />
                    ) : (
                        //Parter's icon placeholder
                        <img src="/icons/default_partner.svg" alt="" />
                    )}
                </div>
                <button type="button" className="change-logo-button" onClick={handleUploadButtonClick}>
                    {logo ? 'Change Icon' : 'Upload Icon'}
                </button>
                <input
                    type="file"
                    accept="image/*"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                />
            </div>
            <div className="form-group partner-name-group">
                <label htmlFor="partnerName">Partner Name</label>
                <input
                    type="text"
                    id="partnerName"
                    placeholder="e.g., Google, Amazon"
                    value={partnerName}
                    onChange={(e) => setPartnerName(e.target.value)}
                    className="input-field"
                    required
                />
            </div>
          </div>

          {/* Detection Settings */}
          <h3 className="section-title">Detection Settings</h3>
          <div className="detection-grid">
            {Object.keys(detectionSettings).map((key) => (
              <label key={key} className="checkbox-container">
                {key.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())} {/* Format labels nicely */}
                <input
                  type="checkbox"
                  name={key}
                  checked={detectionSettings[key]}
                  onChange={handleCheckboxChange}
                />
                <span className="checkmark"></span>
              </label>
            ))}
          </div>

          {/* Secret Info */}
          <h3 className="section-title">Secret Info</h3>
          <div className="form-group">
            <label htmlFor="dataEncryptionKey">Data Encryption Key</label>
            <input
              type="password"
              id="dataEncryptionKey"
              placeholder="Enter encryption key"
              value={dataEncryptionKey}
              onChange={(e) => setDataEncryptionKey(e.target.value)}
              className="input-field"
            />
          </div>
          <div className="form-group">
            <label htmlFor="filePassword">File password</label>
            <input
              type="password"
              id="filePassword"
              placeholder="Enter password"
              value={filePassword}
              onChange={(e) => setFilePassword(e.target.value)}
              className="input-field"
            />
          </div>

          <div className="modal-footer">
            <button type="submit" className="create-button">Create Partner</button> {/* Changed button text */}
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPartner;