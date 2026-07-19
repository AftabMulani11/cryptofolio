import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import StatCard from '../components/statcard';
import AssetTable from '../components/assettable';
import TradeModal from '../components/trademodel'; 
import '../styles/Dashboard.css';
import { API_URL } from '../config';

const Dashboard = ({ onCoinClick }) => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const prevAssetPricesRef = useRef({});
  const [error, setError] = useState(null);

  // --- MODAL STATES ---
  const [showTradeModal, setShowTradeModal] = useState(false);
  const [tradeCoin, setTradeCoin] = useState(null);
  const [tradePrice, setTradePrice] = useState(0);
  const [initialTradeType, setInitialTradeType] = useState('buy');
  const [initialTradeAmount, setInitialTradeAmount] = useState('');

  const fetchData = async () => {
    try {
      setError(null);
      const username = sessionStorage.getItem('username');
      const token = sessionStorage.getItem('token');
      
      if (!username || !token) return; 

      const res = await fetch(`${API_URL}/api/dashboard?username=${username}`, {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
      });
      
      if (!res.ok) throw new Error("Failed to fetch dashboard");
      
      const json = await res.json();

      const processedAssets = json.assets.map(asset => {
        const currentPrice = asset.raw_price;
        const prevPrice = prevAssetPricesRef.current[asset.symbol];
        let priceColor = 'text-neutral';
        if (prevPrice) {
             if (currentPrice > prevPrice) priceColor = 'text-green';
             else if (currentPrice < prevPrice) priceColor = 'text-red';
        }
        prevAssetPricesRef.current[asset.symbol] = currentPrice;
        return { ...asset, priceColor };
      });
      setData({ ...json, assets: processedAssets });
    } catch (err) { 
        console.error("API Error:", err);
        setError("Failed to load dashboard.");
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleBuy = (asset) => {
      setTradeCoin(asset);
      setTradePrice(asset.raw_price);
      setInitialTradeType('buy');
      setInitialTradeAmount('');
      setShowTradeModal(true);
  };

  const handleSell = (asset) => {
      setTradeCoin(asset);
      setTradePrice(asset.raw_price);
      setInitialTradeType('sell');
      setInitialTradeAmount(asset.holdings.replace(/[^0-9.]/g, '')); 
      setShowTradeModal(true);
  };
  
  const handleModalSuccess = () => {
      setShowTradeModal(false);
      fetchData(); 
  };

  if (error) return <div className="loading" style={{color:'var(--accent-red)'}}>{error}</div>;
  if (!data) return <div className="loading">Loading Dashboard...</div>;

  const isPortfolioEmpty = data.assets.length === 0;
  const profitValue = parseFloat(data.profitPercent);

  return (
    <div className="dashboard-container">
      <div className="stats-grid">
        <StatCard 
            title="Total Balance" 
            value={data.totalBalance} 
            change={data.profitPercent} 
            isPositive={profitValue >= 0} 
        />
        <StatCard 
            title="Total Invested" 
            value={data.totalInvested}
            change="Cost Basis" 
            isPositive={true} 
        />
        <StatCard 
            title="Net Profit / Loss" 
            value={data.netProfit} 
            change={data.profitPercent} 
            isPositive={profitValue >= 0} 
        />
      </div>

      <div className="table-section">
        <h3>Your Assets</h3>
        {isPortfolioEmpty ? (
            <div className="empty-state" style={{display:'flex', flexDirection:'column', alignItems:'center', gap:'15px'}}>
                <p>You have no assets yet.</p>
                <button 
                    onClick={() => navigate('/dashboard/coins')} 
                    style={{
                        background:'var(--accent-green)', 
                        color:'#000', 
                        border:'none', 
                        padding:'10px 20px', 
                        borderRadius:'8px', 
                        fontWeight:'bold', 
                        cursor:'pointer'
                    }}
                >
                    + Buy Your First Asset
                </button>
            </div>
        ) : (
            <AssetTable 
                assets={data.assets} 
                onCoinClick={onCoinClick} 
                onBuy={handleBuy} 
                onSell={handleSell} 
            />
        )}
      </div>

      {data.recentTransactions && data.recentTransactions.length > 0 && (
        <div className="recent-activity-section">
            <h3>Recent Activity</h3>
            <div className="activity-list">
                {data.recentTransactions.map(tx => (
                    <div key={tx.id} className="activity-item">
                        <div className="activity-left">
                            <span className={`type-dot ${tx.type}`}></span>
                            <div>
                                <span className="activity-coin">{tx.coin}</span>
                                <span className="activity-date">{tx.date}</span>
                            </div>
                        </div>
                        <div className="activity-right">
                            <span className={`activity-amount ${tx.type === 'buy' ? 'text-green' : 'text-red'}`}>
                                {tx.type === 'buy' ? '+' : '-'}{tx.amount} {tx.symbol}
                            </span>
                            <span className="activity-price">@ ${tx.price.toLocaleString()}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
      )}
      
      {showTradeModal && tradeCoin && (
          <TradeModal 
            coin={tradeCoin} 
            currentPrice={tradePrice} 
            onClose={() => setShowTradeModal(false)} 
            onSuccess={handleModalSuccess}
            initialType={initialTradeType}
            initialAmount={initialTradeAmount}
          />
      )}
    </div>
  );
};
export default Dashboard;