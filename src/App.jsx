import React, { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Sidenav from './Components/Sidenav/Sidenav';
import PartnerDetails from './Components/Partner/PartnerDetails';
import AddPartner from './Components/Partner/AddPartner';
import ViewPartner from './Components/Partner/ViewPartner';
import LoadingOverlay from './Components/Common/LoadingOverlay';
import Review from './Components/Review/Review';
import AuditLog from './Components/AuditLog/AuditLog';
import './App.css';

const API_BASE_URL = 'http://localhost:5000';
const DEFAULT_FRONTEND_ICON_PATH = '/icons/question-mark.png';

function App() {
  //Partners state - will be fetched from backend
  const [partners, setPartners] = useState([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState(null);
  const [isAddPartnerModalOpen, setIsAddPartnerModalOpen] = useState(false);
  const [isViewPartnerModalOpen, setIsViewPartnerModalOpen] = useState(false);

  //Loading Screen Indicator
  const [isAnalyzing, setIsAnalyzing] = useState(false); // For file upload/anonymization process
  const [loadingPartners, setLoadingPartners] = useState(true); // For initial partners fetch
  const [error, setError] = useState(null); // For general fetch errors

  //Human Review
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewData, setReviewData] = useState(null); // Detected PII for review
  const [currentFileBeingReviewed, setCurrentFileBeingReviewed] = useState(null); // The file object currently in review

  //Audit
  const [isAuditLogModalOpen, setIsAuditLogModalOpen] = useState(false);
  const [auditLogData, setAuditLogData] = useState(null);

  // Helper function to determine file type based on extension (still useful for sending to backend)
  const getFileTypeFromExtension = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (['txt'].includes(ext)) {
      return 'Text file';
    } else if (['jpg', 'jpeg', 'png', 'bmp'].includes(ext)) {
      return 'Image file';
    } else if (['csv', 'xlsx', 'xlsm', 'xls'].includes(ext)) {
      return 'Tabular file';
    } else if (['doc', 'docx', 'pdf'].includes(ext)) {
      return 'Document file';
    }
    return 'Unknown file';
  };

  // Function to fetch partners from the backend
  const fetchPartners = useCallback(async () => {
    setLoadingPartners(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/partners`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const partnersWithFiles = data.map(partner => ({
        ...partner,
        files: partner.files ? partner.files.map(file => ({
          ...file,
          // Ensure downloadLink is constructed based on file.id
          downloadLink: file.id ? `${API_BASE_URL}/download/${file.id}` : null 
        })) : []
      }));

      setPartners(partnersWithFiles);
      if (!selectedPartnerId && partnersWithFiles.length > 0) {
        setSelectedPartnerId(partnersWithFiles[0].id);
      } else if (selectedPartnerId && !partnersWithFiles.some(p => p.id === selectedPartnerId)) {
        // If selected partner was deleted, select first available or none
        setSelectedPartnerId(partnersWithFiles.length > 0 ? partnersWithFiles[0].id : null);
      }
    } catch (err) {
      console.error("Failed to fetch partners:", err);
      setError("Failed to load partners. Please ensure the backend is running and accessible.");
    } finally {
      setLoadingPartners(false);
    }
  }, [selectedPartnerId]);

  // Initial data fetch on component mount
  useEffect(() => {
    fetchPartners();
  }, [fetchPartners]);

  const selectedPartner = partners.find(p => p.id === selectedPartnerId);

  // Handle adding a new partner via backend API
  const handleAddPartner = async (formData) => {
    try {
      const response = await fetch(`${API_BASE_URL}/create-partner`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      const addedPartner = await response.json();
      await fetchPartners();
      setIsAddPartnerModalOpen(false);
      setSelectedPartnerId(addedPartner.id);
      //alert(`Partner "${addedPartner.name}" added successfully!`);
    } catch (err) {
      console.error("Failed to add partner:", err);
      alert(`Error adding partner: ${err.message}`);
    }
  };

  // Handle file upload and initial PII analysis via backend API
  // This now correctly expects an array of files, as passed from PartnerDetails.jsx
  const handleFileUpload = async (filesToUpload) => {
    if (!selectedPartner) {
        alert("Please select a partner first.");
        return;
    }
    // Check if filesToUpload is empty or not an array with at least one element
    if (!Array.isArray(filesToUpload) || filesToUpload.length === 0) {
        alert("No file selected for upload.");
        return;
    }

    setIsAnalyzing(true);

    const file = filesToUpload[0]; // Take the first file from the array
    const fileType = getFileTypeFromExtension(file.name);

    const formData = new FormData();
    formData.append('partner', selectedPartner.name);
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const backendResponse = await response.json();
      const detectedPiiFromBackend = backendResponse.review;

      setReviewData(detectedPiiFromBackend);
      
      setCurrentFileBeingReviewed({
        id: backendResponse.file_id,
        filename: backendResponse.filename,
        type: backendResponse.type,
        state: 'Pending Review',
        // downloadLink is not needed here as it will be set upon successful anonymization
        // and re-fetching of partners.
      });
      setIsReviewModalOpen(true);

    } catch (err) {
      console.error("Failed to upload and analyze file:", err);
      alert(`Error uploading and analyzing file: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  //Handle proceeding with anonymization after human review
  const handleProceedAnonymization = async (updatedReviewItems) => {
    setIsReviewModalOpen(false);
    setIsAnalyzing(true);

    const anonymizationPayload = {
      file_id: currentFileBeingReviewed.id, // Pass the file_id directly
      review: updatedReviewItems.map(item => {
        const cleanedItem = {
          detect: item.detect,
          confidence: item.confidence / 100, // Convert back to 0.0-1.0
          ignore: item.ignore,
        };
        // Conditionally add 'word', 'start', 'end' for text files
        if (item.word !== undefined) cleanedItem.word = item.word;
        if (item.start !== undefined) cleanedItem.start = item.start;
        if (item.end !== undefined) cleanedItem.end = item.end;
        // Conditionally add 'column', 'topData' for tabular files
        if (item.column !== undefined) cleanedItem.column = item.column;
        if (item.topData !== undefined) cleanedItem.topData = item.topData;
        
        return cleanedItem;
      }),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/proceed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(anonymizationPayload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const backendResponse = await response.json(); // Get response from backend (e.g., anonymized filename)
      await fetchPartners(); // Re-fetch all partners and their files to update the table

      //alert(`${backendResponse.filename} has been anonymized!`);
      setReviewData(null);
      setCurrentFileBeingReviewed(null);

    } catch (err) {
      console.error("Failed to proceed with anonymization:", err);
      alert(`Error anonymizing file: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle toggling file anonymization state (De-anonymize/Anonymize)
  const handleToggleFileAnonymization = async (partnerId, fileId) => {
    const partnerToUpdate = partners.find(p => p.id === partnerId);
    const fileToToggle = partnerToUpdate?.files.find(f => f.id === fileId);

    if (!fileToToggle) return;

    const newState = fileToToggle.state === 'Anonymized' ? 'De-anonymized' : 'Anonymized';

    try {
      const response = await fetch(`${API_BASE_URL}/api/files/${fileId}/state`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: newState }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      await fetchPartners(); // Re-fetch partners to get updated file state and download link
      //alert(`File state updated to ${newState} for ${fileToToggle.filename}.`);
    } catch (err) {
      console.error("Failed to toggle file anonymization:", err);
      alert(`Error toggling anonymization: ${err.message}`);
    }
  };

  //Handle cancelling the review process
  const handleCancelReview = () => {
    setIsReviewModalOpen(false);
    setReviewData(null);
    setCurrentFileBeingReviewed(null);
    //alert('Review cancelled. File not anonymized.');
  };

  // Handle viewing the audit log for a file
  const handleViewAuditLog = async (file) => {
    if (!file.id) {
        alert('Cannot view audit log: File ID is missing.');
        return;
    }
    try {
        const response = await fetch(`${API_BASE_URL}/api/files/${file.id}/auditlog`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const auditData = await response.json();
        setAuditLogData(auditData); // Set the auditData directly
        setIsAuditLogModalOpen(true); // Open the audit log modal
    } catch (err) {
        console.error("Failed to fetch audit log:", err);
        alert(`Audit log not available for this file: ${err.message}`);
    }
  };

  // Handle closing the audit log modal
  const handleCloseAuditLog = () => {
    setIsAuditLogModalOpen(false);
    setAuditLogData(null);
  }

  // --- Handle opening ViewPartner modal ---
  const handleViewPartnerDetails = () => {
    setIsViewPartnerModalOpen(true);
  };

  // --- Initial Loading State for Partners ---
  if (loadingPartners) {
    return <LoadingOverlay message="Loading partners..." />;
  }

  // --- Error State for Partners ---
  if (error) {
    return (
      <div className="app-container error-container">
        <p className="error-message">{error}</p>
        <button onClick={fetchPartners} className="retry-button">Retry</button>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidenav */}
      <Sidenav
        partners={partners}
        selectedPartnerId={selectedPartnerId}
        onSelectPartner={setSelectedPartnerId}
        onAddPartnerClick={() => setIsAddPartnerModalOpen(true)}
        apiBaseUrl={API_BASE_URL}
        defaultIconPath={DEFAULT_FRONTEND_ICON_PATH}
      />

      {/* Main Content Area */}
      <div className="main-content">
        {selectedPartner ? (
          <PartnerDetails
            partner={selectedPartner}
            onFileUpload={handleFileUpload}
            onToggleFileAnonymization={handleToggleFileAnonymization}
            onViewAuditLog={handleViewAuditLog}
            onViewPartnerDetails={handleViewPartnerDetails}
            apiBaseUrl={API_BASE_URL}
            defaultIconPath={DEFAULT_FRONTEND_ICON_PATH}
          />
        ) : (
          <div className="no-partner-selected">
            {partners.length === 0 ? "No partners found. Add a new partner to begin!" : "Select a partner to view details."}
          </div>
        )}
      </div>

      {/* Add Partner Modal */}
      {isAddPartnerModalOpen && (
        <AddPartner
          onClose={() => setIsAddPartnerModalOpen(false)}
          onCreatePartner={handleAddPartner}
        />
      )}

      {/* View/Edit Partner Modal */}
      {isViewPartnerModalOpen && selectedPartner && (
        <ViewPartner
          partner={selectedPartner}
          onClose={() => setIsViewPartnerModalOpen(false)}
          apiBaseUrl={API_BASE_URL}
          defaultIconPath={DEFAULT_FRONTEND_ICON_PATH}
        />
      )}

      {/* Review Before Anonymization Modal */}
      {isReviewModalOpen && currentFileBeingReviewed && (
        <Review
          fileName={currentFileBeingReviewed.filename}
          fileType={currentFileBeingReviewed.type}
          detectedPii={reviewData}
          onProceed={handleProceedAnonymization}
          onCancel={handleCancelReview}
        />
      )}

      {/* Audit Log Modal */}
      {isAuditLogModalOpen && auditLogData && (
        <AuditLog
          auditData={auditLogData}
          onClose={handleCloseAuditLog}
        />
      )}

      {/* Analyzing Overlay (for file upload/anonymization) */}
      {isAnalyzing && <LoadingOverlay message="Processing..." />}
    </div>
  );
}

export default App;