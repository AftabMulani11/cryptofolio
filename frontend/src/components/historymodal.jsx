import React, { useState, useEffect } from 'react';
import '../styles/Portfolio.css'; 
import { API_URL } from '../config';

const HistoryModal = ({ symbol, name, onClose, onEditTransaction }) => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      const username = sessionStorage.getItem('username');
      const token = sessionStorage.getItem('token'); 
      
      if (!username || !token) return;

      try {
        // Using API_URL variable here
        const res = await fetch(`${API_URL}/api/portfolio?username=${username}`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await res.json();
        
        // Filter for this specific coin
        const coinTxs = data.filter(tx => tx.symbol === symbol);
        
        // Sort newest first
        coinTxs.sort((a, b) => new Date(b.date) - new Date(a.date));
        
        setTransactions(coinTxs);
      } catch (err) {
        console.error("Error loading history", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [symbol, API_URL]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{width: '600px', maxWidth: '95vw'}}>
        <div className="modal-header">
            <h3>{name} ({symbol}) History</h3>
            <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div style={{maxHeight: '400px', overflowY: 'auto'}}>
            {loading ? (
                <div style={{padding:'20px', textAlign:'center'}}>Loading history...</div>
            ) : transactions.length === 0 ? (
                <div style={{padding:'20px', textAlign:'center'}}>No transactions found.</div>
            ) : (
                <table className="portfolio-table" style={{fontSize: '0.9rem'}}>
                    <thead>
                        <tr>
                            <th style={{padding:'10px'}}>Date</th>
                            <th style={{padding:'10px'}}>Type</th>
                            <th style={{padding:'10px'}}>Amount</th>
                            <th style={{padding:'10px'}}>Price</th>
                            <th style={{padding:'10px'}}>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {transactions.map(tx => (
                            <tr key={tx.id}>
                                <td style={{padding:'10px', borderBottom:'1px solid var(--border-color)'}}>{tx.date}</td>
                                <td style={{padding:'10px', borderBottom:'1px solid var(--border-color)'}}>
                                    <span className={`type-badge ${tx.type}`}>{tx.type}</span>
                                </td>
                                <td style={{padding:'10px', borderBottom:'1px solid var(--border-color)'}}>{tx.amount}</td>
                                <td style={{padding:'10px', borderBottom:'1px solid var(--border-color)'}}>${parseFloat(tx.price).toLocaleString()}</td>
                                <td style={{padding:'10px', borderBottom:'1px solid var(--border-color)'}}>
                                    <button 
                                        className="action-btn-icon edit" 
                                        onClick={() => onEditTransaction(tx)}
                                        title="Edit this transaction"
                                    >
                                        ✏️
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
      </div>
    </div>
  );
};

export default HistoryModal;