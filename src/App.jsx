import React, { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Sidenav from './Components/Sidenav/Sidenav';
import PartnerDetails from './Components/Partner/PartnerDetails';
import AddPartner from './Components/Partner/AddPartner';
import LoadingOverlay from './Components/Common/LoadingOverlay';
import Review from './Components/Review/Review';
import AuditLog from './Components/AuditLog/AuditLog';
import './App.css';

//Dummy data (yeah, there's a lot. Just for reference before we put the real one)
const initialPartners = [
  {
    id: 'starbucks',
    name: 'Starbucks',
    logo: '/icons/starbucks-logo.png',
    files: [
      { id: 'sb-file1', filename: 'Customers_Orders.xlsx', type: 'Tabular file', state: 'Anonymized', downloadLink: '#',
        auditLog: {
          intendedFor: 'Starbucks',
          anonymizedMethod: 'Encryption',
          detectedEntitiesSummary: [
            { entity: 'IC_NUMBER', count: 50 },
            { entity: 'PERSON', count: 120 },
            { entity: 'CREDIT_CARD', count: 15 }
          ]
        }
      },
      { id: 'sb-file2', filename: 'Marketing_Campaign.txt', type: 'Text file', state: 'De-anonymized', downloadLink: '#' },
    ],
    dataEncryptionKey: 'starbucksKey123',
    filePassword: 'sbPass',
    detectionSettings: {
      phoneNumber: true, icNumber: true, personCompanyName: true, email: true,
      addressGeographic: true, dateTime: false, ethnicityRaceNationality: true, creditCard: false,
    },
  },
  {
    id: 'bmw',
    name: 'BMW',
    logo: '/icons/bmw-logo.png',
    files: [
      {
        id: 'bmw-file1', filename: 'Finanial_Data.xlsx', type: 'Tabular file', state: 'Anonymized', downloadLink: '#',
        auditLog: {
          intendedFor: 'BMW',
          anonymizedMethod: 'Encryption',
          detectedEntitiesSummary: [
            { entity: 'PERSON', count: 10 },
            { entity: 'EMAIL', count: 5 },
          ]
        }
      },
      {
        id: 'bmw-file2', filename: 'Client_Testimonial.txt', type: 'Text file', state: 'De-anonymized', downloadLink: '#',
        auditLog: {
          intendedFor: 'BMW',
          anonymizedMethod: 'Encryption',
          detectedEntitiesSummary: [
            { entity: 'PHONE_NUMBER', count: 2 },
            { entity: 'PERSON', count: 3 },
          ]
        }
      },
      { id: 'bmw-file3', filename: 'Purchase_record.csv', type: 'Tabular file', state: 'Anonymized', downloadLink: '#' },
      { id: 'bmw-file4', filename: 'IC_photo.jpg', type: 'Image file', state: 'Anonymized', downloadLink: '#' },
    ],
    dataEncryptionKey: 'bmwKey456',
    filePassword: 'bmwPass',
    detectionSettings: {
      phoneNumber: true, icNumber: true, personCompanyName: true, email: true,
      addressGeographic: true, dateTime: true, ethnicityRaceNationality: true, creditCard: true,
    },
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    logo: '/icons/salesforce-logo.png',
    files: [
        { id: 'sf-file1', filename: 'CRM_Data_Q1.xlsx', type: 'Tabular file', state: 'Anonymized', downloadLink: '#' },
    ],
    dataEncryptionKey: 'sfKey789',
    filePassword: 'sfPass',
    detectionSettings: {
      phoneNumber: true, icNumber: true, personCompanyName: true, email: true,
      addressGeographic: true, dateTime: true, ethnicityRaceNationality: true, creditCard: true,
    },
  },
];

function App() {

  //Partners
  const [partners, setPartners] = useState([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState(null);
  const [isAddPartnerModalOpen, setIsAddPartnerModalOpen] = useState(false);

  //That Loading Screen Indicator
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  //Human Review
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewData, setReviewData] = useState(null);
  const [currentFileBeingReviewed, setCurrentFileBeingReviewed] = useState(null);

  //Audit
  const [isAuditLogModalOpen, setIsAuditLogModalOpen] = useState(false);
  const [auditLogData, setAuditLogData] = useState(null);

  //File Handler
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

  useEffect(() => {
    setPartners(initialPartners);
    if (initialPartners.length > 0) {
      setSelectedPartnerId(initialPartners[0].id);
    }
  }, []);

  const selectedPartner = partners.find(p => p.id === selectedPartnerId);

  const handleAddPartner = (newPartnerData) => {
    const newId = uuidv4();
    const newPartner = {
      id: newId,
      name: newPartnerData.name,
      logo: newPartnerData.logo || '/icons/default_partner.svg',
      files: [],
      detectionSettings: newPartnerData.detectionSettings,
      dataEncryptionKey: newPartnerData.dataEncryptionKey,
      filePassword: newPartnerData.filePassword,
    };
    setPartners([...partners, newPartner]);
    setIsAddPartnerModalOpen(false);
    setSelectedPartnerId(newId);
  };

  const handleFileUpload = (filesToUpload) => {
    if (!selectedPartner) return;

    setIsAnalyzing(true);

    setTimeout(() => {
      const newFilesMetadata = filesToUpload.map(file => {
        const fileId = uuidv4();
        const fileType = getFileTypeFromExtension(file.name);

        let detectedPii = [];
        if (fileType === 'Text file') {
          detectedPii = [
            { id: uuidv4(), word: 'Muhammad Zain', entity: 'PERSON', confidence: 95, ignore: false },
            { id: uuidv4(), word: '+6011-2578107', entity: 'PHONE_NUMBER', confidence: 88, ignore: false },
            { id: uuidv4(), word: 'Firmu Metro Holdings', entity: 'PERSON', confidence: 60, ignore: false }, // Will be auto-ignored
            { id: uuidv4(), word: '556-5555-5555', entity: 'CREDIT_CARD', confidence: 10, ignore: false }, // Will be auto-ignored
          ];
        } else if (fileType === 'Tabular file') {
          detectedPii = [
            { id: uuidv4(), column: 'Name', entity: 'PERSON', topData: ['Wong Chen', 'Hafiz Zawawi'], avgConfidence: 90, ignore: false },
            { id: uuidv4(), column: 'Identification Number', entity: 'IC_NUMBER', topData: ['820927-07-7473', '521210-08-9327'], avgConfidence: 85, ignore: false },
            { id: uuidv4(), column: 'Credit Card Number', entity: 'CREDIT_CARD', topData: ['446031846464896', '2956223794907692'], avgConfidence: 50, ignore: false }, // Will be auto-ignored
          ];
        }
        detectedPii = detectedPii.map(item => {
          const confidence = item.confidence || item.avgConfidence;
          if (confidence < 70) { //
            return { ...item, ignore: true };
          }
          return item;
        });

        return {
          id: fileId,
          filename: file.name,
          type: fileType,
          state: 'Pending Review',
          downloadLink: '#',
          detectedPii: detectedPii,
          auditLog: null,
        };
      });

      if (newFilesMetadata.length > 0) {
        setReviewData(newFilesMetadata[0].detectedPii);
        setCurrentFileBeingReviewed(newFilesMetadata[0]);
        setIsReviewModalOpen(true);
      }

      setIsAnalyzing(false);
    }, 2000);
  };

  const handleProceedAnonymization = (updatedDetectedPii) => {
    setIsReviewModalOpen(false);
    setIsAnalyzing(true);

    const detectedEntitiesSummary = {};
    updatedDetectedPii.forEach(item => {
        if (!item.ignore) {
            const entityType = item.entity;
            detectedEntitiesSummary[entityType] = (detectedEntitiesSummary[entityType] || 0) + 1;
        }
    });

    const auditLogInfo = {
        intendedFor: selectedPartner.name,
        anonymizedMethod: 'Encryption',
        detectedEntitiesSummary: Object.keys(detectedEntitiesSummary).map(entity => ({
            entity: entity,
            count: detectedEntitiesSummary[entity]
        })),
    };

    setTimeout(() => {
      setPartners(prevPartners =>
        prevPartners.map(partner => {
          if (partner.id === selectedPartnerId) {
            const updatedFiles = partner.files.map(file => {
              if (file.id === currentFileBeingReviewed.id) {
                return {
                  ...file,
                  state: 'Anonymized',
                  auditLog: auditLogInfo,
                };
              }
              return file;
            });
            const fileAlreadyExists = updatedFiles.some(f => f.id === currentFileBeingReviewed.id);
            if (!fileAlreadyExists) {
                updatedFiles.push({ ...currentFileBeingReviewed, state: 'Anonymized' });
            }

            return { ...partner, files: updatedFiles };
          }
          return partner;
        })
      );
      setIsAnalyzing(false);
      alert(`${currentFileBeingReviewed.filename} has been anonymized!`);
      setReviewData(null);
      setCurrentFileBeingReviewed(null);
    }, 1500);
  };

  //Anonymization
  const handleToggleFileAnonymization = (partnerId, fileId) => {
    setPartners(prevPartners =>
      prevPartners.map(partner => {
        if (partner.id === partnerId) {
          const updatedFiles = partner.files.map(file => {
            if (file.id === fileId) {
              return {
                ...file,
                state: file.state === 'Anonymized' ? 'De-anonymized' : 'Anonymized'
              };
            }
            return file;
          });
          return { ...partner, files: updatedFiles };
        }
        return partner;
      })
    );
  };

  //Cancel Anonymize
  const handleCancelReview = () => {
    setIsReviewModalOpen(false);
    setReviewData(null);
    setCurrentFileBeingReviewed(null);
    alert('Review cancelled. File not anonymized.');
  };

  //View Audit Log
  const handleViewAuditLog = (file) => {
    if (file.auditLog) {
      setAuditLogData({
        filename: file.filename,
        fileType: file.type,
        intendedFor: file.auditLog.intendedFor,
        anonymizedMethod: file.auditLog.anonymizedMethod,
        detectedEntitiesSummary: file.auditLog.detectedEntitiesSummary,
      });
      setIsAuditLogModalOpen(true);
    } else {
      alert('Audit log not available for this file. It might not have been anonymized yet.');
    }
  };

  //Close Audit Log
  const handleCloseAuditLog = () => {
    setIsAuditLogModalOpen(false);
    setAuditLogData(null);
  }

  return (
    <div className="app-container">
      {/* Sidenav */}
      <Sidenav
        partners={partners}
        selectedPartnerId={selectedPartnerId}
        onSelectPartner={setSelectedPartnerId}
        onAddPartnerClick={() => setIsAddPartnerModalOpen(true)}
      />

      {/* Main Content Area */}
      <div className="main-content">
        {selectedPartner ? (
          <PartnerDetails
            partner={selectedPartner}
            onFileUpload={handleFileUpload}
            onToggleFileAnonymization={handleToggleFileAnonymization}
            onViewAuditLog={handleViewAuditLog}
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

      {/* Analyzing Overlay */}
      {isAnalyzing && <LoadingOverlay message="Analyzing..." />}
    </div>
  );
}

export default App;