/**
 * React component for Git Activity Feed
 * 
 * This component shows a compact, real-time activity feed of git operations
 * performed by the multi-agent system.
 */

import React, { useEffect, useState } from 'react';

interface GitActivity {
  id: string;
  type: 'commit' | 'checkpoint' | 'task' | 'merge' | 'revert';
  icon: string;
  title: string;
  author: string;
  timestamp: string;
  relativeTime: string;
  taskId?: string;
  agentId?: string;
  branch: string;
}

interface Props {
  maxItems?: number;
  refreshInterval?: number; // in milliseconds
  onActivityClick?: (activity: GitActivity) => void;
}

export const GitActivityFeed: React.FC<Props> = ({
  maxItems = 20,
  refreshInterval = 30000, // 30 seconds
  onActivityClick
}) => {
  const [activities, setActivities] = useState<GitActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActivities();
    
    // Set up auto-refresh
    const interval = setInterval(fetchActivities, refreshInterval);
    
    return () => clearInterval(interval);
  }, [maxItems, refreshInterval]);

  const fetchActivities = async () => {
    try {
      const response = await fetch(`/api/git/activity?max_items=${maxItems}`);
      const result = await response.json();
      
      if (result.success) {
        setActivities(result.activities);
      }
    } catch (error) {
      console.error('Failed to fetch git activities:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityColor = (type: string): string => {
    switch (type) {
      case 'checkpoint':
        return '#2196F3'; // Blue
      case 'task':
        return '#4CAF50'; // Green
      case 'merge':
        return '#9C27B0'; // Purple
      case 'revert':
        return '#F44336'; // Red
      default:
        return '#757575'; // Gray
    }
  };

  const getAgentBadgeColor = (agentId?: string): string => {
    if (!agentId) return '#999';
    
    const agentColors: Record<string, string> = {
      'coding_agent': '#4CAF50',
      'test_agent': '#2196F3',
      'architect': '#9C27B0',
      'request_planner': '#FF9800',
      'analyzer': '#00BCD4'
    };
    
    return agentColors[agentId] || '#999';
  };

  if (loading) {
    return (
      <div className="activity-feed loading">
        <div className="spinner"></div>
        Loading activities...
      </div>
    );
  }

  return (
    <div className="git-activity-feed">
      <div className="feed-header">
        <h3>Git Activity</h3>
        <button onClick={fetchActivities} className="refresh-btn">
          🔄 Refresh
        </button>
      </div>

      <div className="activities">
        {activities.length === 0 ? (
          <div className="no-activities">No recent activities</div>
        ) : (
          activities.map(activity => (
            <div
              key={activity.id}
              className="activity-item"
              onClick={() => onActivityClick?.(activity)}
            >
              <div 
                className="activity-icon"
                style={{ color: getActivityColor(activity.type) }}
              >
                {activity.icon}
              </div>
              
              <div className="activity-content">
                <div className="activity-title">{activity.title}</div>
                <div className="activity-meta">
                  <span className="author">{activity.author}</span>
                  <span className="time">{activity.relativeTime}</span>
                  <span className="branch">{activity.branch}</span>
                </div>
                
                {(activity.taskId || activity.agentId) && (
                  <div className="activity-tags">
                    {activity.taskId && (
                      <span className="tag task-tag">
                        Task: {activity.taskId}
                      </span>
                    )}
                    {activity.agentId && (
                      <span 
                        className="tag agent-tag"
                        style={{ 
                          backgroundColor: getAgentBadgeColor(activity.agentId),
                          color: 'white'
                        }}
                      >
                        {activity.agentId.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <style jsx>{`
        .git-activity-feed {
          display: flex;
          flex-direction: column;
          height: 100%;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: white;
          border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .feed-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          border-bottom: 1px solid #e0e0e0;
        }

        .feed-header h3 {
          margin: 0;
          font-size: 1.1rem;
          color: #333;
        }

        .refresh-btn {
          background: none;
          border: 1px solid #e0e0e0;
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.85rem;
          color: #666;
          transition: all 0.2s;
        }

        .refresh-btn:hover {
          background: #f5f5f5;
          border-color: #ccc;
        }

        .activities {
          flex: 1;
          overflow-y: auto;
        }

        .activity-item {
          display: flex;
          gap: 1rem;
          padding: 1rem;
          border-bottom: 1px solid #f0f0f0;
          cursor: pointer;
          transition: background 0.2s;
        }

        .activity-item:hover {
          background: #f9f9f9;
        }

        .activity-icon {
          font-size: 1.5rem;
          line-height: 1;
          flex-shrink: 0;
        }

        .activity-content {
          flex: 1;
          min-width: 0;
        }

        .activity-title {
          font-weight: 500;
          color: #333;
          margin-bottom: 0.25rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .activity-meta {
          display: flex;
          gap: 1rem;
          font-size: 0.85rem;
          color: #666;
          margin-bottom: 0.25rem;
        }

        .author {
          font-weight: 500;
        }

        .time {
          color: #999;
        }

        .branch {
          color: #999;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 0.8rem;
        }

        .activity-tags {
          display: flex;
          gap: 0.5rem;
          margin-top: 0.5rem;
        }

        .tag {
          display: inline-block;
          padding: 0.15rem 0.5rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .task-tag {
          background: #e3f2fd;
          color: #1976d2;
        }

        .agent-tag {
          text-transform: capitalize;
        }

        .no-activities {
          padding: 2rem;
          text-align: center;
          color: #999;
        }

        .loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          color: #666;
        }

        .spinner {
          width: 24px;
          height: 24px;
          border: 2px solid #f0f0f0;
          border-top-color: #2196f3;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin-bottom: 1rem;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
};