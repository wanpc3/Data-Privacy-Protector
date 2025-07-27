import { FaEye, FaDownload, FaUpload, FaUser, FaTable, FaFileAlt, FaImage, FaFolder, FaQuestion } from 'react-icons/fa';
import { useRef } from 'react';
import './PartnerDetails.css';

function PartnerDetails({ partner, onFileUpload, onToggleFileAnonymization, onViewAuditLog}) {
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

  //Download All
  const handleDownloadAll = () => {
    alert(`Simulating "Download All" for ${partner.name}`);
  };

  //See Profile
  const handleSeeProfile = () => {
    alert(`Simulating "See Profile" for ${partner.name}`);
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
          <img src={partner.logo || '/icons/default_partner.svg'} alt={partner.name} className="partner-logo-main" />
          <h1>{partner.name}</h1>
        </div>
        <div className="header-actions">
          <button className="action-button" onClick={handleDownloadAll}>
            <FaDownload /> Download all
          </button>
          <button className="action-button" onClick={handleUploadButtonClick}>
            <FaUpload /> Upload file
          </button>
          <button className="action-button" onClick={handleSeeProfile}>
            <FaUser /> See Profile
          </button>
          {/* Hidden file input */}
          <input
            type="file"
            multiple // Allow multiple file selection
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
                      {/* Placeholder for the Log/View icon */}
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
                  <td colSpan="6" className="no-files-message">No files uploaded for this partner yet.</td> {/* Adjusted colspan */}
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