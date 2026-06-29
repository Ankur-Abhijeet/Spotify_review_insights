import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Themes from './pages/Themes';
import Reviews from './pages/Reviews';
import Segments from './pages/Segments';
import Chat from './pages/Chat';


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="themes" element={<Themes />} />
          <Route path="reviews" element={<Reviews />} />
          <Route path="segments" element={<Segments />} />
          <Route path="chat" element={<Chat />} />

        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
