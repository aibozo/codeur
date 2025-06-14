
import React from 'react';
import { StakentLogoIcon, LockIcon } from '../constants'; // Assuming StakentLogo is available

const LiquidStakingPanel: React.FC = () => {
  return (
    <div className="bg-gradient-to-br from-slate-800 via-slate-800 to-purple-900/30 p-6 rounded-xl shadow-xl h-full flex flex-col">
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center space-x-2">
            <StakentLogoIcon className="h-6"/>
            <h3 className="text-lg font-semibold text-white">Liquid Staking Portfolio</h3>
        </div>
        <span className="text-xs bg-purple-600 text-white px-2 py-1 rounded-full font-semibold">New</span>
      </div>
      <p className="text-sm text-gray-400 mb-6">
        An all-in-one portfolio that helps you make smarter investments into Ethereum Liquid Staking.
      </p>
      
      {/* Placeholder for the subtle background graphic if needed */}
      <div className="relative flex-grow flex flex-col justify-end items-center mb-6">
        {/* Shooting star SVG - simplified */}
        <svg width="100" height="60" viewBox="0 0 100 60" className="absolute top-0 right-0 opacity-30 -mr-8 -mt-4 transform rotate-12" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M85.7303 6.22911C84.0386 5.61903 82.2595 5.75333 80.709 6.59079L5.3533 46.1955C3.80288 47.033 2.82588 48.5524 2.70136 50.211C2.57685 51.8696 3.32486 53.4795 4.70014 54.453L5.80877 55.2259C7.18405 56.1994 8.95991 56.3989 10.5103 55.5615L85.866 15.9567C87.4164 15.1193 88.3934 13.5999 88.5179 11.9413C88.6425 10.2827 87.8945 8.67278 86.5192 7.70043L85.7303 6.22911Z" fill="url(#paint0_linear_liquid_panel)"/>
            <defs>
            <linearGradient id="paint0_linear_liquid_panel" x1="45.6096" y1="5.12411" x2="45.6096" y2="56.3009" gradientUnits="userSpaceOnUse">
            <stop stopColor="white" stopOpacity="0.5"/>
            <stop offset="1" stopColor="white" stopOpacity="0"/>
            </linearGradient>
            </defs>
        </svg>

      </div>

      <button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md hover:shadow-lg transition-all duration-150 mb-3 text-sm">
        Connect with Wallet
      </button>
      <button className="w-full flex items-center justify-center space-x-2 bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white font-medium py-3 px-4 rounded-lg transition-colors text-sm">
        <span>Enter a Wallet Address</span>
        <LockIcon className="w-4 h-4 text-gray-400" />
      </button>
    </div>
  );
};

export default LiquidStakingPanel;
