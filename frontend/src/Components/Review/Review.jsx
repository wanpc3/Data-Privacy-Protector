import React, { useState, useEffect } from 'react';
import './Review.css';

function Review({ fileName, fileType, detectedPii, onProceed, onCancel }) {
  const [reviewItems, setReviewItems] = useState([]);

  //console.log("====== Check component=========")
  //console.log("fileName:", fileName)
  //console.log("fileType:", fileType)
  //console.log("detectedPii:", detectedPii)
  //console.log("detectedPii type:", typeof detectedPii)
  //console.log("detectedPii is array:", Array.isArray(detectedPii))
  //console.log("detectedPii length:", detectedPii ? detectedPii.length : "N/A")
  //console.log("reviewItems:", reviewItems)
  //console.log("reviewItems length:", reviewItems.length)

  useEffect(() => {

    //console.log("========================Use effect triggers====================================")
    //console.log("New detectedPii received:", detectedPii);
    if (detectedPii && detectedPii.length > 0) {
      setReviewItems(
        detectedPii.map((item, index) => {
          return {
            id: index,
            ...item,
          };
        })
      );
    } else {
      setReviewItems([]);
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
    //console.log("=============  IMPORTANT: See here   ====================")
    //console.log("renderTableContent called with fileType:", fileType)
    //console.log("reviewItems in renderTableContent:", reviewItems)
    
    if (fileType === "Text File") {
      //console.log("========Rendering text file table======")
      return (
        <>
          <thead>
            <tr>
              <th>Word</th>
              <th>Entity</th> {/* Changed from PII_Confidence_Title to Entity for clarity */}
              <th>PII_Confidence</th>
              <th>Ignore</th>
            </tr>
          </thead>
          <tbody>
            {reviewItems.map(item => (
              <tr key={item.id}>
                <td>{item.word}</td>
                <td>{item.detect}</td>
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
    } else if (fileType === "Tabular File") {
      //console.log("=============Rendering tabular file table===============")
      return (
        <>
          <thead>
            <tr>
              <th>Column</th>
              <th>Entity</th> {/* Changed from PII_Confidence_Title to Entity for clarity */}
              <th>PII_Confidence(Avg)</th>
              <th>Ignore</th>
            </tr>
          </thead>
          <tbody>
            {reviewItems.map(item => (
              <tr key={item.id}>
                <td>{item.column}
                  <br /><span>&nbsp;&nbsp;&nbsp;{item.words[0]}</span>
                  <br /><span>&nbsp;&nbsp;&nbsp;{item.words[1]}</span>
                  <br /><span>&nbsp;&nbsp;&nbsp;{item.words[2]}</span>
                </td>
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
    }
    //console.log("==========No matching file type, returning null=========")
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
            {(() => {
              //console.log("Conditional rendering check:")
              //console.log("reviewItems.length:", reviewItems.length)
              //console.log("Should show table:", reviewItems.length > 0)
              
              if (reviewItems.length > 0) {
                //console.log("***********************Rendering table***********************")
                return (
                  <table>
                    {renderTableContent()}
                  </table>
                );
              } else {
                //console.log("***************Rendering no PII message******************")
                return (
                  <p className="no-pii-message">
                    {detectedPii === null || detectedPii === undefined 
                      ? "No PII detection data available for this file." 
                      : detectedPii.length === 0 
                        ? "No PII detected in this file." 
                        : "No PII detected for this file, or data not available for review."}
                  </p>
                );
              }
            })()}
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