import React from 'react';
import { NavLink } from 'react-router-dom';
import { Bot, Activity, FileText, Settings, LayoutDashboard, Hammer } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/build', label: 'Build', icon: Hammer },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/metrics', label: 'Metrics', icon: Activity },
  { path: '/logs', label: 'Logs', icon: FileText },
  { path: '/settings', label: 'Settings', icon: Settings },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Bot className="w-8 h-8 text-purple-500" />
          Codeur
        </h1>
      </div>
      
      <nav className="flex-1 px-4 pb-4">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-slate-700 hover:text-white transition-colors ${
                      isActive ? 'bg-slate-700 text-white' : ''
                    }`
                  }
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
      
      <div className="p-4 border-t border-slate-700">
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-1">Pro Version</h3>
          <p className="text-purple-100 text-sm">Unlock advanced features</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;