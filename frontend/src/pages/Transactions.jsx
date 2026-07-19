import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Portfolio.css';
import { API_URL } from '../config';

const Transactions = ({ onCoinClick }) => {
  const [transactions, setTransactions] = useState([]);
  
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const getPrimaryIcon = (s) => `https://bin.bnbstatic.com/static/images/home/coin-logo/${s.toUpperCase()}.png`;
  const getBackupIcon = (s) => `https://assets.coincap.io/assets/icons/${s.toLowerCase()}@2x.png`;
  const handleImageError = (e, s) => { if (e.target.src !== getBackupIcon(s)) e.target.src = getBackupIcon(s); else e.target.style.display = 'none'; };

  const fetchPortfolio = useCallback(async () => {
      try {
        const username = sessionStorage.getItem('username');
        const token = sessionStorage.getItem('token'); 
        if (!username || !token) return;

        const txRes = await fetch(`${API_URL}/api/portfolio?username=${username}`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        const txData = await txRes.json();
        
        if (Array.isArray(txData)) {
            // FIX: Sort by ID (Timestamp) instead of just Date string
            // This ensures same-day transactions are shown in correct order (Newest first)
            const sorted = txData.sort((a, b) => Number(b.id) - Number(a.id));
            setTransactions(sorted);
        } else {
            setTransactions([]);
        }
        
      } catch (err) {
        console.error("Fetch Error:", err);
        setTransactions([]);
      }
  }, [API_URL]); 

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentTransactions = transactions.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(transactions.length / itemsPerPage);

  const handlePrev = () => setCurrentPage(prev => Math.max(1, prev - 1));
  const handleNext = () => setCurrentPage(prev => Math.min(totalPages, prev + 1));

  return (
    <div className="portfolio-page">
      <div className="portfolio-header">
          <div><h2>Transactions History</h2><p>All your buy and sell records</p></div>
      </div>
      
      <div className="table-container">
        <table className="portfolio-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Asset</th>
              <th>Date</th>
              <th>Quantity</th>
              <th>Price</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(currentTransactions) && currentTransactions.length > 0 ? (
                currentTransactions.map(tx => (
                <tr key={tx.id}>
                    <td><span className={`type-badge ${tx.type}`}>{tx.type}</span></td>
                    <td>
                        <div 
                            className="asset-cell"
                            onClick={() => onCoinClick && onCoinClick({ name: tx.coin, symbol: tx.symbol })} 
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    onCoinClick && onCoinClick({ name: tx.coin, symbol: tx.symbol });
                                }
                            }}
                            tabIndex="0"
                            role="link"
                        >
                            <img src={getPrimaryIcon(tx.symbol)} alt={tx.symbol} className="asset-icon" onError={(e)=>handleImageError(e, tx.symbol)}/>
                            <div className="asset-info"><span className="asset-symbol">{tx.symbol}</span><span className="asset-name">{tx.coin}</span></div>
                        </div>
                    </td>
                    <td>{tx.date}</td>
                    <td style={{fontWeight:'bold'}}>{tx.amount}</td>
                    <td>${parseFloat(tx.price).toLocaleString()}</td>
                    <td style={{fontWeight:'bold', color:'var(--text-primary)'}}>${(tx.amount * tx.price).toLocaleString()}</td>
                </tr>
                ))
            ) : (
                <tr><td colSpan="6" style={{textAlign:'center', padding:'40px', color:'var(--text-secondary)'}}>No transactions found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      
      {transactions.length > itemsPerPage && (
        <div className="pagination-controls">
            <button className="nav-btn" onClick={handlePrev} disabled={currentPage === 1}>
                ← Previous
            </button>
            <span className="page-info">Page {currentPage} of {totalPages}</span>
            <button className="nav-btn" onClick={handleNext} disabled={currentPage === totalPages}>
                Next →
            </button>
        </div>
      )}
    </div>
  );
};
export default Transactions;