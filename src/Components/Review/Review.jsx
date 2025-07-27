import React, { useState, useEffect } from 'react';
import './Review.css';

function Review({ fileName, fileType, detectedPii, onProceed, onCancel }) {
  const [reviewItems, setReviewItems] = useState([]);

  useEffect(() => {
    if (detectedPii) {
      setReviewItems(detectedPii.map(item => {
        const confidence = item.confidence || item.avgConfidence;
        return {
          ...item,
          ignore: confidence < 70 ? true : item.ignore // Apply auto-ignore based on threshold
        };
      }));
    }
  }, [detectedPii]);

  const handleIgnoreChange = (id) => {
    setReviewItems(prevItems =>
      prevItems.map(item =>
        item.id === id ? { ...item, ignore: !item.ignore } : item
      )
    );
  };

  const renderTableContent = () => {
    if (fileType === 'Text file') {
      return (
        <>
          <thead>
            <tr>
              <th>Word</th>
              <th>Entity</th>
              <th>PII_Confidence</th>
              <th>Ignore</th>
            </tr>
          </thead>
          <tbody>
            {reviewItems.map(item => (
              <tr key={item.id}>
                <td>{item.word}</td>
                <td>{item.entity}</td>
                <td className={item.confidence < 70 ? 'confidence-low' : 'confidence-high'}>
                  {item.confidence}%
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={item.ignore}
                    onChange={() => handleIgnoreChange(item.id)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </>
      );
    } else if (fileType === 'Tabular file') {
      return (
        <>
          <thead>
            <tr>
              <th>Column</th>
              <th>Entity</th>
              <th>Top data (First 2 rows)</th>
              <th>PII_Confidence (Avg)</th>
              <th>Ignore</th>
            </tr>
          </thead>
          <tbody>
            {reviewItems.map(item => (
              <tr key={item.id}>
                <td>{item.column}</td>
                <td>{item.entity}</td>
                <td>
                  {Array.isArray(item.topData) ? item.topData.join(', ') : item.topData}
                </td>
                <td className={item.avgConfidence < 70 ? 'confidence-low' : 'confidence-high'}>
                  {item.avgConfidence}%
                </td>
                <td>
                  <input
                    type="checkbox"
                    checked={item.ignore}
                    onChange={() => handleIgnoreChange(item.id)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </>
      );
    }
    return null; // Or handle other file types
  };

  return (
    <div className="modal-overlay">
      <div className="review-modal-content">
        <div className="modal-header">
          <h2>Review Before Anonymization</h2>
          <button className="close-button" onClick={onCancel}>&times;</button>
        </div>
        <div className="review-modal-body">
          <p>File: <strong>{fileName}</strong> (Type: {fileType})</p>
          <div className="review-table-container">
            {reviewItems.length > 0 ? (
              <table>
                {renderTableContent()}
              </table>
            ) : (
              <p className="no-pii-message">No PII detected for this file, or data not available for review.</p>
            )}
          </div>
          <p className="note-text">Note: Those below 70% automatically marked as ignore (NONE_PII).</p>
        </div>
        <div className="modal-footer">
          <button className="proceed-button" onClick={() => onProceed(reviewItems)}>Proceed</button>
        </div>
      </div>
    </div>
  );
}

export default Review;