import React, { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { PlayCircle, Database, AlertCircle } from 'lucide-react';

const COLORS = ['#1ed760', '#3b82f6', '#f59e0b', '#ef4444', '#a1a1aa'];

// Helper component to render clean review items
const ReviewItem = ({ data }) => {
  const isForum = data.source === 'reddit' || data.source === 'spotify_community';
  
  if (isForum) {
    return (
      <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', borderLeft: '3px solid var(--primary)', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted)' }}>
            @{data.source} user • Thread
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{data.date}</span>
        </div>
        <p style={{ fontSize: '0.85rem', lineHeight: '1.4', whiteSpace: 'pre-wrap' }}>
          {data.body}
        </p>
        <div style={{ marginTop: '0.5rem', paddingLeft: '1rem', borderLeft: '2px solid rgba(255,255,255,0.1)' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>↳ [Scraped Thread Content]</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', marginBottom: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div>
          <span style={{ color: '#f59e0b', fontSize: '0.85rem' }}>
            {'★'.repeat(data.rating || 0)}{'☆'.repeat(5 - (data.rating || 0))}
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>({data.source})</span>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{data.date}</span>
      </div>
      <p style={{ fontSize: '0.85rem', lineHeight: '1.4' }}>{data.body}</p>
    </div>
  );
};

const Dashboard = () => {
  const { summary, themes, behaviors, repetitionCauses, segments, unmetNeeds, activeJobType, triggerPipeline, pipelinePreview, lastCompletedStep } = useAppStore();
  const [limits, setLimits] = useState({
    play_store: 2,
    app_store: 2,
    reddit: 2,
    spotify_community: 2
  });
  const [keywords, setKeywords] = useState("discovery, algorithm, recommendation, explore");
  const [aiLimit, setAiLimit] = useState(50);

  const handleTrigger = async (type) => {
    try {
      const parsedLimits = {
        play_store: parseInt(limits.play_store),
        app_store: parseInt(limits.app_store),
        reddit: parseInt(limits.reddit),
        spotify_community: parseInt(limits.spotify_community)
      };
      let payloadKeywords = keywords;
      if (type === 'preprocess') {
          payloadKeywords = keywords.split(',').map(k => k.trim()).filter(k => k);
      }

      const payload = {
        sources: ["all"],
        limits: parsedLimits,
        keywords: type === 'preprocess' ? payloadKeywords : undefined,
        limit: type === 'analyze' ? parseInt(aiLimit) : undefined
      };
      
      await triggerPipeline(type, payload);
    } catch (e) {
      alert("Failed to trigger " + type + ".");
    }
  };

  const topThemes = themes?.slice(0, 5).map(t => ({
    name: t.theme_name,
    pain: t.pain_score
  })) || [];

  return (
    <div className="dashboard">
      <h2 style={{ marginBottom: '2rem' }}>Intelligence Overview</h2>
      
      <div className="dashboard-grid" style={{ gridTemplateColumns: '2fr 1fr' }}>
        
        {/* Results Accordions (Left Side) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Step 1 Results */}
          <details className="glass-card accordion" open>
            <summary>
              <h3 style={{ display: 'inline-block', margin: 0 }}>Step 1: Scraped Data Results</h3>
            </summary>
            <div className="accordion-content">
              <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
                <strong>Total Reviews Scraped:</strong> {pipelinePreview?.scraped?.total || 0}
              </p>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Showing sample batch of 10 items to prevent UI lag.</p>
              {pipelinePreview?.scraped?.sample?.length > 0 && (
                <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                  {pipelinePreview.scraped.sample.map((item, i) => <ReviewItem key={i} data={item} />)}
                </div>
              )}
            </div>
          </details>

          {/* Step 2 Results */}
          <details className="glass-card accordion" open={lastCompletedStep >= 1}>
            <summary>
              <h3 style={{ display: 'inline-block', margin: 0 }}>Step 2: Preprocessed Data Results</h3>
            </summary>
            <div className="accordion-content">
              <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
                <strong>Filtered Target Reviews:</strong> {pipelinePreview?.preprocessed?.total || 0}
              </p>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Showing sample batch of 10 items.</p>
              {pipelinePreview?.preprocessed?.sample?.length > 0 && (
                <div style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                  {pipelinePreview.preprocessed.sample.map((item, i) => <ReviewItem key={i} data={item} />)}
                </div>
              )}
            </div>
          </details>

          {/* Step 3 Results */}
          <details className="glass-card accordion" open={lastCompletedStep >= 4}>
            <summary>
              <h3 style={{ display: 'inline-block', margin: 0 }}>Step 3/4: AI Analysis & Summary Results</h3>
            </summary>
            <div className="accordion-content">
              {summary ? (
                <>
                  <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '1.5rem', marginBottom: '1.5rem' }}>
                    <div className="glass-card" style={{ padding: '1rem' }}>
                      <h4 style={{ color: 'var(--text-muted)' }}>Analyzed Feedback</h4>
                      <p style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--primary)' }}>{summary.total_reviews}</p>
                    </div>
                    <div className="glass-card" style={{ padding: '1rem' }}>
                      <h4 style={{ color: 'var(--text-muted)' }}>Discovery Complaints</h4>
                      <p style={{ fontSize: '2rem', fontWeight: '700', color: '#f59e0b' }}>{summary.discovery_related_percentage}%</p>
                    </div>
                  </div>
                  
                  <div style={{ height: '300px' }}>
                    <h4 style={{ marginBottom: '1rem' }}>Top Pain Points</h4>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={topThemes} layout="vertical" margin={{ left: 50, right: 20, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                        <XAxis type="number" stroke="var(--text-muted)" />
                        <YAxis dataKey="name" type="category" stroke="var(--text-muted)" width={100} />
                        <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }} />
                        <Bar dataKey="pain" fill="var(--primary)" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  
                  <div style={{ marginTop: '3rem' }}>
                    <h4 style={{ marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>Strategic Questions Answered</h4>
                    
                    <div style={{ display: 'grid', gap: '1.5rem' }}>
                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>1. Why do users struggle to discover new music?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {(() => {
                            const frustrations = themes?.slice(0, 2).flatMap(t => t.top_frustrations).slice(0, 3) || [];
                            return frustrations.length > 0 
                              ? frustrations.map((f, i) => <li key={i}>{f}</li>)
                              : <li>No clear frustrations extracted yet.</li>;
                          })()}
                        </ul>
                      </div>

                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>2. What are the most common frustrations with recommendations?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {(() => {
                            const recFrustrations = themes?.filter(t => t.theme_name.toLowerCase().includes('recommend') || t.theme_name.toLowerCase().includes('algorithm'))
                              .flatMap(t => t.top_frustrations).slice(0, 3) || [];
                            return recFrustrations.length > 0 
                              ? recFrustrations.map((f, i) => <li key={i}>{f}</li>)
                              : <li>Not enough recommendation-specific data in this batch.</li>;
                          })()}
                        </ul>
                      </div>

                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>3. What listening behaviors are users trying to achieve?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {behaviors && behaviors.length > 0 ? behaviors.slice(0, 3).map((b, i) => (
                            <li key={i}><strong>{b.intent_archetype}:</strong> {b.sample_intents[0] || 'Various listening intents'}</li>
                          )) : <li>No distinct behaviors identified.</li>}
                        </ul>
                      </div>

                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>4. What causes users to repeatedly listen to the same content?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {repetitionCauses && repetitionCauses.length > 0 ? repetitionCauses.slice(0, 3).map((r, i) => (
                            <li key={i}>{r.repetition_trigger}</li>
                          )) : <li>No significant repetition causes found.</li>}
                        </ul>
                      </div>

                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>5. Which user segments experience different discovery challenges?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {segments && segments.length > 0 ? segments.slice(0, 3).map((s, i) => (
                            <li key={i}><strong>{s.user_segment}:</strong> Struggles with {Object.keys(s.top_barriers)[0] || 'general discovery'}</li>
                          )) : <li>No significant segmentation found.</li>}
                        </ul>
                      </div>

                      <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.02)' }}>
                        <h5 style={{ color: 'var(--primary)', marginBottom: '0.75rem' }}>6. What unmet needs emerge consistently across reviews?</h5>
                        <ul style={{ paddingLeft: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          {unmetNeeds && unmetNeeds.length > 0 ? unmetNeeds.slice(0, 3).map((n, i) => (
                            <li key={i}>{n.unmet_need}</li>
                          )) : <li>No unmet needs identified.</li>}
                        </ul>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <p style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>No AI Analysis available yet.</p>
              )}
            </div>
          </details>

        </div>

        {/* Pipeline Control */}
        <div className="glass-card">
          <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Database size={20} /> Pipeline Controls
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Step 1: Scrapers */}
            <div style={{ padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}>
              <div style={{ marginBottom: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Play Store Limit</label>
                  <input type="number" className="input-field" style={{ width: '100%', padding: '0.5rem' }} value={limits.play_store} onChange={(e) => setLimits({...limits, play_store: e.target.value})} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>App Store Limit</label>
                  <input type="number" className="input-field" style={{ width: '100%', padding: '0.5rem' }} value={limits.app_store} onChange={(e) => setLimits({...limits, app_store: e.target.value})} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Reddit Limit</label>
                  <input type="number" className="input-field" style={{ width: '100%', padding: '0.5rem' }} value={limits.reddit} onChange={(e) => setLimits({...limits, reddit: e.target.value})} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Community Limit</label>
                  <input type="number" className="input-field" style={{ width: '100%', padding: '0.5rem' }} value={limits.spotify_community} onChange={(e) => setLimits({...limits, spotify_community: e.target.value})} />
                </div>
              </div>
              <button className="btn-primary" style={{ width: '100%' }} onClick={() => handleTrigger('scrape')} disabled={activeJobType !== null}>
                {activeJobType === 'scrape' ? <span className="spinner" style={{width: 18, height: 18}} /> : <PlayCircle size={18} />} 1. Run Data Scrapers
              </button>
            </div>

            {/* Step 2: Preprocessor */}
            <div style={{ padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', opacity: lastCompletedStep < 1 ? 0.5 : 1 }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Keywords (Comma Separated)</label>
                <input type="text" className="input-field" style={{ width: '100%', padding: '0.5rem' }} placeholder="discovery, algorithm, etc." value={keywords} onChange={(e) => setKeywords(e.target.value)} disabled={lastCompletedStep < 1} />
              </div>
              <button className="btn-primary" style={{ width: '100%', background: '#8b5cf6' }} onClick={() => handleTrigger('preprocess')} disabled={activeJobType !== null || lastCompletedStep < 1}>
                {activeJobType === 'preprocess' ? <span className="spinner" style={{width: 18, height: 18}} /> : <PlayCircle size={18} />} 2. Run Preprocessor
              </button>
            </div>

            {/* Step 3: AI Annotation */}
            <div style={{ padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', opacity: lastCompletedStep < 2 ? 0.5 : 1 }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>LLM Input Limit (Rows)</label>
                <input type="number" className="input-field" style={{ width: '100%', padding: '0.5rem' }} value={aiLimit} onChange={(e) => setAiLimit(e.target.value)} disabled={lastCompletedStep < 2} />
              </div>
              <button className="btn-primary" style={{ width: '100%', background: 'var(--info)', color: '#fff' }} onClick={() => handleTrigger('analyze')} disabled={activeJobType !== null || lastCompletedStep < 2}>
                {activeJobType === 'analyze' ? <span className="spinner" style={{width: 18, height: 18}} /> : <PlayCircle size={18} />} 3. Run AI Annotation (LLM)
              </button>
              {lastCompletedStep >= 3 && <p style={{fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.5rem', textAlign: 'center'}}>✓ Annotation Complete</p>}
            </div>

            {/* Step 4: AI Summary Aggregation */}
            <div style={{ padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', opacity: lastCompletedStep < 3 ? 0.5 : 1 }}>
              <button className="btn-primary" style={{ width: '100%', background: '#f59e0b', color: '#fff' }} onClick={() => handleTrigger('aggregate')} disabled={activeJobType !== null || lastCompletedStep < 3}>
                {activeJobType === 'aggregate' ? <span className="spinner" style={{width: 18, height: 18}} /> : <PlayCircle size={18} />} 4. Generate AI Summary
              </button>
              {lastCompletedStep >= 4 && <p style={{fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.5rem', textAlign: 'center'}}>✓ Dashboard Updated</p>}
            </div>

            {/* Step 5: Chatbot Database Sync */}
            <div style={{ padding: '1rem', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', opacity: lastCompletedStep < 3 ? 0.5 : 1 }}>
              <button className="btn-primary" style={{ width: '100%', background: '#10b981', color: '#fff' }} onClick={() => handleTrigger('index-chat')} disabled={activeJobType !== null || lastCompletedStep < 3}>
                {activeJobType === 'index-chat' ? <span className="spinner" style={{width: 18, height: 18}} /> : <Database size={18} />} 5. Sync Chatbot Database
              </button>
              {lastCompletedStep >= 5 && <p style={{fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.5rem', textAlign: 'center'}}>✓ Database Synced</p>}
            </div>

          </div>

          {activeJobType && (
            <div style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px' }}>
              <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
                <span className="spinner" style={{width: 16, height: 16}} />
                Status: <strong>Running Step synchronously...</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
