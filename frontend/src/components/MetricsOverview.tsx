import React from 'react';
import { Bot, Activity, CheckCircle, Clock, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: string;
  trendDirection?: 'up' | 'down';
}

const MetricCard: React.FC<MetricCardProps> = ({ icon, label, value, trend, trendDirection }) => (
  <div className="bg-slate-800 rounded-xl p-6 shadow-lg hover:bg-slate-700/50 transition-colors duration-150">
    <div className="flex items-center justify-between mb-4">
      <div className="p-2 bg-slate-700 rounded-lg">
        {icon}
      </div>
      {trend && (
        <div className={`flex items-center gap-1 text-sm ${
          trendDirection === 'up' ? 'text-green-400' : 'text-red-400'
        }`}>
          {trendDirection === 'up' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          <span>{trend}</span>
        </div>
      )}
    </div>
    <p className="text-gray-400 text-sm">{label}</p>
    <p className="text-2xl font-bold text-white mt-1">{value}</p>
  </div>
);

const MetricsOverview: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
      <MetricCard
        icon={<Bot className="w-5 h-5 text-purple-400" />}
        label="Active Agents"
        value="12"
        trend="+2"
        trendDirection="up"
      />
      <MetricCard
        icon={<Activity className="w-5 h-5 text-blue-400" />}
        label="Avg Response Time"
        value="245ms"
        trend="-15ms"
        trendDirection="up"
      />
      <MetricCard
        icon={<CheckCircle className="w-5 h-5 text-green-400" />}
        label="Success Rate"
        value="98.5%"
        trend="+0.3%"
        trendDirection="up"
      />
      <MetricCard
        icon={<Clock className="w-5 h-5 text-orange-400" />}
        label="Uptime"
        value="99.9%"
      />
    </div>
  );
};

export default MetricsOverview;