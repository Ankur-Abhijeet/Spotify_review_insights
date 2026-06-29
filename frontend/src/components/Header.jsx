import React from 'react';
import { useAppStore } from '../store/useAppStore';

const Header = () => {
  const { summary, usage, clearDataOnLoad } = useAppStore();

  const tokenPct = Math.min((usage?.tokens_used / 500000) * 100, 100).toFixed(1);
  const reqPct = Math.min((usage?.requests_made / 14400) * 100, 100).toFixed(1);

  return (
    <header className="header">
      <div className="header-left">
        <h1>Overview</h1>
      </div>
      <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        
        {/* Action Buttons */}
        <button 
          onClick={async () => {
            if(window.confirm('Are you sure you want to delete all scraped data, RAG embeddings, and summary reports? This cannot be undone.')) {
              await clearDataOnLoad();
            }
          }}
          style={{ 
            padding: '0.5rem 1rem', 
            borderRadius: '8px', 
            background: 'rgba(239, 68, 68, 0.2)', 
            border: '1px solid var(--danger)', 
            color: 'var(--danger)', 
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: 'bold'
          }}>
          🗑️ Clear All Data
        </button>

        {/* Usage Tracker */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Daily Tokens (500K)</div>
            <div style={{ fontSize: '0.875rem', fontWeight: 'bold' }}>{usage?.tokens_used?.toLocaleString() || 0} <span style={{ color: 'var(--primary)', fontSize: '0.75rem' }}>({tokenPct}%)</span></div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Daily Requests (14.4K)</div>
            <div style={{ fontSize: '0.875rem', fontWeight: 'bold' }}>{usage?.requests_made?.toLocaleString() || 0} <span style={{ color: 'var(--primary)', fontSize: '0.75rem' }}>({reqPct}%)</span></div>
          </div>
        </div>

        {summary && (
          <div className="header-metrics">
            <span className="metric-chip highlight">
              <strong>Top Pain:</strong> {summary.top_pain_point}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
