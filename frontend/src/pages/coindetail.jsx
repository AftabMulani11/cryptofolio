import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import TradeModal from '../components/trademodel'; 
import { formatCurrency, formatCompact, getIconUrl, handleImageError } from '../Utils/helpers';
import { API_URL } from '../config'; // Using centralized config
import '../styles/CoinDetail.css';

const CoinDetail = ({ onBack }) => {
  const { symbol } = useParams();
  const location = useLocation();
  
  // Use coin passed via state, or fallback object if accessed directly via URL
  const stateCoin = location.state?.coin;
  const coin = stateCoin || { symbol: symbol, name: symbol }; 

  const [ticker, setTicker] = useState(null);
  const [history, setHistory] = useState([]);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hoverData, setHoverData] = useState(null);
  const [cursorX, setCursorX] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const canvasRef = useRef(null);

  const formatTime = (t) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsRes = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${coin.symbol}USDT`);
        const statsData = await statsRes.json();
        setTicker(statsData);
        
        const historyRes = await fetch(`https://api.binance.com/api/v3/klines?symbol=${coin.symbol}USDT&interval=1h&limit=48`);
        const historyData = await historyRes.json();
        setHistory(historyData.map(d => ({ time: d[0], price: parseFloat(d[4]) })));
        
        const infoRes = await fetch(`${API_URL}/api/coin/${coin.symbol}`);
        setInfo(await infoRes.json());
        setLoading(false);
      } catch (e) {
          console.error(e);
      }
    };
    fetchData();
  }, [coin.symbol]);

  useEffect(() => {
    if (!loading && history.length > 0 && canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      const width = canvasRef.current.width;
      const height = canvasRef.current.height;
      ctx.clearRect(0, 0, width, height);
      const prices = history.map(h => h.price);
      const min = Math.min(...prices);
      const max = Math.max(...prices);
      const range = max - min;
      const padding = 30;
      const getY = (p) => height - ((p - min) / range) * (height - padding * 2) - padding;
      const step = width / (history.length - 1);
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      const isPositive = parseFloat(ticker.priceChangePercent) > 0;
      const color = isPositive ? '#00df9a' : '#ff4d4d';
      gradient.addColorStop(0, isPositive ? 'rgba(0, 223, 154, 0.25)' : 'rgba(255, 77, 77, 0.25)');
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.beginPath();
      history.forEach((point, i) => { const x = i * step; const y = getY(point.price); i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); });
      ctx.lineTo(width, height); ctx.lineTo(0, height); ctx.fillStyle = gradient; ctx.fill();
      ctx.beginPath(); ctx.lineWidth = 3; ctx.strokeStyle = color; ctx.lineJoin = 'round';
      history.forEach((point, i) => { const x = i * step; const y = getY(point.price); i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); });
      ctx.stroke();
      if (cursorX !== null) {
        ctx.beginPath(); ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 1; ctx.setLineDash([5, 5]); ctx.moveTo(cursorX, 0); ctx.lineTo(cursorX, height); ctx.stroke(); ctx.setLineDash([]);
        const index = Math.round(cursorX / step);
        if (history[index]) { ctx.beginPath(); ctx.fillStyle = '#fff'; ctx.arc(cursorX, getY(history[index].price), 6, 0, Math.PI * 2); ctx.fill(); }
      }
    }
  }, [loading, history, ticker, cursorX]);

  const handleMouseMove = (e) => {
    if (!canvasRef.current || history.length === 0) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const step = canvasRef.current.width / (history.length - 1);
    const index = Math.round(x / step);
    if (index >= 0 && index < history.length) {
      setCursorX(index * step);
      setHoverData({ x: e.clientX - rect.left, y: e.clientY - rect.top, time: formatTime(history[index].time), price: formatCurrency(history[index].price) });
    }
  };
  const getRangePercent = () => {
    if (!ticker) return 50;
    const high = parseFloat(ticker.highPrice); const low = parseFloat(ticker.lowPrice); const current = parseFloat(ticker.lastPrice);
    return Math.min(Math.max(((current - low) / (high - low)) * 100, 0), 100);
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="detail-page">
      <div className="detail-header">
        <div className="header-left">
            <button className="back-button" onClick={onBack}>← Back</button>
            <div className="detail-title-group"><img src={getIconUrl(coin.symbol)} alt={coin.symbol} className="detail-icon" onError={(e) => handleImageError(e, coin.symbol)}/><div><h1>{coin.name}</h1><span className="detail-symbol">{coin.symbol}</span></div></div>
        </div>
        <div className="detail-price-group">
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '15px'}}>
                <h2 style={{margin: 0}}>{formatCurrency(ticker.lastPrice)}</h2>
                <button 
                    onClick={() => setShowModal(true)}
                    style={{
                        background: 'var(--accent-green)',
                        color: '#000',
                        border: 'none',
                        padding: '8px 20px',
                        borderRadius: '6px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        height: 'fit-content'
                    }}
                >
                    Buy
                </button>
            </div>
            <span className={parseFloat(ticker.priceChangePercent) > 0 ? 'badge-green' : 'badge-red'} style={{display:'block', marginTop:'5px'}}>
                {parseFloat(ticker.priceChangePercent).toFixed(2)}% (24h)
            </span>
        </div>
      </div>
      <div className="chart-container">
        <div className="chart-header"><h3>Price Trend (48h)</h3><div className="chart-legend"><span className="legend-price">{hoverData ? hoverData.price : formatCurrency(ticker.lastPrice)}</span><span className="legend-time">{hoverData ? hoverData.time : 'Live'}</span></div></div>
        <div className="canvas-wrapper" onMouseMove={handleMouseMove} onMouseLeave={() => {setHoverData(null); setCursorX(null);}}><canvas ref={canvasRef} width={900} height={350} className="price-canvas" />{hoverData && <div className="chart-tooltip" style={{ left: hoverData.x + 15, top: 50 }}><strong>{hoverData.price}</strong><br/>{hoverData.time}</div>}</div>
      </div>
      <div className="details-grid-container">
        <div className="details-column">
            <h3 className="section-title">Performance</h3>
            <div className="range-card">
                <div className="range-labels"><div><small>24h Low</small><br/><strong>{formatCurrency(ticker.lowPrice)}</strong></div><div style={{textAlign:'right'}}><small>24h High</small><br/><strong>{formatCurrency(ticker.highPrice)}</strong></div></div>
                <div className="range-bar-bg"><div className="range-bar-fill" style={{ width: `${getRangePercent()}%` }}></div><div className="range-indicator" style={{ left: `${getRangePercent()}%` }}></div></div>
            </div>
             <div className="stat-row"><div className="stat-item"><span className="label">Volume (24h)</span><span className="val">{formatCompact(ticker.quoteVolume)}</span></div><div className="stat-item"><span className="label">Trades</span><span className="val">{parseInt(ticker.count).toLocaleString()}</span></div><div className="stat-item"><span className="label">Avg Price</span><span className="val">{formatCurrency(ticker.weightedAvgPrice)}</span></div></div>
        </div>
        <div className="details-column">
            <h3 className="section-title">Supply & Info</h3>
            <div className="stat-row"><div className="stat-item"><span className="label">Market Cap</span><span className="val">{info && info.market_cap > 0 ? formatCompact(info.market_cap) : '—'}</span></div><div className="stat-item"><span className="label">Circulating Supply</span><span className="val">{info && info.supply > 0 ? formatCompact(info.supply) : '—'} {coin.symbol}</span></div><div className="stat-item"><span className="label">All Time High</span><span className="val">{info && info.ath > 0 ? formatCurrency(info.ath) : '—'}</span></div></div>
            <div className="description-box"><h4>About {coin.name}</h4><p>{info && info.description ? info.description : `Real-time market data for ${coin.name} (${coin.symbol}).`}</p></div>
        </div>
      </div>

      {showModal && (
          <TradeModal 
            coin={coin} 
            currentPrice={parseFloat(ticker.lastPrice)} 
            onClose={() => setShowModal(false)} 
            onSuccess={() => {}}
            initialType="buy"
            initialAmount=""
          />
      )}
    </div>
  );
};
export default CoinDetail;