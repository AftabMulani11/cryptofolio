// src/utils/helpers.js

// --- Formatting ---
export const formatCurrency = (value) => 
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);

export const formatCompact = (number) => 
  new Intl.NumberFormat('en-US', { notation: "compact", maximumFractionDigits: 2, style: "currency", currency: "USD" }).format(number);

// --- Images ---
export const getIconUrl = (symbol) => 
  `https://bin.bnbstatic.com/static/images/home/coin-logo/${symbol.toUpperCase()}.png`;

export const getBackupIconUrl = (symbol) => 
  `https://assets.coincap.io/assets/icons/${symbol.toLowerCase()}@2x.png`;

export const handleImageError = (e, symbol) => {
  const backup = getBackupIconUrl(symbol);
  if (e.target.src !== backup) {
    e.target.src = backup;
  } else {
    e.target.style.display = 'none';
  }
};