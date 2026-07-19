import React, { useState, useEffect } from 'react';
import '../styles/Profile.css';
import { API_URL } from '../config';

const ProfileModal = ({ onClose, onLogout }) => {
  const [view, setView] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  
  const [user, setUser] = useState({
    name: "Loading...",
    email: "...",
    joinDate: "...",
    totalValue: "...",
    totalTrades: 0,
    pnl: "..."
  });

  const [editForm, setEditForm] = useState({ name: '', email: '' }); 
  const [securityForm, setSecurityForm] = useState({ currentPass: '', newPass: '', confirmPass: '' });


  // --- 1. Fetch Real-Time Profile Data ---
  useEffect(() => {
    const fetchProfile = async () => {
      const username = sessionStorage.getItem('username');
      const token = sessionStorage.getItem('token');
      
      if (!username || !token) return;

      try {
        const res = await fetch(`${API_URL}/api/profile?username=${username}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setEditForm({ name: data.name, email: data.email });
        }
      } catch (error) {
        console.error("Failed to fetch profile:", error);
      }
    };

    fetchProfile();
  }, [API_URL]);

  const handleSaveProfile = async () => { 
      const username = sessionStorage.getItem('username');
      const token = sessionStorage.getItem('token');
      
      if (!username || !token) return;
      
      if (!editForm.name.trim() || !editForm.email.trim()) {
          alert("Name and Email cannot be empty.");
          return;
      }

      setIsLoading(true);
      try {
          const res = await fetch(`${API_URL}/api/profile?username=${username}`, {
              method: 'PUT',
              headers: { 
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({ name: editForm.name, email: editForm.email })
          });

          const data = await res.json();

          if (res.ok) {
              alert("Profile updated successfully!");
              setUser(prev => ({ ...prev, name: editForm.name, email: editForm.email }));
              setView('main');
          } else {
              alert(data.error || data.message || "Failed to update profile");
          }
      } catch (err) {
          alert("Network error.");
      } finally {
          setIsLoading(false);
      }
  };
  
  const handleSaveSecurity = async () => {
    if (!securityForm.currentPass || !securityForm.newPass || !securityForm.confirmPass) {
        return alert("Please fill in all fields.");
    }

    if (securityForm.newPass !== securityForm.confirmPass) {
        return alert("New passwords do not match.");
    }
    
    const username = sessionStorage.getItem('username');
    const token = sessionStorage.getItem('token');
    
    if (!username || !token) return;

    setIsLoading(true);
    try {
        const endpoint = `${API_URL}/api/password-update`; 

        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                username: username,
                currentPass: securityForm.currentPass,
                newPass: securityForm.newPass
            })
        });

        const data = await res.json();

        if (res.ok) {
            alert("Password updated successfully!");
            setSecurityForm({ currentPass: '', newPass: '', confirmPass: '' });
            setView('main');
        } else {
            alert(data.message || "Failed to update password");
        }
    } catch (err) {
        alert("Network error.");
    } finally {
        setIsLoading(false);
    }
  };

  const getInitials = (name) => name ? name.charAt(0).toUpperCase() : 'U';

  // --- VIEWS (Main, Edit, Security) ---
  if (view === 'main') {
    return (
      <div className="profile-overlay" onClick={onClose}>
        <div className="profile-card slide-up" onClick={(e) => e.stopPropagation()}>
          <div className="profile-header">
            <button className="close-icon" onClick={onClose}>×</button>
            <div className="profile-avatar-large">{getInitials(user.name)}</div>
            <h2>{user.name}</h2>
          </div>

          <div className="profile-stats-row">
            <div className="stat-item">
              <span className="label">NET WORTH</span>
              <span className="value text-green">{user.totalValue}</span>
            </div>
            <div className="stat-item">
              <span className="label">PNL</span>
              <span className={`value ${user.pnl && user.pnl.includes('-') ? 'text-red' : 'text-green'}`}>{user.pnl}</span>
            </div>
            <div className="stat-item">
              <span className="label">TRADES</span>
              <span className="value text-neutral">{user.totalTrades}</span>
            </div>
          </div>

          <div className="profile-details">
            <div className="detail-row"><span>Email</span><strong>{user.email}</strong></div>
            <div className="detail-row"><span>Joined</span><strong>{user.joinDate}</strong></div>
          </div>

          <div className="profile-actions">
            <button className="action-btn" onClick={() => setView('edit')}>Edit Profile</button>
            <button className="action-btn secondary" onClick={() => setView('security')}>Security Settings</button>
            <button className="logout-btn-large" onClick={onLogout}>Log Out</button>
          </div>
        </div>
      </div>
    );
  }

  if (view === 'edit') {
    return (
      <div className="profile-overlay" onClick={onClose}>
        <div className="profile-card slide-up" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header-row">
            <button className="back-btn" onClick={() => setView('main')}>← Back</button>
            <h3>Edit Profile</h3>
          </div>
          <div className="form-container">
            <div className="form-group">
                <label>Display Name</label>
                <input type="text" value={editForm.name} onChange={(e) => setEditForm({...editForm, name: e.target.value})} />
            </div>
            <div className="form-group">
                <label>Email</label>
                <input type="email" value={editForm.email} onChange={(e) => setEditForm({...editForm, email: e.target.value})} />
            </div>
          </div>
          <div className="profile-actions">
            <button className="action-btn primary" onClick={handleSaveProfile} disabled={isLoading}>
                {isLoading ? "Saving..." : "Save Changes"}
            </button>
            <button className="logout-btn-large" onClick={() => setView('main')} disabled={isLoading}>Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  if (view === 'security') {
    return (
      <div className="profile-overlay" onClick={onClose}>
        <div className="profile-card slide-up" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header-row">
            <button className="back-btn" onClick={() => setView('main')}>← Back</button>
            <h3>Security</h3>
          </div>
          <div className="form-container">
            <div className="form-group">
                <label>Current Password</label>
                <input type="password" value={securityForm.currentPass} onChange={(e) => setSecurityForm({...securityForm, currentPass: e.target.value})} />
            </div>
            <div className="form-group">
                <label>New Password</label>
                <input type="password" value={securityForm.newPass} onChange={(e) => setSecurityForm({...securityForm, newPass: e.target.value})} />
            </div>
            <div className="form-group">
                <label>Confirm Password</label>
                <input type="password" value={securityForm.confirmPass} onChange={(e) => setSecurityForm({...securityForm, confirmPass: e.target.value})} />
            </div>
          </div>
          <div className="profile-actions">
            <button className="action-btn primary" onClick={handleSaveSecurity} disabled={isLoading}>
                {isLoading ? "Updating..." : "Update Password"}
            </button>
            <button className="logout-btn-large" onClick={() => setView('main')} disabled={isLoading}>Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default ProfileModal;