
import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, DotProps, Dot } from 'recharts';
import { AvalancheIcon, ExternalLinkIcon, RefreshIcon, ChevronDownIcon, ChartBarIcon, MenuIcon } from '../constants';
import { INVESTMENT_PERIOD_DATA } from '../constants';
import { ChartDataItem } from '../types';


interface CustomDotProps extends DotProps {
  // DotProps from recharts includes cx, cy, stroke, fill, r, payload, value, etc.
  // Recharts' payload is the data object for that point. Here, it's ChartDataItem.
  payload?: ChartDataItem; 
  currentPeriod?: string;
}

const CustomizedDot = (props: CustomDotProps): React.ReactElement | null => {
  const { cx, cy, stroke, payload, currentPeriod } = props; // 'value' prop removed from destructuring as it was not used.

  // cx and cy are optional in DotProps, ensure they are numbers before using
  if (typeof cx !== 'number' || typeof cy !== 'number') {
    return null;
  }

  if (payload && payload.name === currentPeriod) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={8} fill={stroke} stroke="#1e293b" strokeWidth={3} />
        <circle cx={cx} cy={cy} r={4} fill="#fff" />
      </g>
    );
  }
  
  // The original code had a condition for '4 Month' or '6 Month'.
  // Assuming data keys like '4M', and preventing overlap with currentPeriod dot.
  if (payload && (payload.name === '4M' || payload.name === '6M') && payload.name !== currentPeriod) {
    // Assuming 'stroke' (line color) should be the fill of these secondary dots.
    return <Dot cx={cx} cy={cy} r={4} fill={stroke} stroke="#1e293b" strokeWidth={2}/>;
  }

  return null;
};


const StatCard: React.FC<{ title: string; value: string; trend?: string; trendType?: 'positive' | 'negative'; timeFrame?: string; subTitle?: string; children?: React.ReactNode }> = 
({ title, value, trend, trendType, timeFrame, subTitle, children }) => {
  const trendColor = trendType === 'positive' ? 'text-green-400' : trendType === 'negative' ? 'text-red-400' : 'text-gray-400';
  return (
    <div className="bg-slate-800/50 p-4 rounded-lg">
      <div className="flex justify-between items-center mb-1">
        <h4 className="text-xs text-gray-400">{title}</h4>
        {timeFrame && <span className="text-xs bg-slate-700 px-1.5 py-0.5 rounded text-gray-300">{timeFrame}</span>}
      </div>
      {subTitle && <p className="text-xs text-gray-500 mb-1">{subTitle}</p>}
      <p className="text-xl font-semibold text-white">{value}</p>
      {trend && <p className={`text-xs ${trendColor}`}>{trend}</p>}
      {children}
    </div>
  );
};


const ActiveStakingInfo: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<'4 Month' | '6 Month'>('4 Month');
  // Note: INVESTMENT_PERIOD_DATA uses '4M', '6M'. `currentInvestmentPeriod` should match these keys.
  const currentInvestmentPeriod = '4M'; // Example, should match a 'name' in INVESTMENT_PERIOD_DATA

  return (
    <div className="bg-slate-800 p-6 rounded-xl shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
        <div>
          <p className="text-xs text-gray-500">Last Update - 45 minutes ago</p>
          <div className="flex items-center space-x-2 mt-1">
            <h2 className="text-2xl font-semibold text-white">Stake Avalance (AVAX)</h2>
            <AvalancheIcon className="w-7 h-7" />
            <button className="p-1 rounded-md text-gray-400 hover:text-gray-200"><RefreshIcon className="w-4 h-4" /></button>
            <button className="flex items-center text-xs text-purple-400 hover:text-purple-300">
              View Profile <ExternalLinkIcon className="ml-1 w-3 h-3" />
            </button>
          </div>
        </div>
        <div className="flex items-center space-x-2 mt-3 md:mt-0">
          <button className="p-1.5 rounded-md text-gray-400 hover:text-gray-200 bg-slate-700/50 hover:bg-slate-600/50"><ChartBarIcon /></button>
          <button className="p-1.5 rounded-md text-gray-400 hover:text-gray-200 bg-slate-700/50 hover:bg-slate-600/50"><RefreshIcon /></button>
          <button className="p-1.5 rounded-md text-gray-400 hover:text-gray-200 bg-slate-700/50 hover:bg-slate-600/50"><MenuIcon /></button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row items-start md:items-end justify-between mb-6">
        <div>
            <p className="text-sm text-gray-400">Current Reward Balance, AVAX</p>
            <p className="text-5xl font-bold text-white mt-1">31.39686</p>
        </div>
        <div className="flex space-x-3 mt-4 md:mt-0">
          <button className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium py-2.5 px-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-150 text-sm">
            Upgrade
          </button>
          <button className="bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white font-medium py-2.5 px-6 rounded-lg text-sm transition-colors">
            Unstake
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Momentum" subTitle="Growth dynamics" value="-0.82%" trendType="negative" timeFrame="24H" />
        <StatCard title="Price" value="$41.99" trend="-1.09%" trendType="negative" timeFrame="24H" />
        <StatCard title="Staking Ratio" value="60.6%" timeFrame="24H" />
        <StatCard title="Reward Rate" value="2.23%" trend="+1.46% 48H Ago" trendType="positive" />
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold text-white">Investment Period</h3>
            <div className="flex space-x-1 bg-slate-700 p-0.5 rounded-md">
                <button 
                    onClick={() => setActiveTab('4 Month')}
                    className={`px-3 py-1 text-xs rounded ${activeTab === '4 Month' ? 'bg-slate-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                    4 Month
                </button>
                <button 
                    onClick={() => setActiveTab('6 Month')}
                    className={`px-3 py-1 text-xs rounded ${activeTab === '6 Month' ? 'bg-slate-600 text-white' : 'text-gray-400 hover:text-white'}`}
                >
                    6 Month
                </button>
            </div>
        </div>
        <p className="text-sm text-gray-400 mb-3">Contribution Period ({activeTab})</p>
        <div className="h-20 bg-slate-800/50 p-2 rounded-lg">
             <ResponsiveContainer width="100%" height="100%">
                <LineChart data={INVESTMENT_PERIOD_DATA} margin={{ top: 5, right: 30, left: -30, bottom: 5 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval={0} />
                    <YAxis hide={true} domain={[0, 120]} />
                    <Tooltip 
                        contentStyle={{ backgroundColor: 'rgba(30, 41, 59, 0.8)', borderColor: 'rgba(51, 65, 85, 0.8)', borderRadius: '0.5rem' }} 
                        itemStyle={{color: '#e2e8f0'}}
                        labelFormatter={(label) => `Period: ${label}`}
                        formatter={(value: number, name: string, entry) => {
                             // Assuming entry.payload always has a 'value' field of type number
                             // The 'value' argument to formatter is the specific dataKey's value
                             const numericValue = typeof entry.payload.value === 'string' ? parseFloat(entry.payload.value) : entry.payload.value;
                             return [`${numericValue}%`, name.charAt(0).toUpperCase() + name.slice(1)];
                        }}
                    />
                    <Line 
                        type="stepAfter" 
                        dataKey="value" 
                        stroke="#8b5cf6" // purple-500
                        strokeWidth={3} 
                        // The `dot` prop can accept a ReactElement, a boolean, or a function component.
                        // Pass the component itself, not an instance: dot={CustomizedDot}
                        // To pass props to it (like currentPeriod), use a function or render prop pattern if supported,
                        // or rely on Recharts passing relevant props (like payload, cx, cy).
                        // For currentPeriod, it's better to pass it via a custom prop if the `dot` prop takes a function.
                        // Recharts typically passes cx, cy, stroke, payload, value to the dot function or component.
                        // We are passing currentInvestmentPeriod to our CustomizedDot component.
                        dot={(props: DotProps) => <CustomizedDot {...props} currentPeriod={currentInvestmentPeriod} />}
                        activeDot={false}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};

export default ActiveStakingInfo;
