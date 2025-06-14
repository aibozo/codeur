
import React from 'react';
import { NavLink } from 'react-router-dom';
import { NavItemType, ActiveAssetType } from '../types';
import { StakentLogoIcon, NAV_ITEMS, ACTIVE_ASSETS, ChevronUpIcon, ChevronDownIcon, PowerIcon } from '../constants';

interface NavItemProps {
  item: NavItemType;
}

const NavItem: React.FC<NavItemProps> = ({ item }) => {
  const baseClasses = "flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-700 transition-colors duration-150";
  const activeClasses = "bg-slate-700 text-white";
  const inactiveClasses = "text-gray-400 hover:text-white";

  return (
    <NavLink
      to={item.path}
      className={({ isActive }) => `${baseClasses} ${isActive ? activeClasses : inactiveClasses}`}
    >
      {item.icon}
      <span className="flex-1 text-sm font-medium">{item.name}</span>
      {item.beta && <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded-md">Beta</span>}
      {item.count && <span className="text-xs bg-purple-600 text-white px-1.5 py-0.5 rounded-full">{item.count}</span>}
    </NavLink>
  );
};

interface ActiveAssetItemProps {
  asset: ActiveAssetType;
}

const ActiveAssetItem: React.FC<ActiveAssetItemProps> = ({ asset }) => (
  <div className="flex items-center space-x-2 p-2 hover:bg-slate-700 rounded-md cursor-pointer">
    <div className={`w-5 h-5 rounded-sm flex items-center justify-center text-white text-xs ${asset.bgColorClass}`}>
      {React.cloneElement(asset.icon as React.ReactElement, { className: "w-3 h-3" })}
    </div>
    <span className="text-xs text-gray-300 flex-1">{asset.name}</span>
    <span className="text-xs text-gray-400">{asset.amount}</span>
  </div>
);

const Sidebar: React.FC = () => {
  const [activeStakingOpen, setActiveStakingOpen] = React.useState(true);

  return (
    <div className="w-64 bg-slate-800 p-4 flex flex-col border-r border-slate-700 space-y-4 h-full overflow-y-auto">
      <div className="px-2 mb-4">
        <StakentLogoIcon />
        <p className="text-xs text-gray-500 mt-1">Top Staking Assets</p>
      </div>

      <nav className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.name} item={item} />
        ))}
      </nav>

      <div className="mt-auto pt-4 space-y-2 border-t border-slate-700">
        <button 
          onClick={() => setActiveStakingOpen(!activeStakingOpen)}
          className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-slate-700 rounded-lg"
        >
          <span>Active Staking</span>
          <div className="flex items-center">
            <span className="text-xs bg-purple-600 text-white px-1.5 py-0.5 rounded-full mr-2">{ACTIVE_ASSETS.length}</span>
            {activeStakingOpen ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
          </div>
        </button>
        {activeStakingOpen && (
          <div className="space-y-1 pl-2">
            {ACTIVE_ASSETS.map((asset) => (
              <ActiveAssetItem key={asset.name} asset={asset} />
            ))}
          </div>
        )}
      </div>
      
      <div className="mt-4 p-3 bg-slate-700/50 rounded-lg">
          <button className="w-full flex items-center justify-center space-x-2 text-sm text-purple-400 hover:text-purple-300 font-medium py-2 px-3 rounded-md bg-purple-600/20 hover:bg-purple-600/30 transition-colors">
              <PowerIcon className="w-4 h-4"/>
              <span>Activate Super</span>
          </button>
          <p className="text-xs text-gray-400 mt-1.5 text-center">Unlock all features on Stakent</p>
      </div>
    </div>
  );
};

export default Sidebar;
