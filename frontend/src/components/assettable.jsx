import React from 'react';
import { getIconUrl, handleImageError } from '../Utils/helpers';

// NEW: Helper function to handle keyboard navigation for click actions
const handleKeyDown = (e, action, asset) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    action(asset);
  }
};

const AssetTable = ({ assets, onCoinClick, onBuy, onSell, onEdit }) => {
  
  // Helper to stop the row/card click from firing when a button is clicked
  const handleAction = (e, action, asset) => {
    // Stop the event from bubbling up to the card container so the card click doesn't trigger
    e.stopPropagation();
    // Execute the specific button action
    action(asset);
  };

  return (
    <div className="asset-list-container">
      {/* Desktop Table View */}
      <table className="asset-table desktop-only">
        <thead>
            <tr>
                <th>Asset</th>
                <th>Price</th>
                <th>Holdings</th>
                <th>Total</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
          {assets.map(a => (
            <tr 
              key={a.id} 
              onClick={() => onCoinClick && onCoinClick(a)} 
              // FIX: Add keyboard accessibility (tabIndex, role, onKeyDown)
              onKeyDown={(e) => handleKeyDown(e, onCoinClick, a)}
              tabIndex="0"
              role="button"
              className="asset-row"
            >
              <td>
                <div className="asset-cell-content">
                  <img 
                    src={getIconUrl(a.symbol)} 
                    alt={a.symbol} 
                    className="asset-icon"
                    onError={(e) => handleImageError(e, a.symbol)}
                  />
                  <div>
                      <span className="asset-symbol">{a.symbol}</span>
                      <span className="asset-name">{a.name}</span>
                  </div>
                </div>
              </td>
              <td className={a.priceColor || ''}>{a.price}</td>
              <td>{a.holdings}</td>
              <td>{a.value}</td>
              <td>
                  <div className="action-buttons">
                      <button className="btn-buy" onClick={(e) => handleAction(e, onBuy, a)}>Buy</button>
                      <button className="btn-sell" onClick={(e) => handleAction(e, onSell, a)}>Sell</button>
                      {onEdit && <button className="btn-edit" onClick={(e) => handleAction(e, onEdit, a)}>Edit</button>}
                  </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile Card View */}
      <div className="mobile-asset-list mobile-only">
        {assets.map(a => (
            <div 
              key={a.id} 
              className="asset-card" 
              onClick={() => onCoinClick && onCoinClick(a)}
              // FIX: Add keyboard accessibility (tabIndex, role, onKeyDown)
              onKeyDown={(e) => handleKeyDown(e, onCoinClick, a)}
              tabIndex="0"
              role="button"
            >
                <div className="card-header">
                    <div className="asset-info-mobile">
                        <img 
                            src={getIconUrl(a.symbol)} 
                            alt={a.symbol} 
                            className="asset-icon"
                            onError={(e) => handleImageError(e, a.symbol)}
                        />
                        <div>
                            <span className="asset-symbol">{a.symbol}</span>
                            <span className="asset-name">{a.name}</span>
                        </div>
                    </div>
                    <div className="asset-price-mobile">
                        <span className={a.priceColor || ''}>{a.price}</span>
                    </div>
                </div>
                
                <div className="card-body">
                    <div className="card-stat">
                        <span>Holdings</span>
                        <strong>{a.holdings}</strong>
                    </div>
                    <div className="card-stat">
                        <span>Total Value</span>
                        <strong>{a.value}</strong>
                    </div>
                </div>

                {/* Actions Container */}
                {/* We stop propagation on the container to catch any stray clicks around buttons */}
                <div className="card-actions" onClick={(e) => e.stopPropagation()}>
                    <button 
                        className="btn-buy" 
                        onClick={(e) => handleAction(e, onBuy, a)}
                    >
                        Buy
                    </button>
                    <button 
                        className="btn-sell" 
                        onClick={(e) => handleAction(e, onSell, a)}
                    >
                        Sell
                    </button>
                    {onEdit && (
                        <button 
                            className="btn-edit" 
                            onClick={(e) => handleAction(e, onEdit, a)}
                        >
                            Edit
                        </button>
                    )}
                </div>
            </div>
        ))}
      </div>
    </div>
  );
}

export default AssetTable;