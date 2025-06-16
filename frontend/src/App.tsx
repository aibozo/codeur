import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardContent from './components/DashboardContent';
import BuildPage from './components/BuildPage';

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
              <Route path="/build" element={<BuildPage />} />
              <Route path="/agents" element={<div className="text-white text-2xl">Agents Page</div>} />
              <Route path="/metrics" element={<div className="text-white text-2xl">Metrics Page</div>} />
              <Route path="/logs" element={<div className="text-white text-2xl">Logs Page</div>} />
              <Route path="/settings" element={<div className="text-white text-2xl">Settings Page</div>} />
            </Routes>
          </main>
        </div>
      </div>
    </HashRouter>
  );
};

export default App;