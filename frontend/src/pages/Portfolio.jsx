import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import TradeModal from '../components/trademodel';
import HistoryModal from '../components/historymodal';
import DoughnutChart from '../components/DoughnutChart';
import { getIconUrl, handleImageError } from '../Utils/helpers';
import '../styles/Portfolio.css';
import { API_URL } from '../config';

const Portfolio = ({ onCoinClick }) => {
  const navigate = useNavigate();
  const [assets, setAssets] = useState([]);
  
  const [stats, setStats] = useState({
    totalBalance: '$0.00',
    totalInvested: '$0.00',
    totalSpentLifetime: '$0.00',
    totalRealizedGain: '$0.00',
    totalUnrealizedGain: '$0.00',
    netProfit: '$0.00',
    profitPercent: '0.00%',
    bestPerformer: { symbol: '-', change: '0.00%' },
    totalTrades: 0,
  });
  const [loading, setLoading] = useState(true);
  
  const [showModal, setShowModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [selectedCoinForModal, setSelectedCoinForModal] = useState(null);
  const [editingTx, setEditingTx] = useState(null);
  const [initialModalType, setInitialModalType] = useState('buy');
  const [initialModalAmount, setInitialModalAmount] = useState('');

  const fetchAssets = useCallback(async () => {
      try {
        const username = sessionStorage.getItem('username');
        const token = sessionStorage.getItem('token'); 
        if (!username || !token) return;

        const res = await fetch(`${API_URL}/api/dashboard?username=${username}`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await res.json();
        
        if (data.assets) {
            setAssets(data.assets);
            setStats({
                totalBalance: data.totalBalance || '$0.00',
                totalInvested: data.totalInvested || '$0.00',
                totalSpentLifetime: data.totalSpentLifetime || '$0.00',
                totalRealizedGain: data.totalRealizedGain || '$0.00',
                totalUnrealizedGain: data.totalUnrealizedGain || '$0.00',
                netProfit: data.netProfit || '$0.00',
                profitPercent: data.profitPercent || '0.00%',
                bestPerformer: data.bestPerformer || { symbol: '-', change: '0.00%' },
                totalTrades: data.totalTrades || 0,
            });
        } else {
            setAssets([]);
        }
        setLoading(false);
      } catch (err) {
        console.error("Fetch Error:", err);
        setAssets([]);
        setLoading(false);
      }
  }, [API_URL]); 

  useEffect(() => {
    fetchAssets();
    const interval = setInterval(fetchAssets, 3000);
    return () => clearInterval(interval);
  }, [fetchAssets]);

  // --- UPDATED EXPORT FUNCTION ---
  const handleExportData = () => {
      const username = sessionStorage.getItem('username');
      if (!username) return;
      // Calls the new single endpoint that returns an Excel file with 2 tabs
      window.open(`${API_URL}/api/export/all-data?username=${username}`, '_self');
  };

  const handleBuy = (asset) => { 
      setEditingTx(null);
      setSelectedCoinForModal({ symbol: asset.symbol, name: asset.name });
      setInitialModalType('buy');
      setInitialModalAmount('');
      setShowModal(true);
  };

  const handleSell = (asset) => {
      setEditingTx(null);
      setSelectedCoinForModal({ symbol: asset.symbol, name: asset.name });
      setInitialModalType('sell');
      setInitialModalAmount(''); 
      setShowModal(true);
  };
  
  const handleEdit = (asset) => {
      setSelectedCoinForModal({ symbol: asset.symbol, name: asset.name });
      setShowHistoryModal(true);
  };
  
  const handleEditTransaction = (tx) => {
      setShowHistoryModal(false);
      setEditingTx(tx);
      setSelectedCoinForModal({ symbol: tx.symbol, name: tx.coin });
      setShowModal(true);
  };
  
  const handleModalSuccess = () => { fetchAssets(); };

  if (loading) return <div className="loading">Loading Portfolio...</div>;

  const isPositive = parseFloat(stats.profitPercent) >= 0;

  const getGainColor = (value) => {
      if (!value) return 'text-neutral';
      return parseFloat(value.replace(/[^0-9.-]+/g,"")) >= 0 ? 'text-green' : 'text-red';
  };

  const getBestPerformerColor = () => {
      if (!stats.bestPerformer || !stats.bestPerformer.change) return 'text-neutral';
      const val = parseFloat(stats.bestPerformer.change.replace('%', ''));
      return val >= 0 ? 'text-green' : 'text-red';
  };

  return (
    <div className="portfolio-page">
      <div className="portfolio-header">
          <div><h2>Portfolio</h2><p>Performance & Allocation</p></div>
          <div className="header-actions">
              {/* --- UPDATED EXPORT BUTTON --- */}
              <button 
                  className="action-btn-icon export" 
                  onClick={handleExportData}
                  title="Download full Excel report"
              >
                📊 Export Excel Report
              </button>

              <button className="add-btn" onClick={() => navigate('/dashboard/coins')}>+ Add New Asset</button>
          </div>
      </div>

      <div className="insights-container">
        <div className="stats-column">
             <div className="insight-card">
                <span className="insight-label">Current Balance</span>
                <span className="insight-value">{stats.totalBalance}</span>
             </div>
             <div className="insight-card">
                <span className="insight-label">Total Spent (Lifetime)</span>
                <span className="insight-value">{stats.totalSpentLifetime}</span>
             </div>
             <div className="insight-card">
                <span className="insight-label">Realized Gain (Closed Trades)</span>
                <span className={`insight-value ${getGainColor(stats.totalRealizedGain)}`}>{stats.totalRealizedGain}</span>
             </div>
             <div className="insight-card">
                <span className="insight-label">Unrealized Gain (Open Positions)</span>
                <span className={`insight-value ${getGainColor(stats.totalUnrealizedGain)}`}>{stats.totalUnrealizedGain}</span>
             </div>
             <div className="insight-card">
                <span className="insight-label">Net Profit / Loss (Lifetime)</span>
                <span className={`insight-value ${isPositive ? 'text-green' : 'text-red'}`}>
                    {stats.netProfit} <small>({stats.profitPercent})</small>
                </span>
             </div>
             <div className="insight-card">
                <span className="insight-label">Best Performer</span>
                <div className="insight-best">
                    {stats.bestPerformer.symbol !== '-' && (
                        <img 
                            src={getIconUrl(stats.bestPerformer.symbol)} 
                            alt={stats.bestPerformer.symbol} 
                            className="mini-icon" 
                            onError={(e) => handleImageError(e, stats.bestPerformer.symbol)}
                        />
                    )}
                    <span className={getBestPerformerColor()}>{stats.bestPerformer.symbol} {stats.bestPerformer.change}</span>
                </div>
            </div>
        </div>

        <div className="chart-column">
            <h3 className="chart-heading">Allocation</h3>
            {assets.length > 0 ? <DoughnutChart assets={assets} /> : <div className="no-chart">No assets</div>}
        </div>
      </div>
      
      <div className="table-container">
        <table className="portfolio-table">
          <thead>
            <tr>
                <th>Asset</th>
                <th>Allocation</th>
                <th>Price</th>
                <th>Avg Buy</th>
                <th>Holdings</th>
                <th>Total Value</th>
                <th>Return</th>
                <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {assets.length > 0 ? (
                assets.map(asset => {
                    const pnlColor = asset.pnl_percent >= 0 ? 'text-green' : 'text-red';
                    return (
                        <tr key={asset.symbol}>
                            <td>
                                <div 
                                    className="asset-cell"
                                    onClick={() => onCoinClick && onCoinClick({ name: asset.name, symbol: asset.symbol })}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' || e.key === ' ') {
                                            e.preventDefault();
                                            onCoinClick && onCoinClick({ name: asset.name, symbol: asset.symbol });
                                        }
                                    }}
                                    tabIndex="0"
                                    role="link"
                                >
                                    <img src={getIconUrl(asset.symbol)} alt={asset.symbol} className="asset-icon" onError={(e)=>handleImageError(e, asset.symbol)}/>
                                    <div className="asset-info"><span className="asset-symbol">{asset.symbol}</span><span className="asset-name">{asset.name}</span></div>
                                </div>
                            </td>
                            <td style={{width:'100px'}}>
                                <div className="allocation-bar-bg">
                                    <div className="allocation-bar-fill" style={{width: `${asset.allocation}%`}}></div>
                                </div>
                                <span style={{fontSize:'0.75rem', color:'var(--text-secondary)'}}>{asset.allocation.toFixed(1)}%</span>
                            </td>
                            <td>{asset.price}</td>
                            <td style={{color:'var(--text-secondary)'}}>{asset.avg_price}</td>
                            <td style={{fontWeight:'bold'}}>{asset.holdings}</td>
                            <td style={{fontWeight:'bold', color:'var(--text-primary)'}}>{asset.value}</td>
                            <td className={pnlColor} style={{fontWeight:'bold'}}>
                                {asset.pnl_percent > 0 ? '+' : ''}{asset.pnl_percent.toFixed(2)}%
                            </td>
                            <td>
                                <div className="actions-cell">
                                    <button className="action-btn-icon" onClick={() => handleBuy(asset)} title="Buy">Buy</button>
                                    <button className="action-btn-icon delete" onClick={() => handleSell(asset)} title="Sell">Sell</button>
                                    <button className="action-btn-icon edit" onClick={() => handleEdit(asset)} title="History">Edit</button>
                                </div>
                            </td>
                        </tr>
                    );
                })
            ) : (
                <tr><td colSpan="8" style={{textAlign:'center', padding:'40px', color:'var(--text-secondary)'}}>You have no active assets.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      
      {showHistoryModal && selectedCoinForModal && (
          <HistoryModal symbol={selectedCoinForModal.symbol} name={selectedCoinForModal.name} onClose={() => setShowHistoryModal(false)} onEditTransaction={handleEditTransaction} />
      )}

      {showModal && (
          <TradeModal coin={selectedCoinForModal} currentPrice={0} onClose={() => setShowModal(false)} onSuccess={handleModalSuccess} editData={editingTx} initialType={initialModalType} initialAmount={initialModalAmount} />
      )}
    </div>
  );
};
export default Portfolio;