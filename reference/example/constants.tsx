
import React from 'react';
import { TopAsset, ActiveAssetType, NavItemType, ChartDataItem } from './types';

// Generic Icons
export const ChevronDownIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={className}>
    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.23 8.27a.75.75 0 01.02-1.06z" clipRule="evenodd" />
  </svg>
);

export const ChevronRightIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={className}>
    <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.06 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
  </svg>
);

export const StakentLogoIcon: React.FC<{className?: string}> = ({className = "h-8 w-auto"}) => (
 <svg className={className} width="100" height="28" viewBox="0 0 100 28" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12.7445 22.8805L7.02734 27.0002V1.00024L12.7445 5.12001V22.8805Z" fill="url(#paint0_linear_1_2)"/>
    <path d="M0.000137329 5.12V22.8805L5.71727 27.0002V1.00024L0.000137329 5.12Z" fill="url(#paint1_linear_1_2)"/>
    <path d="M22.0833 7.84619C21.3542 7.21157 20.375 6.94235 19.3438 6.94235C16.5104 6.94235 14.25 9.07696 14.25 12.0308C14.25 13.4308 14.7604 14.7116 15.6042 15.6693C16.1979 16.3231 16.9167 16.8231 17.7188 17.1462L17.5104 17.3077H13.5V20.1077H22.75V17.6154C22.75 17.0769 22.4792 16.6 22.0417 16.2769C21.1458 15.6616 20.5104 14.7693 20.2188 13.7539C20.4792 13.7847 20.7396 13.8 21C21.6875 13.8 22.3333 13.6385 22.9063 13.3308L23.5104 15.3539H26.3438L24.6042 10.3616C23.8646 8.87696 23.0104 8.28465 22.0833 7.84619ZM20.0104 10.5539C20.0104 10.0308 19.7188 9.69235 19.2292 9.69235C18.7813 9.69235 18.5 10.0154 18.5 10.5539V11.5385C18.8438 11.2308 19.2604 11.0539 19.75 11.0539C19.8854 11.0539 20.0104 11.0693 20.0104 10.5539Z" fill="white"/>
    <path d="M36.1039 13.444C36.1039 10.4286 33.9164 8.12109 30.9997 8.12109C28.0831 8.12109 25.8956 10.4286 25.8956 13.444C25.8956 16.4593 28.0831 18.7668 30.9997 18.7668C33.9164 18.7668 36.1039 16.4593 36.1039 13.444ZM31.8122 13.444C31.8122 14.5286 31.4269 15.5211 30.9997 15.5211C30.5726 15.5211 30.1872 14.5286 30.1872 13.444C30.1872 12.3593 30.5726 11.3668 30.9997 11.3668C31.4269 11.3668 31.8122 12.3593 31.8122 13.444Z" fill="white"/>
    <path d="M38.8543 8.36118H41.5001L44.0314 13.6537L46.5626 8.36118H49.1147L45.3439 16.0359V20.0441H42.7918V16.0359L38.8543 8.36118Z" fill="white"/>
    <path d="M57.9708 11.3804C57.9708 9.67389 57.3458 8.65389 55.4853 8.18833C55.0853 8.08098 54.6708 8.02118 54.2385 8.02118C52.6109 8.02118 51.5276 8.84618 51.0182 9.77118L51.3109 8.36118H48.8182V20.0441H51.3109V13.8039C51.3109 12.1939 52.0958 11.0804 53.8682 11.0804C54.2235 11.0804 54.4853 11.1383 54.6708 11.2039C55.2235 11.3804 55.4853 11.8304 55.4853 12.5159V20.0441H57.9708V11.3804Z" fill="white"/>
    <path d="M66.4262 13.444C66.4262 10.4286 64.2387 8.12109 61.322 8.12109C58.4053 8.12109 56.2178 10.4286 56.2178 13.444C56.2178 16.4593 58.4053 18.7668 61.322 18.7668C64.2387 18.7668 66.4262 16.4593 66.4262 13.444ZM62.1345 13.444C62.1345 14.5286 61.7491 15.5211 61.322 15.5211C60.8948 15.5211 60.5095 14.5286 60.5095 13.444C60.5095 12.3593 60.8948 11.3668 61.322 11.3668C61.7491 11.3668 62.1345 12.3593 62.1345 13.444Z" fill="white"/>
    <path d="M74.8816 8.36118H67.4124V20.0441H74.7124V17.7512H69.9049V14.936H74.3316V12.6432H69.9049V10.6537H74.8816V8.36118Z" fill="white"/>
    <path d="M84.7214 13.8039L84.8045 13.7804C84.0978 11.7583 83.1845 11.0804 81.3978 11.0804C79.4311 11.0804 78.0789 12.3326 78.0789 13.444C78.0789 14.5552 79.4311 15.8073 81.3978 15.8073C82.4978 15.8073 83.2826 15.4219 83.8978 14.7883L83.6361 16.2959C83.2195 16.8941 82.4345 17.2039 81.6045 17.2039C79.8322 17.2039 78.3639 16.4191 77.5337 15.0089C76.8437 13.7804 76.8437 12.597 77.7124 11.597C78.6803 10.4286 80.0903 9.77118 81.6045 9.77118C83.3322 9.77118 84.7124 10.6844 85.3816 12.217L84.7214 13.8039Z" fill="white"/>
    <path d="M99.6438 8.98833C99.2585 8.56118 98.7178 8.32892 98.1322 8.13618C97.6822 7.99966 97.1045 7.93618 96.4893 7.93618C95.7322 7.93618 94.9472 8.16844 94.3126 8.5956C93.678 9.02275 93.3607 9.65736 93.3607 10.377C93.3607 11.3347 93.9545 12.0124 95.0264 12.2883L96.8139 12.7539C97.9139 13.0298 98.4233 13.5612 98.4233 14.3462C98.4233 15.147 97.8107 15.8073 96.6423 15.8073C95.5187 15.8073 94.7062 15.2601 94.3107 14.6739L94.1345 14.7362L93.0004 16.6883C93.635 17.2197 94.5033 17.5124 95.4483 17.5883C95.5745 17.5956 95.6987 17.6002 95.8226 17.6002C96.5972 17.6002 97.3545 17.382 98.0148 16.9966C98.675 16.6112 99.0438 15.992 99.0438 15.2197C99.0438 14.1997 98.4091 13.432 97.1045 13.1245L95.6045 12.7539C94.4187 12.4462 93.9393 11.8304 93.9393 11.1304C93.9393 10.5989 94.247 10.1562 94.7564 9.87118C95.2658 10.1562 95.9658 10.377 96.6558 10.377C97.1789 10.377 97.6445 10.2154 98.0004 9.92118L98.4233 8.36118L99.6438 8.98833Z" fill="white"/>
    <defs>
    <linearGradient id="paint0_linear_1_2" x1="9.88591" y1="0.923056" x2="9.88591" y2="27.0774" gradientUnits="userSpaceOnUse">
    <stop stopColor="#BE40FF"/>
    <stop offset="1" stopColor="#6A3BFF"/>
    </linearGradient>
    <linearGradient id="paint1_linear_1_2" x1="2.8587" y1="0.923056" x2="2.8587" y2="27.0774" gradientUnits="userSpaceOnUse">
    <stop stopColor="#BE40FF"/>
    <stop offset="1" stopColor="#6A3BFF"/>
    </linearGradient>
    </defs>
</svg>
);

export const DashboardIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25A2.25 2.25 0 0113.5 8.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
  </svg>
);

export const AssetsIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h6m3-3.75l3 3m0 0l3-3m-3 3V1.5m6 5.25l3 3m0 0l3-3m-3 3V1.5" />
  </svg>
);

export const StakingProvidersIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5zm0 9.75h2.25A2.25 2.25 0 0010.5 18v-2.25a2.25 2.25 0 00-2.25-2.25H6a2.25 2.25 0 00-2.25 2.25V18A2.25 2.25 0 006 20.25zm9.75-9.75H18a2.25 2.25 0 002.25-2.25V6A2.25 2.25 0 0018 3.75h-2.25A2.25 2.25 0 0013.5 6v2.25a2.25 2.25 0 002.25 2.25z" />
  </svg>
);

export const StakingCalculatorIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V13.5zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V18zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V13.5zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V18zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zm0 2.25h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V18zm2.498-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zM8.25 6h7.5v2.25h-7.5V6zM12 2.25c-1.892 0-3.64.766-4.908 2.034A7.458 7.458 0 004.57 9.516a7.47 7.47 0 00-1.096 4.908 7.458 7.458 0 002.034 4.908A7.458 7.458 0 009.516 21.43a7.47 7.47 0 004.908 1.096 7.458 7.458 0 004.908-2.034 7.458 7.458 0 002.034-4.908 7.47 7.47 0 00-1.096-4.908A7.458 7.458 0 0016.484 4.284 7.5 7.5 0 0012 2.25z" />
  </svg>
);

export const DataApiIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
  </svg>
);

export const LiquidStakingIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.125-.504 1.125-1.125V14.25m-17.25 4.5H9m9-4.5H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125V6.75m17.25-3H9M9 3.75V1.5M12 3.75V1.5m-3 2.25V1.5m12 2.25V1.5" />
  </svg>
);

export const ChevronUpIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className={className}>
    <path fillRule="evenodd" d="M14.77 12.79a.75.75 0 01-1.06-.02L10 8.06l-3.71 3.71a.75.75 0 11-1.06-1.06l4.25-4.25a.75.75 0 011.06 0l4.25 4.25a.75.75 0 01-.02 1.06z" clipRule="evenodd" />
  </svg>
);


export const SearchIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
  </svg>
);

export const BellIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
  </svg>
);

export const SettingsIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-1.003 1.11-.962a8.969 8.969 0 013.842 0c.55.04 1.02.42 1.11.962l.096.568c.25.049.492.115.726.202.493.185.958.441 1.374.776.415.335.792.747 1.108 1.192.316.445.578.932.784 1.451a8.969 8.969 0 010 3.842c-.206.519-.468 1.006-.784 1.451-.316.445-.693.857-1.108 1.192-.416.335-.88.591-1.374.776-.234.087-.476.153-.726.202l-.097.568c-.09.542-.56 1.003-1.11.962a8.969 8.969 0 01-3.842 0c-.55-.04-1.02-.42-1.11-.962l-.096-.568c-.25-.049-.492-.115-.726-.202-.493-.185-.958-.441-1.374-.776a7.509 7.509 0 01-1.108-1.192c-.316-.445-.578-.932-.784-1.451a8.969 8.969 0 010-3.842c.206-.519.468-1.006.784-1.451.316-.445.693-.857 1.108-1.192.416-.335.88-.591 1.374-.776.234-.087.476-.153.726-.202l.097-.568zM12 6.75a5.25 5.25 0 100 10.5 5.25 5.25 0 000-10.5z" />
  </svg>
);

export const LockIcon: React.FC<{className?: string}> = ({ className = "w-4 h-4" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
  </svg>
);

export const UserAvatar: React.FC<{className?: string}> = ({className = "h-8 w-8 rounded-full"}) => (
  <img className={className} src="https://picsum.photos/seed/ryancrawford/40/40" alt="User Avatar" />
);

// Coin Icons (Simple Placeholders)
export const EthereumIcon: React.FC<{className?: string}> = ({ className = "w-8 h-8" }) => (
  <div className={`flex items-center justify-center rounded-lg bg-indigo-500 text-white ${className}`}>ETH</div>
);
export const BnbIcon: React.FC<{className?: string}> = ({ className = "w-8 h-8" }) => (
  <div className={`flex items-center justify-center rounded-lg bg-yellow-500 text-black ${className}`}>BNB</div>
);
export const PolygonIcon: React.FC<{className?: string}> = ({ className = "w-8 h-8" }) => (
  <div className={`flex items-center justify-center rounded-lg bg-purple-500 text-white ${className}`}>MATIC</div>
);
export const AvalancheIcon: React.FC<{className?: string}> = ({ className = "w-6 h-6" }) => (
  <div className={`flex items-center justify-center rounded-full bg-red-500 text-white ${className}`}>AVAX</div>
);

export const ExternalLinkIcon: React.FC<{className?: string}> = ({ className = "w-4 h-4" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
  </svg>
);

export const ChartBarIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
</svg>
);

export const RefreshIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
</svg>
);

export const MenuIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
 <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
</svg>
);

export const PowerIcon: React.FC<{className?: string}> = ({ className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={className}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
  </svg>
);


// Mock Data
export const NAV_ITEMS: NavItemType[] = [
  { name: "Dashboard", icon: <DashboardIcon />, path: "/", active: true },
  { name: "Assets", icon: <AssetsIcon />, path: "/assets" },
  { name: "Staking Providers", icon: <StakingProvidersIcon />, path: "/providers" },
  { name: "Staking Calculator", icon: <StakingCalculatorIcon />, path: "/calculator" },
  { name: "Data API", icon: <DataApiIcon />, path: "/api" },
  { name: "Liquid Staking", icon: <LiquidStakingIcon />, path: "/liquid-staking", beta: true },
];

export const ACTIVE_ASSETS: ActiveAssetType[] = [
  { name: "Asset Ethereum", icon: <EthereumIcon className="w-5 h-5" />, amount: "$7,699.00", bgColorClass: "bg-indigo-500" },
  { name: "Asset Avalanche", icon: <AvalancheIcon className="w-5 h-5" />, amount: "$1,340.00", bgColorClass: "bg-red-500" },
  { name: "Asset Polygon", icon: <PolygonIcon className="w-5 h-5" />, amount: "$540.00", bgColorClass: "bg-purple-500" },
  { name: "Asset Solana", icon: <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-xs text-white">SOL</div>, amount: "$980.00", bgColorClass: "bg-green-500" },
];

export const TOP_STAKING_ASSETS_DATA: TopAsset[] = [
  {
    id: 'eth',
    name: "Ethereum (ETH)",
    shortName: "Proof of Stake",
    icon: <EthereumIcon />,
    rewardRate: "13.62%",
    change: "+6.28%",
    changeType: 'positive',
    chartData: [ { name: 'Jan', value: 30 }, { name: 'Feb', value: 45 }, { name: 'Mar', value: 40 }, { name: 'Apr', value: 60 }, { name: 'May', value: 70 }, { name: 'Jun', value: 65 } ],
    color: "#818cf8" // indigo-400
  },
  {
    id: 'bnb',
    name: "BNB Chain",
    shortName: "Proof of Stake",
    icon: <BnbIcon />,
    rewardRate: "12.72%",
    change: "+8.67%",
    changeType: 'positive',
    chartData: [ { name: 'Jan', value: 20 }, { name: 'Feb', value: 35 }, { name: 'Mar', value: 50 }, { name: 'Apr', value: 45 }, { name: 'May', value: 60 }, { name: 'Jun', value: 75 } ],
    color: "#a78bfa" // violet-400 (approximating the purple line)
  },
  {
    id: 'matic',
    name: "Polygon (Matic)",
    shortName: "Proof of Stake",
    icon: <PolygonIcon />,
    rewardRate: "6.29%",
    change: "-1.89%",
    changeType: 'negative',
    chartData: [ { name: 'Jan', value: 50 }, { name: 'Feb', value: 40 }, { name: 'Mar', value: 30 }, { name: 'Apr', value: 25 }, { name: 'May', value: 20 }, { name: 'Jun', value: 15 } ],
    color: "#f87171" // red-400
  },
];

export const INVESTMENT_PERIOD_DATA: ChartDataItem[] = [
  { name: 'Start', value: 0 },
  { name: '1M', value: 25 },
  { name: '2M', value: 50 },
  { name: '3M', value: 75 },
  { name: '4M', value: 100 }, // Current position example
  { name: '5M', value: 100 },
  { name: '6M', value: 100 },
];
