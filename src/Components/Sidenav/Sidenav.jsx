import React from 'react';
import './Sidenav.css';

const Sidenav = ({ partners, selectedPartnerId, onSelectPartner, onAddPartnerClick }) => {
  return (
    <div className="sidenav-container">
        <div className="sidenav-header">
            <h2>Partners</h2>
            <button className="add-partner-btn" onClick={onAddPartnerClick}>+</button>
        </div>
        <ul className="partner-list">
            {partners.length === 0 ? (
                <li className="no-partners-message">No partners added yet.</li>
            ) : (
                partners.map(partner => (
                    <li
                        key={partner.id}
                        className={`partner-item ${partner.id === selectedPartnerId ? 'selected' : ''}`}
                        onClick={() => onSelectPartner(partner.id)}
                    >
                        {partner.logo && <img src={partner.logo} alt={`${partner.name} logo`} className="partner-logo" />}
                        <span className="partner-name">{partner.name}</span>
                    </li>
                ))
            )}
        </ul>
    </div>
  )
}

export default Sidenav
