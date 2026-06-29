import React, { useState, useRef, useEffect } from 'react';
import apiClient from '../api/client';
import { Send, User, Bot, AlertCircle } from 'lucide-react';

const Chat = () => {
  const [messages, setMessages] = useState([
    { role: 'bot', text: "Hello! I'm the Spotify Insights AI. Ask me questions about user frustrations, feature requests, or algorithm performance.", citations: [] }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef(null);

  const scrollToBottom = () => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsTyping(true);

    try {
      const res = await apiClient.post('/chat', { query: userMsg });
      setMessages(prev => [...prev, { role: 'bot', text: res.data.answer, citations: res.data.citations }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'bot', text: "I'm sorry, I couldn't connect to the insight database.", isError: true }]);
    }
    setIsTyping(false);
  };

  return (
    <div className="chat-container">
      <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
        
        {/* Header */}
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', background: 'rgba(0,0,0,0.2)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Bot color="var(--primary)" /> RAG Intelligence Chat
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Answers are strictly grounded in user reviews and community threads.
          </p>
        </div>

        {/* Messages Box */}
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', maxWidth: '80%' }}>
                {msg.role === 'bot' && <Bot size={20} color="var(--primary)" style={{ marginBottom: '0.5rem' }} />}
                
                <div className={`chat-bubble ${msg.role}`}>
                  {msg.isError && <AlertCircle size={16} style={{ display: 'inline', marginRight: '0.5rem', marginBottom: '-2px' }} />}
                  {msg.text}
                </div>
                
                {msg.role === 'user' && <User size={20} color="var(--text-muted)" style={{ marginBottom: '0.5rem' }} />}
              </div>

              {/* Citations Box */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="citations-box" style={{ alignSelf: 'flex-start', marginLeft: '32px', maxWidth: '70%' }}>
                  <strong style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-main)' }}>Sources Cited:</strong>
                  {msg.citations.map((c, idx) => (
                    <div key={idx} style={{ marginBottom: '0.5rem', paddingBottom: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <span className="badge neutral" style={{ marginRight: '0.5rem' }}>{c.tag}</span>
                      <em style={{ fontSize: '0.75rem' }}>"{c.text.substring(0, 100)}..."</em>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          
          {isTyping && (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
              <Bot size={20} color="var(--primary)" style={{ marginBottom: '0.5rem' }} />
              <div className="chat-bubble bot" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                <span style={{ fontSize: '0.875rem' }}>Synthesizing...</span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input Area */}
        <form className="chat-input-area" onSubmit={handleSend}>
          <input 
            type="text" 
            className="input-field" 
            placeholder="Ask about user sentiments, discovery flaws, etc..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
            style={{ fontSize: '1rem' }}
          />
          <button 
            type="submit" 
            className="btn-primary" 
            disabled={isTyping || !input.trim()}
            style={{ borderRadius: 'var(--radius-md)' }}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
