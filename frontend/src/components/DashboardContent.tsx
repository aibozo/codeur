import React, { useState } from 'react';
import AgentCard from './AgentCard';
import MetricsOverview from './MetricsOverview';
import PerformanceChart from './PerformanceChart';
import SystemStatus from './SystemStatus';
import { ChevronDown } from 'lucide-react';

const TabButton: React.FC<{ label: string; isActive: boolean; onClick: () => void }> = ({ label, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150
      ${isActive ? 'bg-slate-700 text-white' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'}`}
  >
    {label}
  </button>
);

const FilterButton: React.FC<{ label: string }> = ({ label }) => (
  <button className="flex items-center space-x-1.5 text-xs text-gray-300 bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-md">
    <span>{label}</span>
    <ChevronDown className="w-3.5 h-3.5" />
  </button>
);

const DashboardContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'performance'>('overview');

  return (
    <div className="space-y-6 lg:space-y-8">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
        <div className="flex items-center space-x-2 bg-slate-800 p-1 rounded-xl">
          <TabButton label="Overview" isActive={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
          <TabButton label="Performance" isActive={activeTab === 'performance'} onClick={() => setActiveTab('performance')} />
        </div>
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6 lg:space-y-8">
          {/* Metrics Overview Section */}
          <div>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
              <h2 className="text-xl sm:text-2xl font-semibold text-white">System Overview</h2>
              <div className="flex items-center space-x-2 mt-2 sm:mt-0">
                <span className="text-sm text-gray-400 mr-2 hidden md:inline">Real-time metrics</span>
                <span className="text-xs bg-purple-600 text-white px-2 py-1 rounded-md">Live</span>
                <div className="hidden md:flex items-center space-x-2">
                  <FilterButton label="24H" />
                  <FilterButton label="All Agents" />
                  <FilterButton label="Sort" />
                </div>
              </div>
            </div>
            <MetricsOverview />
          </div>

          {/* Active Agents Section - Grid Layout */}
          <div>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
              <h2 className="text-xl sm:text-2xl font-semibold text-white">Active Agents</h2>
              <div className="flex items-center space-x-2 mt-2 sm:mt-0">
                <span className="text-xs bg-purple-600 text-white px-2 py-1 rounded-md">6 Agents</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
              <AgentCard 
                name="Research Agent" 
                status="active" 
                tasks={156} 
                model="claude-3.5"
                metrics={{ accuracy: "98.5%", speed: "245ms" }}
              />
              <AgentCard 
                name="Code Agent" 
                status="active" 
                tasks={89}
                model="gpt-4"
                metrics={{ accuracy: "97.2%", speed: "312ms" }}
              />
              <AgentCard 
                name="Analysis Agent" 
                status="idle" 
                tasks={45}
                model="claude-3.5"
                metrics={{ accuracy: "99.1%", speed: "189ms" }}
              />
              <AgentCard 
                name="Testing Agent" 
                status="active" 
                tasks={67}
                model="gpt-4"
                metrics={{ accuracy: "96.8%", speed: "423ms" }}
              />
              <AgentCard 
                name="Documentation Agent" 
                status="idle" 
                tasks={23}
                model="claude-3.5"
                metrics={{ accuracy: "99.5%", speed: "156ms" }}
              />
              <AgentCard 
                name="Review Agent" 
                status="active" 
                tasks={134}
                model="gpt-4"
                metrics={{ accuracy: "97.9%", speed: "287ms" }}
              />
            </div>
          </div>

          {/* Performance Chart and System Status - 2/3 + 1/3 Layout */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 lg:gap-8">
            <div className="xl:col-span-2">
              <PerformanceChart />
            </div>
            <div className="xl:col-span-1">
              <SystemStatus />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="text-center py-10">
          <h2 className="text-2xl font-semibold text-white">Performance Analytics</h2>
          <p className="text-gray-400 mt-2">Detailed performance metrics coming soon.</p>
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-slate-800 p-6 rounded-xl shadow-lg h-48 flex items-center justify-center">
                <p className="text-gray-500">Performance Metric {i}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardContent;