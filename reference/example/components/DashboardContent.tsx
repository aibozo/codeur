
import React, { useState } from 'react';
import AssetCard from './AssetCard';
import ActiveStakingInfo from './ActiveStakingInfo';
import LiquidStakingPanel from './LiquidStakingPanel';
import { TOP_STAKING_ASSETS_DATA, ChevronDownIcon } from '../constants';

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
        <ChevronDownIcon className="w-3.5 h-3.5" />
    </button>
);


const DashboardContent: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'staking' | 'stablecoin'>('staking');

  return (
    <div className="space-y-6 lg:space-y-8">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center space-y-4 lg:space-y-0">
        <div className="flex items-center space-x-2 bg-slate-800 p-1 rounded-xl">
          <TabButton label="Staking" isActive={activeTab === 'staking'} onClick={() => setActiveTab('staking')} />
          <TabButton label="Stablecoin" isActive={activeTab === 'stablecoin'} onClick={() => setActiveTab('stablecoin')} />
        </div>
        {/* Placeholder for other filters if needed */}
      </div>

      {activeTab === 'staking' && (
        <div className="space-y-6 lg:space-y-8">
          <div>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
                <h2 className="text-xl sm:text-2xl font-semibold text-white">Top Staking Assets</h2>
                <div className="flex items-center space-x-2 mt-2 sm:mt-0">
                    <span className="text-sm text-gray-400 mr-2 hidden md:inline">Recommended coins for 24 hours</span>
                    <span className="text-xs bg-purple-600 text-white px-2 py-1 rounded-md">3 Assets</span>
                    <div className="hidden md:flex items-center space-x-2">
                        <FilterButton label="24H"/>
                        <FilterButton label="Proof of Stake"/>
                        <FilterButton label="Desc"/>
                    </div>
                </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
              {TOP_STAKING_ASSETS_DATA.map(asset => (
                <AssetCard key={asset.id} asset={asset} />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 lg:gap-8">
            <div className="xl:col-span-2">
              <ActiveStakingInfo />
            </div>
            <div className="xl:col-span-1">
              <LiquidStakingPanel />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'stablecoin' && (
        <div className="text-center py-10">
          <h2 className="text-2xl font-semibold text-white">Stablecoin Assets</h2>
          <p className="text-gray-400 mt-2">Content for Stablecoin tab will be displayed here.</p>
          {/* Placeholder content for Stablecoin tab */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1,2,3].map(i => (
                <div key={i} className="bg-slate-800 p-6 rounded-xl shadow-lg h-48 flex items-center justify-center">
                    <p className="text-gray-500">Stablecoin Asset {i}</p>
                </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardContent;
