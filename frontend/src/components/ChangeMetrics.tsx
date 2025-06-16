import React, { useState, useEffect } from 'react';
import { GitBranch, TrendingUp, TrendingDown, RefreshCw, FileText, Activity } from 'lucide-react';
import { api } from '../api/client';

interface ChangeMetricsProps {
  className?: string;
  compact?: boolean;
}

const ChangeMetrics: React.FC<ChangeMetricsProps> = ({ className = '', compact = false }) => {
  const [metrics, setMetrics] = useState<any>(null);
  const [recentChanges, setRecentChanges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await api.getChangeMetrics();
      if (response.status === 'success') {
        setMetrics(response.metrics);
        setRecentChanges(response.recent_changes || []);
        setError(null);
      } else {
        setError(response.error || 'Failed to load metrics');
      }
    } catch (err) {
      setError('Failed to fetch change metrics');
      console.error('Change metrics error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset change tracking metrics? This will trigger architecture analysis at the next threshold.')) {
      return;
    }
    
    try {
      await api.resetChangeMetrics();
      await fetchMetrics();
    } catch (err) {
      console.error('Reset error:', err);
    }
  };

  const formatTimeSince = (seconds: number): string => {
    if (seconds < 60) return `${Math.floor(seconds)}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  if (loading) {
    return (
      <div className={`bg-slate-800 rounded-xl shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-slate-800 rounded-xl shadow-lg p-6 ${className}`}>
        <p className="text-red-400 text-center">{error}</p>
      </div>
    );
  }

  if (!metrics) return null;

  const progressPercentage = Math.min(
    (metrics.total_lines_changed / 100) * 100,
    100
  );

  if (compact) {
    return (
      <div className={`bg-slate-800 rounded-xl shadow-lg p-4 ${className}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-purple-400" />
            <div>
              <p className="text-sm font-medium text-white">Code Changes</p>
              <p className="text-xs text-gray-400">
                {metrics.total_lines_changed} lines · {metrics.files_changed_count} files
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-right">
              <p className="text-xs text-gray-400">Since</p>
              <p className="text-xs text-white">{formatTimeSince(metrics.time_since_reset)}</p>
            </div>
            <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-purple-600 to-indigo-600 transition-all duration-300"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-slate-800 rounded-xl shadow-lg ${className}`}>
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-purple-400" />
          Change Tracking
        </h3>
        <button
          onClick={handleReset}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          title="Reset Metrics"
        >
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      <div className="p-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              <span className="text-xs text-gray-400">Added</span>
            </div>
            <p className="text-2xl font-semibold text-green-400">{metrics.lines_added}</p>
            <p className="text-xs text-gray-400">lines</p>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <TrendingDown className="w-5 h-5 text-red-400" />
              <span className="text-xs text-gray-400">Removed</span>
            </div>
            <p className="text-2xl font-semibold text-red-400">{metrics.lines_removed}</p>
            <p className="text-xs text-gray-400">lines</p>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <FileText className="w-5 h-5 text-blue-400" />
              <span className="text-xs text-gray-400">Files</span>
            </div>
            <p className="text-2xl font-semibold text-blue-400">{metrics.files_changed_count}</p>
            <p className="text-xs text-gray-400">changed</p>
          </div>

          <div className="bg-slate-700/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <Activity className="w-5 h-5 text-purple-400" />
              <span className="text-xs text-gray-400">Diffs</span>
            </div>
            <p className="text-2xl font-semibold text-purple-400">{metrics.diffs_processed}</p>
            <p className="text-xs text-gray-400">tracked</p>
          </div>
        </div>

        {/* Progress to Threshold */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-white">Progress to Analysis Threshold</p>
            <p className="text-sm text-gray-400">{metrics.total_lines_changed} / 100 lines</p>
          </div>
          <div className="w-full h-3 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-purple-600 to-indigo-600 transition-all duration-300"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Architecture analysis triggers at 100 lines changed or 5 files modified
          </p>
        </div>

        {/* Recent Changes */}
        {recentChanges.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-white mb-3">Recent Changes</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {recentChanges.map((change, index) => (
                <div key={index} className="bg-slate-700/30 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-gray-300 truncate flex-1 mr-2">{change.file_path}</span>
                    <span className="text-gray-500">{change.agent_type}</span>
                  </div>
                  <div className="flex items-center gap-4 text-gray-400">
                    <span className="text-green-400">+{change.lines_added}</span>
                    <span className="text-red-400">-{change.lines_removed}</span>
                    <span className="ml-auto">{formatTimeSince(
                      (new Date().getTime() - new Date(change.timestamp).getTime()) / 1000
                    )}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Last Reset */}
        <div className="mt-4 pt-4 border-t border-slate-700">
          <p className="text-xs text-gray-400">
            Tracking since: {new Date(metrics.last_reset).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChangeMetrics;