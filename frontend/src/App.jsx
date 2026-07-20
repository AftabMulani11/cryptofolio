import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/sidebar';
import TopBar from './components/topbar';
import Profile from './components/profile';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Transactions from './pages/Transactions'; 
import Coins from './pages/Coins';
import CoinDetail from './pages/coindetail';
import LandingPage from './pages/LandingPage';
import Login from './pages/LoginPage';
import './styles/App.css';
import './styles/Portfolio.css'; 

const INACTIVITY_LIMIT = 10 * 60 * 1000; // 10 Minutes

const DashboardLayout = () => {
  const navigate = useNavigate();
  const location = useLocation(); 
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const isMobile = window.innerWidth <= 768;
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(isMobile);

  // --- INACTIVITY STATES ---
  const [showTimeoutModal, setShowTimeoutModal] = useState(false);
  const timerRef = useRef(null);
  
  // Trackers to filter "Ghost" events
  const lastActivityTime = useRef(Date.now());
  const lastScrollPos = useRef(0);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    if (window.innerWidth <= 768) {
      setIsSidebarCollapsed(true);
    }
  }, [location.pathname]);

  // --- LOGOUT LOGIC ---
  const handleLogout = useCallback(() => {
    sessionStorage.clear();
    localStorage.removeItem('username');
    localStorage.removeItem('token');
    navigate('/login');
  }, [navigate]);

  const resetTimer = useCallback(() => {
    if (showTimeoutModal) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    
    // Set new timeout
    timerRef.current = setTimeout(() => {
      console.log("⏰ Inactivity Timeout Triggered!");
      setShowTimeoutModal(true);
    }, INACTIVITY_LIMIT);
  }, [showTimeoutModal]);

  // --- STRICT ACTIVITY HANDLER (No Hover) ---
  const handleUserActivity = useCallback((e) => {
    const now = Date.now();
    
    // 1. Throttle: Limit checks to once per 500ms
    if (now - lastActivityTime.current < 500) return;

    // 2. Strict Scroll Filter (Ignore tiny layout shifts)
    if (e.type === 'scroll') {
        const currentScroll = window.scrollY;
        if (Math.abs(currentScroll - lastScrollPos.current) < 10) return;
        lastScrollPos.current = currentScroll;
    }
    
    // Debug Log
    console.log(`User Active: ${e.type} at ${new Date().toLocaleTimeString()}`);

    // If we passed checks (Click, Keydown, Touch, or Real Scroll)
    lastActivityTime.current = now;
    resetTimer();
  }, [resetTimer]);

  useEffect(() => {
    // REMOVED 'mousemove' to prevent hover from keeping session alive
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    
    // Added { capture: true } to ensure events inside scrolling divs are caught
    events.forEach(event => document.addEventListener(event, handleUserActivity, { capture: true }));
    
    // Start initial timer
    resetTimer();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      events.forEach(event => document.removeEventListener(event, handleUserActivity, { capture: true }));
    };
  }, [handleUserActivity, resetTimer]);

  const handleTimeoutConfirm = () => {
      setShowTimeoutModal(false);
      handleLogout();
  };

  const username = sessionStorage.getItem('username');
  if (!username) {
    return <Navigate to="/login" replace />;
  }

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  const handleCoinClick = (coin) => {
    navigate(`/dashboard/detail/${coin.symbol}`, { state: { coin } });
  };

  return (
    <div className={`app-container ${isSidebarCollapsed ? 'collapsed' : ''}`}>
      {!isSidebarCollapsed && window.innerWidth <= 768 && (
        <div 
          className="sidebar-overlay" 
          onClick={() => setIsSidebarCollapsed(true)}
          // FIX: Added accessibility attributes to clickable backdrop
          onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setIsSidebarCollapsed(true);
              }
          }}
          tabIndex="0"
          role="button"
        ></div>
      )}

      <Sidebar 
        onLogout={handleLogout} 
        isCollapsed={isSidebarCollapsed} 
        toggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)} 
      />
      <div className="main-content">
        <TopBar 
          theme={theme} 
          toggleTheme={toggleTheme} 
          onOpenProfile={() => setIsProfileOpen(true)} 
          onCoinSelect={handleCoinClick}
          onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
        <div className="content-wrapper">
           <Routes>
              <Route index element={<Dashboard onCoinClick={handleCoinClick} />} />
              <Route path="portfolio" element={<Portfolio onCoinClick={handleCoinClick} />} />
              <Route path="transactions" element={<Transactions onCoinClick={handleCoinClick} />} />
              <Route path="coins" element={<Coins onCoinClick={handleCoinClick} />} />
              <Route path="detail/:symbol" element={<CoinDetail onBack={() => navigate(-1)} />} />
              <Route path="settings" element={<div style={{padding:'20px'}}>Settings Panel</div>} />
              <Route path="*" element={<Navigate to="" replace />} />
           </Routes>
        </div>
      </div>
      
      {isProfileOpen && <Profile onClose={() => setIsProfileOpen(false)} onLogout={handleLogout} />}

      {/* --- TIMEOUT MODAL --- */}
      {showTimeoutModal && (
        <div className="modal-overlay timeout-modal-overlay">
            <div className="modal-content timeout-modal-content">
                <div className="timeout-icon">💤</div>
                <h3 className="timeout-title">Session Expired</h3>
                <p className="timeout-message">
                    You have been inactive for a while. Please log in again to continue.
                </p>
                <button className="timeout-btn" onClick={handleTimeoutConfirm}>
                    OK, Log In Again
                </button>
            </div>
        </div>
      )}
    </div>
  );
};

function App() {
  return (
    <Router basename={process.env.PUBLIC_URL || '/'}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Login isSignup={true} />} />
        <Route path="/dashboard/*" element={<DashboardLayout />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;