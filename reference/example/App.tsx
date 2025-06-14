
import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardContent from './components/DashboardContent';
// Import other page components if you create more routes
// import AssetsPage from './pages/AssetsPage'; 

const App: React.FC = () => {
  return (
    <HashRouter>
      <div className="flex h-screen bg-slate-900 text-gray-300 overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-x-hidden overflow-y-auto bg-slate-900 p-4 sm:p-6 lg:p-8">
            <Routes>
              <Route path="/" element={<DashboardContent />} />
              {/* Define other routes here if needed */}
              {/* <Route path="/assets" element={<AssetsPage />} /> */}
              {/* For other routes, you can create simple placeholder components */}
              <Route path="/assets" element={<div className="text-white text-2xl">Assets Page (Placeholder)</div>} />
              <Route path="/providers" element={<div className="text-white text-2xl">Staking Providers Page (Placeholder)</div>} />
              <Route path="/calculator" element={<div className="text-white text-2xl">Staking Calculator Page (Placeholder)</div>} />
              <Route path="/api" element={<div className="text-white text-2xl">Data API Page (Placeholder)</div>} />
              <Route path="/liquid-staking" element={<div className="text-white text-2xl">Liquid Staking Page (Placeholder)</div>} />
            </Routes>
          </main>
        </div>
      </div>
    </HashRouter>
  );
};

export default App;
