import React, { useState, useRef } from 'react';
import './AddPartner.css';

const detectionSettingMap = {
  person: 'PERSON',
  icNumber: 'IC_NUMBER',
  passport: 'US_PASSPORT',
  email: 'EMAIL_ADDRESS',
  address: 'LOCATION',
  bankNumber: 'US_BANK_NUMBER',
  phoneNumber: 'PHONE_NUMBER',
  creditCard: 'CREDIT_CARD',
};

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

function AddPartner({ onClose, onCreatePartner }) {
  const [partnerName, setPartnerName] = useState('');
  const [dataEncryptionKey, setDataEncryptionKey] = useState('');
  const [filePassword, setFilePassword] = useState('');
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreviewUrl, setLogoPreviewUrl] = useState(null);
  const fileInputRef = useRef(null);

  const [detectionSettings, setDetectionSettings] = useState({
    person: true,
    icNumber: true,
    passport: true,
    email: true,
    address: true,
    bankNumber: true,
    phoneNumber: true,
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
      setLogoFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    } else {
        setLogoFile(null);
        setLogoPreviewUrl(null);
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

    const backendDetectionSettings = Object.keys(detectionSettings)
        .filter(key => detectionSettings[key])
        .map(key => detectionSettingMap[key]);

    const formData = new FormData();
    formData.append('partner', partnerName);
    if (logoFile) {
      formData.append('icon', logoFile);
    }
    formData.append('key', dataEncryptionKey);
    formData.append('password', filePassword);
    formData.append('detection', JSON.stringify(backendDetectionSettings));

    onCreatePartner(formData);

    setPartnerName('');
    setDataEncryptionKey('');
    setFilePassword('');
    setLogoFile(null);
    setLogoPreviewUrl(null);
    setDetectionSettings({
      person: true, icNumber: true, passport: true, email: true,
      address: true, bankNumber: true, phoneNumber: true, creditCard: true,
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
                    {logoPreviewUrl ? (
                        <img src={logoPreviewUrl} alt="Partner Logo Preview" />
                    ) : (
                        <img src="/icons/camera-icon.png" alt="Default Partner Icon" />
                    )}
                </div>
                <button type="button" className="change-logo-button" onClick={handleUploadButtonClick}>
                    {logoPreviewUrl ? 'Change Icon' : 'Upload Icon'}
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
                    onChange={(e) => {
                      console.log("Typing:", e.target.value);
                      setPartnerName(e.target.value);
                    }}
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
                {/* Use reverse map for display, fallback to formatted key */}
                {reverseDetectionSettingMap[detectionSettingMap[key]] || key.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
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
            <button type="submit" className="create-button">Create Partner</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddPartner;