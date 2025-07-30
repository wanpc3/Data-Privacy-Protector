import { FaEye, FaDownload, FaUpload, FaUser, FaTable, FaFileAlt, FaImage, FaFolder, FaQuestion } from 'react-icons/fa';
import { useRef } from 'react';
import './PartnerDetails.css';

const API_BASE_URL = 'http://localhost:5000'; 

function PartnerDetails({ partner, onFileUpload, onToggleFileAnonymization, onViewAuditLog, onViewPartnerDetails, apiBaseUrl, defaultIconPath }) {
  const fileInputRef = useRef(null);

  
  const handleDownloadButtonClick = async (partnerName) => {
  try {
    const formData = new FormData();
    formData.append("partner", partnerName);

    const response = await fetch(`${API_BASE_URL}/download`, {
      method: 'POST',
      body: formData,
    });

         if (!response.ok) {
        throw new Error(`Server error ${response.status}`);
      }

      // pull out the zip as a Blob
      const blob = await response.blob();

      // turn it into an object URL and click a hidden <a> to download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // set this name however you like
      link.download = `${partnerName}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Download failed', err);
    }
};

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
          {partner.logo && partner.logo !== defaultIconPath ? ( 
              <img 
                  src={`${apiBaseUrl}${partner.logo}`} 
                  alt={`${partner.name} logo`} 
                  className="partner-logo-main"
              /> 
          ) : ( 
              <img 
                  src={defaultIconPath} 
                  alt="Default Partner Logo" 
                  className="partner-logo-main" 
              /> 
          )}
          <h1>{partner.name}</h1>
        </div>
        <div className="header-actions">
          <button className="action-button" onClick={() => handleDownloadButtonClick(partner.name)}>
            <FaDownload /> Download All
          </button>
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
                          checked={file.anonymized}
                          onChange={() => onToggleFileAnonymization(
                            partner.name,
                            file.filename,
                            file.anonymized
                          )}
                        />
                        <span className="slider round"></span>
                      </label>
                      <span className={`file-state ${(file.state || '').toLowerCase().replace('-', '')}`}>
                        {file.state}
                      </span>
                    </td>
                    <td>
                      <button className="log-icon-button" onClick={() => onViewAuditLog(file)}>
                        <FaEye />
                      </button>
                    </td>
                    <td>
                      <a href={`${API_BASE_URL}/${file.download}`} download>
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