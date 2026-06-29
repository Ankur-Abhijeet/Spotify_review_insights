import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAppStore } from '../store/useAppStore';

const Layout = () => {
  const { fetchInsights } = useAppStore();

  useEffect(() => {
    const init = async () => {
      await fetchInsights();
    };
    init();
  }, [fetchInsights]);

  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-wrapper">
        <Header />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
