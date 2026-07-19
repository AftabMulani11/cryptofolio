import React from 'react';
import { NavLink } from 'react-router-dom';
import '../styles/Sidebar.css';

const Sidebar = ({ onLogout, isCollapsed, toggleSidebar }) => {
  
  // Define menu items with explicit paths
  const menuItems = [
    { id: 'dashboard', path: '/dashboard', label: 'Dashboard', icon: '📊', end: true },
    { id: 'portfolio', path: '/dashboard/portfolio', label: 'Portfolio', icon: '💼', end: false },
    { id: 'transactions', path: '/dashboard/transactions', label: 'Transactions', icon: '📝', end: false },
    { id: 'coins', path: '/dashboard/coins', label: 'Coins', icon: '🪙', end: false },
  ];

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo-container">
            {!isCollapsed && <div className="logo-full"><span className="logo-icon">⚡</span><span className="logo-text">CryptoFolio</span></div>}
        </div>
        <button className="header-toggle-btn" onClick={toggleSidebar}>{isCollapsed ? '☰' : '‹'}</button>
      </div>
      
      <div className="menu-container">
        <div className="menu-group">
          {!isCollapsed && <span className="menu-title">MENU</span>}
          <ul className="nav-links">
            {menuItems.map(item => (
                <li key={item.id}>
                    <NavLink 
                        to={item.path} 
                        end={item.end}
                        className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}
                    >
                        <span className="icon">{item.icon}</span>
                        {!isCollapsed && <span className="link-text">{item.label}</span>}
                    </NavLink>
                </li>
            ))}
          </ul>
        </div>
      </div>
      
      <div className="sidebar-footer">
        <button className="logout-btn" onClick={onLogout}>
            <span className="icon">🚪</span>
            {!isCollapsed && <span className="link-text">Logout</span>}
        </button>
      </div>
    </div>
  );
};
export default Sidebar;