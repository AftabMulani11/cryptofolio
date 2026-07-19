import React, { useState, useEffect, useRef } from 'react';
import { getIconUrl, handleImageError } from '../Utils/helpers';
import { BLOCKED_COINS } from '../Utils/constants'; // Imported constant
import '../styles/Profile.css'; 
import '../styles/Portfolio.css'; 
import { API_URL } from '../config';

const TradeModal = ({ coin: initialCoin, currentPrice, onClose, onSuccess, editData = null, initialType = 'buy', initialAmount = '' }) => {
  
  const [type, setType] = useState(editData ? editData.type : initialType);
  const [amount, setAmount] = useState(editData ? editData.amount : initialAmount);
  const [price, setPrice] = useState(editData ? editData.price : '');
  const [date, setDate] = useState(editData ? editData.date : new Date().toISOString().split('T')[0]); 
  const [selectedCoin, setSelectedCoin] = useState(initialCoin || null);
  
  const [userHoldings, setUserHoldings] = useState(null);

  const [allCoins, setAllCoins] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  
  const [error, setError] = useState('');
  const [loadingPrice, setLoadingPrice] = useState(false);
  const dropdownRef = useRef(null);

  const todayDate = new Date().toISOString().split('T')[0];

  // 1. Fetch All Coins
  useEffect(() => {
    const fetchCoins = async () => {
      try {
        const res = await fetch(`${API_URL}/api/coins`);
        const data = await res.json();
        setAllCoins(data);
      } catch (e) { console.error("Failed to load coins"); }
    };
    fetchCoins();
  }, [API_URL]);

  // 2. Handle Edit Mode & Initial Selection
  useEffect(() => {
    if (editData) {
        setSelectedCoin({ symbol: editData.symbol, name: editData.coin });
        setSearchQuery(`${editData.coin} (${editData.symbol})`);
    } else if (initialCoin) {
        setSelectedCoin(initialCoin);
        setSearchQuery(`${initialCoin.name} (${initialCoin.symbol})`);
        
        if (!initialAmount && currentPrice > 0) {
             setPrice(currentPrice);
        }
    }
  }, [editData, initialCoin, currentPrice, initialAmount]);

  // 3. Fetch Historical Price
  useEffect(() => {
    if (!selectedCoin || !date) return;

    const fetchHistory = async () => {
        setLoadingPrice(true);
        try {
            const res = await fetch(`${API_URL}/api/history?symbol=${selectedCoin.symbol}&date=${date}`);
            if (res.ok) {
                const data = await res.json();
                if (data.price) setPrice(data.price); 
            }
        } catch (err) {
            console.error("Failed to fetch history");
        } finally {
            setLoadingPrice(false);
        }
    };

    const isToday = date === todayDate;

    if (editData) {
        if (date !== editData.date) fetchHistory();
    } else {
        if (isToday) {
            const isMatchingCoin = initialCoin && (initialCoin.symbol === selectedCoin.symbol);
            if (isMatchingCoin && currentPrice > 0 && !price) {
                 setPrice(currentPrice);
            } else if (!price || (initialAmount && type === 'sell')) {
                 fetchHistory();
            }
        } else {
            fetchHistory();
        }
    }
  }, [date, selectedCoin, API_URL, editData, currentPrice, initialCoin, todayDate, type, initialAmount, price]); 

  // NEW: Fetch User Holdings for Selected Coin
  useEffect(() => {
    if (!selectedCoin) {
        setUserHoldings(null);
        return;
    }
    
    const fetchHoldings = async () => {
        const username = sessionStorage.getItem('username');
        const token = sessionStorage.getItem('token');
        if (!username || !token) return;

        try {
            const res = await fetch(`${API_URL}/api/holdings/${selectedCoin.symbol}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                const qty = parseFloat(data.holdings);
                setUserHoldings(qty > 0.0000001 ? qty : 0);
            } else {
                setUserHoldings(0);
            }
        } catch (e) { 
            console.error(e); 
            setUserHoldings(0);
        }
    };
    fetchHoldings();
  }, [selectedCoin, API_URL]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectCoin = (coin) => {
      setSelectedCoin(coin);
      setSearchQuery(`${coin.name} (${coin.symbol})`);
      setShowDropdown(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!selectedCoin) {
        setError("Please select a coin.");
        return;
    }

    const username = sessionStorage.getItem('username');
    const token = sessionStorage.getItem('token'); 
    
    if (!username || !token) { setError("You must be logged in."); return; }

    const payload = { 
        type, 
        coin: selectedCoin.name, 
        symbol: selectedCoin.symbol, 
        amount: parseFloat(amount), 
        price: parseFloat(price), 
        date: date,
        ...(editData && { id: editData.id })
    };

    try {
      const method = editData ? 'PUT' : 'POST';
      const res = await fetch(`${API_URL}/api/portfolio?username=${username}`, { 
          method: method, 
          headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
          }, 
          body: JSON.stringify(payload) 
      });
      
      const data = await res.json();
      if (!res.ok) setError(data.error || "Transaction failed");
      else { 
          alert(`Success!`); 
          onSuccess(); 
          onClose(); 
      }
    } catch (err) { setError("Network error."); }
  };

  // Filter with imported BLOCKED_COINS
  const filteredCoins = allCoins.filter(c => 
    (c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    c.symbol.toLowerCase().includes(searchQuery.toLowerCase())) &&
    !BLOCKED_COINS.includes(c.symbol)
  );

  const total = (parseFloat(amount || 0) * parseFloat(price || 0)).toLocaleString();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
            <h3>{editData ? 'Edit Transaction' : (initialType === 'sell' ? `Sell ${selectedCoin?.symbol || ''}` : 'Add Transaction')}</h3>
            <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        {error && <div className="error-banner" style={{marginBottom: '15px'}}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="radio-group">
              <label className={`${type==='buy'?'active-buy':''} ${editData ? 'disabled' : ''}`}>
                  <input 
                    type="radio" 
                    name="type" 
                    value="buy" 
                    checked={type==='buy'} 
                    onChange={()=>setType('buy')}
                    disabled={!!editData}
                  /> Buy
              </label>
              <label className={`${type==='sell'?'active-sell':''} ${editData ? 'disabled' : ''}`}>
                  <input 
                    type="radio" 
                    name="type" 
                    value="sell" 
                    checked={type==='sell'} 
                    onChange={()=>setType('sell')}
                    disabled={!!editData}
                  /> Sell
              </label>
          </div>

          <div className="form-group" ref={dropdownRef} style={{position: 'relative'}}>
              <label style={{display:'flex', alignItems:'center', gap:'8px'}}>
                  Select Asset
                  {selectedCoin && (
                      <img 
                        src={getIconUrl(selectedCoin.symbol)} 
                        alt="" 
                        style={{width:'18px', height:'18px', borderRadius:'50%'}} 
                        onError={(e) => handleImageError(e, selectedCoin.symbol)}
                      />
                  )}
              </label>
              <input 
                type="text" 
                placeholder="Search Bitcoin, Ethereum..." 
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setShowDropdown(true); }}
                onFocus={() => setShowDropdown(true)}
                className="form-input"
                disabled={!!editData} 
                style={editData ? {opacity: 0.7, cursor: 'not-allowed'} : {}}
              />
              {showDropdown && !editData && (
                  <div className="search-results-dropdown" style={{top: '100%', maxHeight: '200px'}}>
                      {filteredCoins.map(c => (
                          <div key={c.symbol} className="search-item" onClick={() => handleSelectCoin(c)}>
                              <img 
                                src={getIconUrl(c.symbol)} 
                                alt={c.symbol} 
                                style={{width:'24px', height:'24px', borderRadius:'50%', marginRight:'10px'}} 
                                onError={(e)=>handleImageError(e, c.symbol)}
                              />
                              <span style={{fontWeight:'bold', width:'50px'}}>{c.symbol}</span>
                              <span>{c.name}</span>
                          </div>
                      ))}
                  </div>
              )}
          </div>

          <div className="form-group">
              <label>Date Bought/Sold</label>
              <input 
                type="date" 
                value={date} 
                onChange={(e) => setDate(e.target.value)} 
                className="form-input" 
                required 
                max={todayDate}
              />
          </div>

          <div className="form-group">
              <label style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  Quantity
                  {userHoldings !== null && (
                      <span style={{fontSize:'0.8rem', color:'var(--text-secondary)', fontWeight:'normal'}}>
                          Owned: <strong style={{color: 'var(--text-primary)'}}>{userHoldings}</strong>
                      </span>
                  )}
              </label>
              <input 
                type="number" 
                placeholder="0.00" 
                value={amount} 
                onChange={(e)=>setAmount(e.target.value)} 
                required 
                step="any" 
                className="form-input"
                disabled={!!editData}
                style={editData ? {opacity: 0.7, cursor: 'not-allowed'} : {}}
              />
          </div>

          <div className="form-group" style={{position:'relative'}}>
              <label>Price per Coin ($) {loadingPrice && <span className="text-green" style={{fontSize:'0.8em'}}> Fetching history...</span>}</label>
              <input 
                type="number" 
                value={price} 
                onChange={(e)=>setPrice(e.target.value)} 
                required 
                step="any" 
                className="form-input"
              />
          </div>

          <div style={{textAlign:'right', marginTop:'10px', marginBottom: '20px'}}>
              Total Value: <strong className="text-green">${total}</strong>
          </div>
          
          <button type="submit" className="submit-btn" style={{backgroundColor:type==='buy'?'var(--accent-green)':'var(--accent-red)', color:'white'}}>
            {editData ? 'Update Transaction' : `Confirm ${type.toUpperCase()}`}
          </button>
        </form>
      </div>
    </div>
  );
};
export default TradeModal;