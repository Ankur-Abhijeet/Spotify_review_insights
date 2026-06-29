import React, { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';

const Header = () => {
  const { summary, usage, clearDataOnLoad, backendStatus, checkBackendStatus } = useAppStore();

  useEffect(() => {
    // Initial check
    checkBackendStatus();
    
    // Poll every 10 seconds
    const interval = setInterval(() => {
      checkBackendStatus();
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const tokenPct = Math.min((usage?.tokens_used / 500000) * 100, 100).toFixed(1);
  const reqPct = Math.min((usage?.requests_made / 14400) * 100, 100).toFixed(1);

  // Status Dot helper
  const getStatusColor = () => {
    if (backendStatus === 'online') return '#1ed760'; // Spotify green
    if (backendStatus === 'offline') return '#ef4444'; // Red
    return '#a1a1aa'; // Gray
  };

  const getStatusText = () => {
    if (backendStatus === 'online') return 'Connected';
    if (backendStatus === 'offline') return 'Offline / Waking up';
    return 'Checking status...';
  };

  return (
    <header className="header">
      <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h1>Overview</h1>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '0.4rem', 
          padding: '0.25rem 0.6rem', 
          background: 'rgba(255,255,255,0.03)', 
          borderRadius: '20px',
          border: '1px solid rgba(255,255,255,0.08)',
          fontSize: '0.75rem'
        }}>
          <span style={{ 
            width: '8px', 
            height: '8px', 
            borderRadius: '50%', 
            background: getStatusColor(),
            boxShadow: backendStatus === 'online' ? '0 0 8px #1ed760' : 'none'
          }} />
          <span style={{ color: 'var(--text-muted)' }}>{getStatusText()}</span>
        </div>
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
