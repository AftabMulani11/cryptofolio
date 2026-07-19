import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/LandingPage.css';


const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <span className="logo-icon">⚡</span> CryptoFolio
        </div>
        <div className="landing-links">
          <button onClick={() => navigate('/login')} className="btn-login">Log In</button>
          <button onClick={() => navigate('/signup')} className="btn-signup">Sign Up</button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="hero-section">
        <div className="hero-content">
          <h1>Track Your Crypto Wealth <br /> <span className="text-gradient">In Real Time</span></h1>
          <p>
            The professional dashboard for managing your portfolio. 
            Live Binance prices, detailed analytics, and secure transaction tracking.
          </p>
          <button onClick={() => navigate('/signup')} className="btn-cta">Get Started Free</button>
        </div>
        <div className="hero-bg-glow"></div>
      </header>

      {/* Features Grid */}
      <section className="features-section">
        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Live Market Data</h3>
          <p>Connects directly to Binance WebSockets for sub-second price updates.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">💼</div>
          <h3>Portfolio Tracking</h3>
          <p>Log your buy/sell transactions and calculate your exact Net Worth and PnL.</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">🔒</div>
          <h3>Secure & Private</h3>
          <p>Your data is stored securely. No API keys required to trade, just track.</p>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;