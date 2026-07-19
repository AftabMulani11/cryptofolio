import React, { useState, useEffect, useRef } from 'react';
import TradeModal from '../components/trademodel';
import { formatCurrency, formatCompact, getIconUrl, handleImageError } from '../Utils/helpers';
import { BLOCKED_COINS } from '../Utils/constants';
import '../styles/Coins.css';
import { API_URL } from '../config';

const Coins = ({ onCoinClick }) => {
  const [coins, setCoins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [validIcons, setValidIcons] = useState(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 50; 
  
  const [tradeCoin, setTradeCoin] = useState(null);
  const [tradePrice, setTradePrice] = useState(0);

  // Removed wsRef since we are moving to backend-only WSS
  const coinMapRef = useRef(new Map());
  
  // NEW: Helper function to handle keyboard navigation for click actions
  const handleRowKeyDown = (e, coin) => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onCoinClick(coin);
    }
  };

  // 1. Fetch Initial Coin List (Static Data)
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const res = await fetch(`${API_URL}/api/coins`);
        const data = await res.json();
        const initialMap = new Map();
        
        data.forEach(coin => { 
            if (!BLOCKED_COINS.includes(coin.symbol)) {
                initialMap.set(coin.symbol, { ...coin, prevPrice: coin.price, priceColor: 'text-neutral' }); 
            }
        });
        
        coinMapRef.current = initialMap;
        setCoins(Array.from(initialMap.values()));
        setLoading(false);
      } catch (err) {
        console.error("Error fetching initial coins:", err);
      }
    };
    fetchInitialData();
  }, [API_URL]);

  // 2. Poll Backend for Live Prices (Replaces direct WebSocket)
  useEffect(() => {
    const fetchLivePrices = async () => {
        try {
            const res = await fetch(`${API_URL}/api/live-prices`);
            if (!res.ok) return;
            
            const liveData = await res.json();
            // liveData structure: { "btcusdt": { symbol: "BTCUSDT", close: 65000, ... }, ... }

            let hasUpdates = false;

            coinMapRef.current.forEach((currentCoin, symbol) => {
                const key = `${symbol.toLowerCase()}usdt`;
                const update = liveData[key];

                if (update) {
                    const newPrice = update.close;
                    const prevPrice = currentCoin.price; // Use last known price as previous

                    // Determine color based on movement
                    let priceColor = 'text-neutral';
                    if (newPrice > prevPrice) priceColor = 'text-green';
                    else if (newPrice < prevPrice) priceColor = 'text-red';

                    // Update Map
                    coinMapRef.current.set(symbol, {
                        ...currentCoin,
                        price: newPrice,
                        prevPrice: prevPrice,
                        priceColor: priceColor,
                        change_24h: update.change,
                        volume: update.volume
                    });
                    hasUpdates = true;
                }
            });

        } catch (err) {
            console.error("Polling error:", err);
        }
    };

    // Poll every 2 seconds
    const interval = setInterval(fetchLivePrices, 2000);
    return () => clearInterval(interval);
  }, []); // Run once on mount

  // 3. Update UI State from Ref (Throttled re-renders)
  useEffect(() => {
    const interval = setInterval(() => {
        if (coinMapRef.current.size > 0 && !tradeCoin) {
            // Sort and update state to trigger render
            setCoins(Array.from(coinMapRef.current.values()).sort((a, b) => a.rank - b.rank));
        }
    }, 1000);
    return () => clearInterval(interval);
  }, [tradeCoin]);

  const handleImageLoad = (s) => setValidIcons(prev => new Set(prev).add(s));
  const handlePageClick = (num) => { setCurrentPage(num); window.scrollTo(0,0); };
  const handleNext = () => { if(currentPage < Math.ceil(coins.length / itemsPerPage)) handlePageClick(currentPage + 1); };
  const handlePrev = () => { if(currentPage > 1) handlePageClick(currentPage - 1); };
  
  const handleBuyClick = (coin) => { setTradePrice(coin.price); setTradeCoin(coin); };
  const ChangeCell = ({ value }) => (<td className={value >= 0 ? 'text-green' : 'text-red'}>{value > 0 ? '▲' : '▼'} {Math.abs(value).toFixed(2)}%</td>);

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentCoins = coins.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(coins.length / itemsPerPage);

  if (loading) return <div className="loading">Loading Market Data...</div>;

  return (
    <div className="coins-page">
      <div className="page-header-row">
        <div style={{display:'flex', alignItems:'center', gap:'10px'}}>
            <h2>Live Market</h2>
            {/* Changed text to indicate backend sync */}
            <span className="live-indicator" style={{borderColor: 'var(--accent-green)'}}>● Synced</span>
        </div>
        <span className="page-count">Page {currentPage} of {totalPages}</span>
      </div>
      <div style={{overflowX: 'auto', minHeight: '600px'}}>
        <table className="coins-table">
          <thead>
            <tr>
                <th>Rank</th>
                <th>Asset</th>
                <th>Price</th>
                <th>24h %</th>
                <th>Volume(24h)</th>
                <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {currentCoins.map((c) => (
              <tr 
                key={c.symbol} 
                onClick={() => onCoinClick(c)} 
                // FIX: Add keyboard accessibility (tabIndex, role, onKeyDown)
                onKeyDown={(e) => handleRowKeyDown(e, c)}
                tabIndex="0"
                role="link"
                style={{cursor:'pointer'}}
              >
                <td className="rank-col">{c.rank}</td>
                <td>
                  <div className="coin-id-cell">
                    {!validIcons.has(c.symbol) && <div className="coin-fallback-icon">{c.symbol[0]}</div>}
                    <img src={getIconUrl(c.symbol)} alt={c.symbol} className="coin-icon-img" style={{ display: validIcons.has(c.symbol) ? 'block' : 'none' }} onLoad={() => handleImageLoad(c.symbol)} onError={(e)=>handleImageError(e,c.symbol)} />
                    <div className="coin-name-wrapper"><span className="coin-symbol">{c.symbol}</span><span className="coin-name">{c.name || c.symbol}</span></div>
                  </div>
                </td>
                <td className={c.priceColor} style={{fontWeight:'bold', transition:'color 0.3s'}}>{formatCurrency(c.price)}</td>
                <ChangeCell value={c.change_24h} />
                <td>{formatCompact(c.volume)}</td>
                <td>
                    <button className="trade-btn" onClick={(e) => { e.stopPropagation(); handleBuyClick(c); }} style={{fontWeight:'bold'}}>
                        Buy
                    </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination-controls">
        <button onClick={handlePrev} disabled={currentPage === 1} className="nav-btn">← Prev</button>
        <div className="page-numbers">{Array.from({length: totalPages}, (_, i) => i + 1).map(num => (<button key={num} onClick={() => handlePageClick(num)} className={`page-num-btn ${currentPage===num?'active':''}`}>{num}</button>))}</div>
        <button onClick={handleNext} disabled={currentPage === totalPages} className="nav-btn">Next →</button>
      </div>
      {tradeCoin && <TradeModal coin={tradeCoin} currentPrice={tradePrice} onClose={() => setTradeCoin(null)} onSuccess={() => {}} />}
    </div>
  );
};
export default Coins;