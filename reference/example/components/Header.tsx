
import React from 'react';
import { UserAvatar, ChevronDownIcon, SearchIcon, BellIcon, SettingsIcon, LockIcon } from '../constants';

const IconButton: React.FC<{ icon: React.ReactNode, hasBadge?: boolean, srText: string }> = ({ icon, hasBadge, srText }) => (
  <button className="p-2 rounded-full hover:bg-slate-700 relative text-gray-400 hover:text-gray-200">
    <span className="sr-only">{srText}</span>
    {icon}
    {hasBadge && <span className="absolute top-1 right-1.5 block h-2 w-2 rounded-full bg-red-500 ring-2 ring-slate-800" />}
  </button>
);

const Header: React.FC = () => {
  return (
    <header className="h-16 bg-slate-800/50 backdrop-blur-md border-b border-slate-700 flex items-center justify-between px-4 sm:px-6 lg:px-8 shrink-0">
      <div className="flex items-center">
        {/* Placeholder for potential breadcrumbs or page title */}
      </div>
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1 p-2 rounded-full bg-slate-700/50">
          <UserAvatar className="h-7 w-7 rounded-full" />
          <span className="text-sm font-medium text-gray-200 hidden sm:inline">Ryan997</span>
          <span className="text-xs bg-purple-600 text-white px-1.5 py-0.5 rounded-sm font-semibold hidden sm:inline">PRO</span>
          <ChevronDownIcon className="w-4 h-4 text-gray-400" />
        </div>
        
        <button className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-medium py-2 px-4 rounded-lg shadow-md hover:shadow-lg transition-all duration-150">
          <span>Deposit</span>
          <LockIcon className="w-3.5 h-3.5" />
        </button>

        <div className="h-6 w-px bg-slate-600"></div>

        <IconButton icon={<SearchIcon className="w-5 h-5" />} srText="Search" />
        <IconButton icon={<BellIcon className="w-5 h-5" />} hasBadge srText="Notifications" />
        <IconButton icon={<SettingsIcon className="w-5 h-5" />} srText="Settings" />
      </div>
    </header>
  );
};

export default Header;
