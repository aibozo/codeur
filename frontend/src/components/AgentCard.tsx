import React from 'react';
import { Bot, MoreVertical } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

interface AgentCardProps {
  name: string;
  status: 'active' | 'idle' | 'error';
  tasks: number;
  model?: string;
  metrics?: {
    accuracy: string;
    speed: string;
  };
}

const statusConfig = {
  active: { color: 'text-green-400', bg: 'bg-green-400/20', label: 'Active' },
  idle: { color: 'text-yellow-400', bg: 'bg-yellow-400/20', label: 'Idle' },
  error: { color: 'text-red-400', bg: 'bg-red-400/20', label: 'Error' },
};

// Sample data for the mini chart
const chartData = [
  { value: 30 },
  { value: 45 },
  { value: 35 },
  { value: 50 },
  { value: 40 },
  { value: 55 },
  { value: 48 },
];

const AgentCard: React.FC<AgentCardProps> = ({ name, status, tasks, model, metrics }) => {
  const config = statusConfig[status];
  
  return (
    <div className="bg-slate-800 p-4 rounded-xl shadow-lg flex flex-col hover:bg-slate-700/50 transition-colors duration-150 cursor-pointer group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-slate-700 rounded-lg">
            <Bot className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <p className="text-sm text-gray-400">{model || 'AI Model'}</p>
            <h3 className="text-md font-semibold text-white">{name}</h3>
          </div>
        </div>
        <button className="p-1 rounded-md text-gray-500 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>

      <div className="mb-3">
        <p className="text-xs text-gray-500">Tasks Completed</p>
        <p className="text-2xl font-bold text-white">{tasks}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-xs px-2 py-1 rounded-full ${config.bg} ${config.color}`}>
            {config.label}
          </span>
          <span className="text-xs text-gray-400">Last active 2m ago</span>
        </div>
      </div>

      {metrics && (
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div>
            <p className="text-xs text-gray-500">Accuracy</p>
            <p className="text-sm font-medium text-white">{metrics.accuracy}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Avg Speed</p>
            <p className="text-sm font-medium text-white">{metrics.speed}</p>
          </div>
        </div>
      )}

      <div className="h-16 -mx-4 -mb-4 mt-auto">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(30, 41, 59, 0.8)',
                borderColor: 'rgba(51, 65, 85, 0.8)',
                borderRadius: '0.5rem',
                color: '#e2e8f0',
                fontSize: '0.75rem',
                padding: '0.25rem 0.5rem',
              }}
              itemStyle={{ color: '#e2e8f0' }}
              labelStyle={{ display: 'none' }}
              cursor={{ stroke: '#a78bfa', strokeWidth: 1, strokeDasharray: '3 3' }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#a78bfa"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, stroke: '#a78bfa', fill: '#a78bfa' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default AgentCard;