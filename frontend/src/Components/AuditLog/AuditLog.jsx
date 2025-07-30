import React from 'react';
import './AuditLog.css';

function AuditLog({ auditData, partnerData, onClose }) {
  if (!auditData) {
    return null;
  }

  // Determine if fileType is Text File or Tabular File
  const isTextFile = auditData.type === 'Text File';
  const isTabularFile = auditData.type === 'Tabular File';
  const summary = auditData.log || [];


  return (
    <div className="modal-overlay">
      <div className="audit-log-modal-content">
        <div className="modal-header">
          <h2>Audit Log</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>
        <div className="audit-log-modal-body">
          <div className="audit-detail-group">
            <span className="detail-label">Filename</span>
            <span className="detail-value">: {auditData.filename}</span>
          </div>
          <div className="audit-detail-group">
            <span className="detail-label">Intended for</span>
            <span className="detail-value">: {partnerData.name}</span>
          </div>
          <div className="audit-detail-group">
            <span className="detail-label">Anonymized Method</span>
            <span className="detail-value">: Encryption</span>
          </div>
          <div className="audit-detail-group">
            <span className="detail-label">Type</span>
            <span className="detail-value">: {auditData.type}</span>
          </div>

          <h3 className="report-header">Text File Report:</h3>
          <div className="entities-detected-table-container">
            <table>
              <thead>
                <tr>
                  <th>Entities Detected</th>
                  {isTextFile && <th>Total</th>}
                  {isTabularFile && <th>Column Name</th>}
                </tr>
              </thead>
              <tbody>
                {summary && Array.isArray(summary) && summary.length > 0 ? (
                  summary.map((entity, index) => (
                    <tr key={index}>
                      <td>{entity.detect}</td>
                      {isTextFile && <td>{entity.total}</td>}
                      {isTabularFile && <td>{entity.column}</td>}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="2" className="no-entities-message">No non-ignored entities found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AuditLog;