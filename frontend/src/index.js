import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Demo mode (GitHub Pages): mock the backend /api/* in the browser,
// with live market data from Binance's free public API.
if (process.env.REACT_APP_DEMO === 'true') {
  const { installDemoApi } = require('./demo/demoApi');
  installDemoApi();
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

