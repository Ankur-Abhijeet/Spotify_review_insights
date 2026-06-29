import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';

const Reviews = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  // Filters
  const [segment, setSegment] = useState('');
  const [discoveryOnly, setDiscoveryOnly] = useState(false);

  const fetchReviews = async () => {
    setLoading(true);
    try {
      let url = `/reviews?page=${page}&size=15`;
      if (segment) url += `&segment=${segment}`;
      if (discoveryOnly) url += `&discovery_only=true`;
      
      const res = await apiClient.get(url);
      setData(res.data.data);
      setTotalPages(res.data.total_pages);
      setTotalRecords(res.data.total);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchReviews();
  }, [page, segment, discoveryOnly]);

  return (
    <div className="reviews-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Review Browser</h2>
        <span className="badge neutral">Total Found: {totalRecords}</span>
      </div>

      <div className="dashboard-grid" style={{ gridTemplateColumns: '250px 1fr' }}>
        
        {/* Filter Sidebar */}
        <div className="glass-card" style={{ alignSelf: 'start', position: 'sticky', top: '100px' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <Filter size={18} /> Filters
          </h3>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>User Segment</label>
            <select className="input-field" style={{ width: '100%' }} value={segment} onChange={e => { setSegment(e.target.value); setPage(1); }}>
              <option value="">All Segments</option>
              <option value="power_user">Power User</option>
              <option value="casual">Casual</option>
              <option value="new_user">New User</option>
              <option value="churned">Churned</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input 
              type="checkbox" 
              id="discovery" 
              checked={discoveryOnly} 
              onChange={e => { setDiscoveryOnly(e.target.checked); setPage(1); }}
            />
            <label htmlFor="discovery" style={{ fontSize: '0.875rem' }}>Discovery Related Only</label>
          </div>
        </div>

        {/* Data Table */}
        <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead style={{ background: 'rgba(255,255,255,0.02)' }}>
                <tr>
                  <th>ID</th>
                  <th>Segment</th>
                  <th>Intent</th>
                  <th>Top Theme</th>
                  <th>Sentiment</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="5" style={{ textAlign: 'center', padding: '3rem' }}><span className="spinner" style={{ margin: '0 auto' }}/></td></tr>
                ) : data.length === 0 ? (
                  <tr><td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No reviews match your filters.</td></tr>
                ) : (
                  data.map(r => (
                    <tr key={r.review_id}>
                      <td style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>{r.review_id.substring(0,8)}</td>
                      <td>
                        <span className={`badge neutral`}>{r.user_segment}</span>
                      </td>
                      <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {r.user_intent}
                      </td>
                      <td>{r.themes[0]?.theme_name || 'N/A'}</td>
                      <td>
                        {r.themes[0] && (
                          <span className={`badge ${r.themes[0].sentiment === 'positive' ? 'positive' : r.themes[0].sentiment === 'negative' ? 'negative' : 'neutral'}`}>
                            {r.themes[0].sentiment}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          
          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.5rem', borderTop: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
            <button 
              className="btn-primary" 
              style={{ padding: '0.5rem', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-main)' }}
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              <ChevronLeft size={18} />
            </button>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Page {page} of {totalPages}
            </span>
            <button 
              className="btn-primary" 
              style={{ padding: '0.5rem', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-main)' }}
              disabled={page === totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Reviews;
