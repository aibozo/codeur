
import React from 'react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { TopAsset } from '../types';
import { ExternalLinkIcon } from '../constants';

interface AssetCardProps {
  asset: TopAsset;
}

const AssetCard: React.FC<AssetCardProps> = ({ asset }) => {
  const changeColorClass = asset.changeType === 'positive' ? 'text-green-400' : 'text-red-400';

  return (
    <div className="bg-slate-800 p-4 rounded-xl shadow-lg flex flex-col h-full hover:bg-slate-700/50 transition-colors duration-150 cursor-pointer group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          {asset.icon}
          <div>
            <p className="text-sm text-gray-400">{asset.shortName}</p>
            <h3 className="text-md font-semibold text-white">{asset.name}</h3>
          </div>
        </div>
        <button className="p-1 rounded-md text-gray-500 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
           <ExternalLinkIcon className="w-4 h-4" />
        </button>
      </div>

      <div className="mb-3">
        <p className="text-xs text-gray-500">Reward Rate</p>
        <p className="text-2xl font-bold text-white">{asset.rewardRate}</p>
        <p className={`text-sm font-medium ${changeColorClass}`}>{asset.change}</p>
      </div>

      <div className="flex-grow h-20 -mx-4 -mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={asset.chartData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id={`gradient-${asset.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={asset.color} stopOpacity={0.4}/>
                <stop offset="95%" stopColor={asset.color} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(30, 41, 59, 0.8)', // slate-800 with opacity
                borderColor: 'rgba(51, 65, 85, 0.8)', // slate-700 with opacity
                borderRadius: '0.5rem',
                color: '#e2e8f0', // slate-200
                fontSize: '0.75rem',
                padding: '0.25rem 0.5rem',
              }}
              itemStyle={{ color: '#e2e8f0' }}
              labelStyle={{ display: 'none' }}
              cursor={{ stroke: asset.color, strokeWidth: 1, strokeDasharray: '3 3' }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={asset.color}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, stroke: asset.color, fill: asset.color }}
            />
             {/* This creates a fill, if desired. The image doesn't strictly have a strong fill for these small charts.
             <Area type="monotone" dataKey="value" stroke={false} fillOpacity={1} fill={`url(#gradient-${asset.id})`} />
             */}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default AssetCard;
