import { FaEye, FaDownload, FaUpload, FaUser, FaTable, FaFileAlt, FaImage, FaFolder, FaQuestion } from 'react-icons/fa';
import { useRef } from 'react';
import './PartnerDetails.css';

const API_BASE_URL = 'http://localhost:5000'; // Ensure this is defined or passed as a prop

function PartnerDetails({ partner, onFileUpload, onToggleFileAnonymization, onViewAuditLog, onViewPartnerDetails }) {
  const fileInputRef = useRef(null);

  const handleUploadButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = (event) => {
    const uploadedFiles = Array.from(event.target.files);
    if (uploadedFiles.length > 0) {
      onFileUpload(uploadedFiles);
    }
    event.target.value = null;
  };

  const handleSeeProfile = () => {
    onViewPartnerDetails();
  };

  const getFileTypeIcon = (fileType) => {
    if (fileType.includes('Tabular')) return <FaTable />;
    if (fileType.includes('Text')) return <FaFileAlt />;
    if (fileType.includes('Image')) return <FaImage />;
    if (fileType.includes('Document')) return <FaFolder />;
    return <FaQuestion />;
  };

  return (
    <div className="partner-details-container">
      <div className="partner-header-main">
        <div className="partner-info-main">
          {partner.logo && partner.logo !== '/icons/question-mark.png' ? (
              <img
                  src={`${API_BASE_URL}${partner.logo}`}
                  alt={`${partner.name} logo`}
                  className="partner-logo-main"
              />
          ) : (
              <img
                  src="/icons/question-mark.png"
                  alt="Default Partner Logo"
                  className="partner-logo-main"
              />
          )}
          <h1>{partner.name}</h1>
        </div>
        <div className="header-actions">
          <button className="action-button" onClick={handleUploadButtonClick}>
            <FaUpload /> Upload file
          </button>
          <button className="action-button" onClick={handleSeeProfile}>
            <FaUser /> See Profile
          </button>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
        </div>
      </div>

      <div className="file-list-section">
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Type</th>
                <th>State</th>
                <th>Log</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {Array.isArray(partner.files) && partner.files.length > 0 ? (
                partner.files.map(file => (
                  <tr key={file.id}>
                    <td>
                      {getFileTypeIcon(file.type)} {file.filename}
                    </td>
                    <td>{file.type}</td>
                    <td>
                      <label className="switch">
                        <input
                          type="checkbox"
                          checked={file.state === 'Anonymized'}
                          onChange={() => onToggleFileAnonymization(partner.id, file.id)}
                        />
                        <span className="slider round"></span>
                      </label>
                      <span className={`file-state ${file.state.toLowerCase().replace('-', '')}`}>
                        {file.state}
                      </span>
                    </td>
                    <td>
                      <button className="log-icon-button" onClick={() => onViewAuditLog(file)}>
                        <FaEye />
                      </button>
                    </td>
                    <td>
                      <a href={file.downloadLink} download>
                        <FaDownload />
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="6" className="no-files-message">No files uploaded for this partner yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default PartnerDetails;