import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity } from 'lucide-react';

const data = [
  { name: '00:00', agents: 8, tasks: 120, success: 98 },
  { name: '04:00', agents: 6, tasks: 80, success: 97 },
  { name: '08:00', agents: 10, tasks: 200, success: 99 },
  { name: '12:00', agents: 12, tasks: 280, success: 98 },
  { name: '16:00', agents: 11, tasks: 250, success: 97 },
  { name: '20:00', agents: 9, tasks: 180, success: 99 },
  { name: '24:00', agents: 8, tasks: 140, success: 98 },
];

const PerformanceChart: React.FC = () => {
  return (
    <div className="bg-gradient-to-br from-slate-800 via-slate-800 to-purple-900/30 p-6 rounded-xl shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" />
            Agent Performance
          </h3>
          <p className="text-sm text-gray-400 mt-1">24-hour overview</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="text-xs px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 text-gray-300">
            Export
          </button>
        </div>
      </div>
      
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
            <XAxis 
              dataKey="name" 
              stroke="#9CA3AF"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#9CA3AF"
              style={{ fontSize: '12px' }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(30, 41, 59, 0.95)', 
                border: '1px solid rgba(51, 65, 85, 0.8)',
                borderRadius: '8px',
                padding: '12px',
              }}
              labelStyle={{ color: '#e2e8f0', fontWeight: 'bold', marginBottom: '4px' }}
              itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
            />
            <Legend 
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="line"
              formatter={(value) => <span style={{ color: '#e2e8f0', fontSize: '12px' }}>{value}</span>}
            />
            <Line 
              type="monotone" 
              dataKey="agents" 
              stroke="#a78bfa" 
              strokeWidth={2.5}
              dot={{ fill: '#a78bfa', r: 4 }}
              activeDot={{ r: 6 }}
              name="Active Agents"
            />
            <Line 
              type="monotone" 
              dataKey="tasks" 
              stroke="#60a5fa" 
              strokeWidth={2.5}
              dot={{ fill: '#60a5fa', r: 4 }}
              activeDot={{ r: 6 }}
              name="Tasks Completed"
              yAxisId="right"
            />
            <Line 
              type="monotone" 
              dataKey="success" 
              stroke="#34d399" 
              strokeWidth={2.5}
              dot={{ fill: '#34d399', r: 4 }}
              activeDot={{ r: 6 }}
              name="Success Rate %"
            />
            <YAxis yAxisId="right" orientation="right" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PerformanceChart;