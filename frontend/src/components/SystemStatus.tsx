import React from 'react';
import { Server, Cpu, HardDrive, Zap, AlertCircle, CheckCircle2 } from 'lucide-react';

interface StatusItemProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  status: 'good' | 'warning' | 'critical';
  subValue?: string;
}

const statusColors = {
  good: 'text-green-400',
  warning: 'text-yellow-400',
  critical: 'text-red-400',
};

const StatusItem: React.FC<StatusItemProps> = ({ icon, label, value, status, subValue }) => (
  <div className="flex items-center justify-between py-3 border-b border-slate-700 last:border-0">
    <div className="flex items-center gap-3">
      <div className="p-2 bg-slate-700/50 rounded-lg">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-white">{label}</p>
        {subValue && <p className="text-xs text-gray-500">{subValue}</p>}
      </div>
    </div>
    <div className="text-right">
      <p className={`text-sm font-medium ${statusColors[status]}`}>{value}</p>
    </div>
  </div>
);

const SystemStatus: React.FC = () => {
  return (
    <div className="bg-slate-800 p-6 rounded-xl shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center gap-2">
          <Server className="w-5 h-5 text-purple-400" />
          System Status
        </h3>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-400">Healthy</span>
        </div>
      </div>

      <div className="space-y-1">
        <StatusItem
          icon={<Cpu className="w-4 h-4 text-blue-400" />}
          label="CPU Usage"
          value="45%"
          status="good"
          subValue="4 cores @ 3.2GHz"
        />
        <StatusItem
          icon={<HardDrive className="w-4 h-4 text-purple-400" />}
          label="Memory"
          value="8.2 / 16 GB"
          status="warning"
          subValue="51% used"
        />
        <StatusItem
          icon={<HardDrive className="w-4 h-4 text-orange-400" />}
          label="Storage"
          value="124 / 500 GB"
          status="good"
          subValue="25% used"
        />
        <StatusItem
          icon={<Zap className="w-4 h-4 text-yellow-400" />}
          label="API Latency"
          value="23ms"
          status="good"
          subValue="↓ 5ms from avg"
        />
      </div>

      <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-white">Maintenance Notice</p>
            <p className="text-xs text-gray-400 mt-1">
              Scheduled system update in 2 hours
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;