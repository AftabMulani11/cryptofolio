import React from 'react';
const style = { background: 'var(--bg-card)', padding: '20px', borderRadius: '10px', flex: 1, minWidth: '200px', border: '1px solid var(--border-color)', boxShadow: 'var(--shadow)' };
export default function StatCard({ title, value, change, isPositive }) {
  return (
    <div style={style}>
      <h4 style={{margin:'0 0 10px 0', color:'var(--text-secondary)'}}>{title}</h4>
      <h2 style={{margin:'0 0 5px 0', color: 'var(--text-primary)'}}>{value}</h2>
      <span className={isPositive ? 'text-green' : 'text-red'}>{isPositive ? '▲' : '▼'} {change}</span>
    </div>
  );
}