import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Compass, MessageSquare, Users, FileOutput, MessageCircle } from 'lucide-react';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: Home },
    { name: 'Themes & Frustrations', path: '/themes', icon: Compass },
    { name: 'Reviews Browser', path: '/reviews', icon: MessageSquare },
    { name: 'User Segments', path: '/segments', icon: Users },
    { name: 'RAG Chatbot', path: '/chat', icon: MessageCircle },

  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Spotify Insights</h2>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink 
            key={item.path} 
            to={item.path}
            className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
          >
            <item.icon className="nav-icon" size={20} />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
