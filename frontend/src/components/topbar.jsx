import React, { useState, useEffect, useRef } from 'react';
import { getIconUrl, handleImageError } from '../Utils/helpers';
import '../styles/TopBar.css';
import { API_URL } from '../config';

const TopBar = ({ theme, toggleTheme, onOpenProfile, onCoinSelect, onToggleSidebar }) => {
  const [query, setQuery] = useState('');
  const [allCoins, setAllCoins] = useState([]);
  const [results, setResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [isMobileSearchOpen, setIsMobileSearchOpen] = useState(false);
  
  const [userInfo, setUserInfo] = useState({ name: 'User', initial: 'U' });
  
  const wrapperRef = useRef(null);
  const searchInputRef = useRef(null);

  useEffect(() => {
    const fetchUserData = async () => {
      const username = sessionStorage.getItem('username');
      const token = sessionStorage.getItem('token'); 

      if (username) {
        try {
          const res = await fetch(`${API_URL}/api/profile?username=${username}`, {
             headers: {
                 'Content-Type': 'application/json',
                 'Authorization': `Bearer ${token}` 
             }
          });

          if (res.ok) {
            const data = await res.json();
            setUserInfo({
              name: data.name || username,
              initial: (data.name || username).charAt(0).toUpperCase()
            });
          } else {
            setUserInfo({ 
                name: username, 
                initial: username.charAt(0).toUpperCase() 
            });
          }
        } catch (err) {
          setUserInfo({ name: username, initial: username.charAt(0).toUpperCase() });
        }
      }
    };
    fetchUserData();
  }, [API_URL]);

  useEffect(() => {
    const fetchCoins = async () => {
      try {
        const res = await fetch(`${API_URL}/api/coins`);
        setAllCoins(await res.json());
      } catch (err) {}
    };
    fetchCoins();
  }, [API_URL]);

  const handleSearch = (e) => {
    const val = e.target.value;
    setQuery(val);
    if (val.length > 0) {
      const filtered = allCoins.filter(c => c.name.toLowerCase().includes(val.toLowerCase()) || c.symbol.toLowerCase().includes(val.toLowerCase()));
      setResults(filtered.slice(0, 5));
      setShowResults(true);
    } else { setShowResults(false); }
  };

  const handleSelect = (c) => { onCoinSelect(c); setQuery(''); setShowResults(false); setIsMobileSearchOpen(false); };

  const toggleMobileSearch = () => {
    // Toggle state
    const nextState = !isMobileSearchOpen;
    setIsMobileSearchOpen(nextState);
    
    // If opening, focus the input after a brief delay to allow render
    if (nextState) {
        setTimeout(() => {
            if(searchInputRef.current) {
                searchInputRef.current.focus();
            }
        }, 100);
    }
  };

  // Close search when clicking outside
  useEffect(() => {
      const handleClick = (e) => { 
          if(wrapperRef.current && !wrapperRef.current.contains(e.target)) {
              setShowResults(false);
              if(query === '') setIsMobileSearchOpen(false);
          }
      };
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
  }, [query]);

  return (
    <div className="topbar">
      <div style={{display: 'flex', alignItems: 'center'}}>
        <button className="mobile-menu-btn" onClick={onToggleSidebar}>
            ☰
        </button>
        <div className={`page-title ${isMobileSearchOpen ? 'hidden-on-mobile' : ''}`}>Overview</div>
      </div>
      
      <div className="topbar-actions">
        <div className={`search-wrapper ${isMobileSearchOpen ? 'mobile-open' : ''}`} ref={wrapperRef}>
            <div className="search-container" onClick={toggleMobileSearch}>
                <span className="search-icon">🔍</span>
                <input 
                    ref={searchInputRef}
                    type="text" 
                    placeholder="Search..." 
                    className="search-input" 
                    value={query} 
                    onChange={handleSearch} 
                    onClick={(e) => e.stopPropagation()} 
                    onFocus={() => query.length > 0 && setShowResults(true)} 
                />
                {isMobileSearchOpen && (
                    <button 
                        className="close-search-btn"
                        onClick={(e) => { e.stopPropagation(); setIsMobileSearchOpen(false); setQuery(''); }}
                    >✕</button>
                )}
            </div>
            {showResults && (
                <div className="search-results-dropdown">
                    {results.length > 0 ? results.map(c => (
                        <div key={c.symbol} className="search-item" onClick={() => handleSelect(c)}>
                            <img src={getIconUrl(c.symbol)} alt={c.symbol} className="search-item-icon" onError={(e)=>handleImageError(e, c.symbol)}/>
                            <div className="search-item-info"><span className="search-item-symbol">{c.symbol}</span><span className="search-item-name">{c.name}</span></div>
                            <span className="search-item-price">${c.price.toLocaleString()}</span>
                        </div>
                    )) : <div className="search-no-results">No coins found</div>}
                </div>
            )}
        </div>

        <button className={`theme-toggle-btn ${isMobileSearchOpen ? 'hidden-on-mobile' : ''}`} onClick={toggleTheme}>{theme === 'dark' ? '☀️' : '🌙'}</button>
        
        <button className={`user-profile ${isMobileSearchOpen ? 'hidden-on-mobile' : ''}`} onClick={onOpenProfile}>
            <div className="user-info">
                <span className="user-name">{userInfo.name}</span>
            </div>
            <div className="avatar">{userInfo.initial}</div>
        </button>
        
      </div>
    </div>
  );
};
export default TopBar;