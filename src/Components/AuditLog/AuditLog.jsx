import React from 'react';
import './AuditLog.css';

function AuditLog({ auditData, onClose }) {
  if (!auditData) {
    return null;
  }

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
            <span className="detail-value">: {auditData.intendedFor}</span>
          </div>
          <div className="audit-detail-group">
            <span className="detail-label">Anonymized Method</span>
            <span className="detail-value">: {auditData.anonymizedMethod}</span>
          </div>
          <div className="audit-detail-group">
            <span className="detail-label">Type</span>
            <span className="detail-value">: {auditData.fileType}</span>
          </div>

          <h3 className="report-header">Text File Report:</h3>
          <div className="entities-detected-table-container">
            <table>
              <thead>
                <tr>
                  <th>Entities Detected</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {auditData.detectedEntitiesSummary && auditData.detectedEntitiesSummary.length > 0 ? (
                  auditData.detectedEntitiesSummary.map((entity, index) => (
                    <tr key={index}>
                      <td>{entity.entity}</td>
                      <td>{entity.count}</td>
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