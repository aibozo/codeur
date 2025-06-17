import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

interface Branch {
  name: string;
  current: boolean;
  type: 'main' | 'working' | 'task' | 'feature' | 'fix' | 'checkpoint' | 'other';
}

interface GitWorkflowViewProps {
  className?: string;
}

const GitWorkflowView: React.FC<GitWorkflowViewProps> = ({ className = '' }) => {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string>('');
  const [gitHistory, setGitHistory] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkpointDescription, setCheckpointDescription] = useState('');
  const [creatingCheckpoint, setCreatingCheckpoint] = useState(false);

  const fetchGitData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch branches
      const branchesResponse = await apiClient.get('/api/git/branches');
      if (branchesResponse.data.status === 'success') {
        setBranches(branchesResponse.data.branches);
        setCurrentBranch(branchesResponse.data.current_branch);
      }

      // Fetch git history
      const historyResponse = await apiClient.get('/api/git/history');
      if (historyResponse.data.status === 'success') {
        setGitHistory(historyResponse.data.history);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch git data');
    } finally {
      setLoading(false);
    }
  };

  const createCheckpoint = async () => {
    if (!checkpointDescription.trim()) return;
    
    try {
      setCreatingCheckpoint(true);
      const response = await apiClient.post('/api/git/checkpoint', {
        description: checkpointDescription
      });
      
      if (response.data.status === 'success') {
        setCheckpointDescription('');
        await fetchGitData(); // Refresh data
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to create checkpoint');
    } finally {
      setCreatingCheckpoint(false);
    }
  };

  useEffect(() => {
    fetchGitData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchGitData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getBranchTypeColor = (type: Branch['type']) => {
    switch (type) {
      case 'main': return 'bg-blue-500';
      case 'working': return 'bg-green-500';
      case 'task': return 'bg-purple-500';
      case 'feature': return 'bg-yellow-500';
      case 'fix': return 'bg-red-500';
      case 'checkpoint': return 'bg-gray-500';
      default: return 'bg-gray-400';
    }
  };

  const getBranchTypeIcon = (type: Branch['type']) => {
    switch (type) {
      case 'main': return '🏠';
      case 'working': return '⚡';
      case 'task': return '📋';
      case 'feature': return '✨';
      case 'fix': return '🔧';
      case 'checkpoint': return '📍';
      default: return '📂';
    }
  };

  if (loading) {
    return (
      <div className={`p-6 bg-white rounded-lg shadow-sm ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-2">
            <div className="h-3 bg-gray-200 rounded"></div>
            <div className="h-3 bg-gray-200 rounded w-5/6"></div>
            <div className="h-3 bg-gray-200 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-6 bg-white rounded-lg shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">Git Workflow</h3>
        <button
          onClick={fetchGitData}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Current Branch Status */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Current Branch</h4>
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            {currentBranch || 'Unknown'}
          </span>
          <span className="text-xs text-gray-500">
            Active working branch
          </span>
        </div>
      </div>

      {/* Branch List */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">All Branches</h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {branches.map((branch) => (
            <div
              key={branch.name}
              className={`flex items-center justify-between p-2 rounded-md ${
                branch.current ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'
              }`}
            >
              <div className="flex items-center space-x-3">
                <span className="text-sm">{getBranchTypeIcon(branch.type)}</span>
                <span className={`text-sm ${branch.current ? 'font-medium text-blue-900' : 'text-gray-700'}`}>
                  {branch.name}
                </span>
                {branch.current && (
                  <span className="text-xs text-blue-600">current</span>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <span className={`inline-block w-2 h-2 rounded-full ${getBranchTypeColor(branch.type)}`}></span>
                <span className="text-xs text-gray-500 capitalize">{branch.type}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Create Checkpoint */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Create Checkpoint</h4>
        <div className="flex space-x-2">
          <input
            type="text"
            value={checkpointDescription}
            onChange={(e) => setCheckpointDescription(e.target.value)}
            placeholder="Checkpoint description..."
            className="flex-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={createCheckpoint}
            disabled={creatingCheckpoint || !checkpointDescription.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creatingCheckpoint ? '...' : '📍 Save'}
          </button>
        </div>
      </div>

      {/* Git History */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Recent Commits</h4>
        <div className="bg-gray-900 rounded-md p-4 overflow-x-auto">
          <pre className="text-xs text-green-400 font-mono whitespace-pre-wrap">
            {gitHistory || 'No commit history available'}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default GitWorkflowView;