/**
 * React component for Git Workflow Visualization
 * 
 * This component demonstrates how to display the git workflow
 * visualization in a React frontend using the data from GitVisualizer.
 */

import React, { useEffect, useState, useRef } from 'react';
import * as d3 from 'd3';

interface GitNode {
  id: string;
  sha: string;
  type: string;
  label: string;
  branch: string;
  message: string;
  author: string;
  timestamp: string;
  taskId?: string;
  agentId?: string;
  isCheckpoint: boolean;
  isCurrent: boolean;
  color: string;
  symbol: string;
}

interface GitEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

interface GitVisualizationData {
  nodes: GitNode[];
  edges: GitEdge[];
  branches: Array<{
    name: string;
    sha: string;
    isCurrent: boolean;
  }>;
  currentBranch: string;
  currentCommit: string;
  tasks: Array<{
    id: string;
    commits: string[];
    agents: string[];
    status: string;
  }>;
  checkpoints: Array<{
    id: string;
    description: string;
    timestamp: string;
    branch: string;
  }>;
  stats: {
    totalCommits: number;
    totalTasks: number;
    totalCheckpoints: number;
    activeBranches: number;
  };
}

interface Props {
  projectPath?: string;
  maxCommits?: number;
  onNodeClick?: (node: GitNode) => void;
  onCheckpointRestore?: (checkpointId: string) => void;
  onTaskRevert?: (taskId: string) => void;
}

export const GitWorkflowVisualization: React.FC<Props> = ({
  maxCommits = 50,
  onNodeClick,
  onCheckpointRestore,
  onTaskRevert
}) => {
  const [data, setData] = useState<GitVisualizationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GitNode | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    fetchVisualizationData();
  }, [maxCommits]);

  const fetchVisualizationData = async () => {
    try {
      const response = await fetch(`/api/git/visualization?max_commits=${maxCommits}`);
      const result = await response.json();
      if (result.success) {
        setData(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch git visualization:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (data && svgRef.current) {
      renderD3Visualization();
    }
  }, [data]);

  const renderD3Visualization = () => {
    if (!data || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous visualization

    const width = 1200;
    const height = 600;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create a map for quick node lookup
    const nodeMap = new Map(data.nodes.map(n => [n.id, n]));

    // Create hierarchical layout
    const stratify = d3.stratify<GitEdge>()
      .id(d => d.target)
      .parentId(d => d.source);

    // Convert edges to hierarchy
    const root = d3.hierarchy({
      id: 'root',
      children: data.nodes.filter(n => 
        !data.edges.some(e => e.target === n.id)
      )
    });

    // Create tree layout
    const treeLayout = d3.tree<any>()
      .size([height - margin.top - margin.bottom, width - margin.left - margin.right - 200]);

    // Define arrow markers
    svg.append('defs').selectAll('marker')
      .data(['arrow'])
      .enter().append('marker')
      .attr('id', d => d)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Draw edges
    const links = g.selectAll('.link')
      .data(data.edges)
      .enter().append('path')
      .attr('class', 'link')
      .attr('d', (d: GitEdge) => {
        const source = nodeMap.get(d.source);
        const target = nodeMap.get(d.target);
        if (!source || !target) return '';
        
        // Simple curved path
        const dx = target.x! - source.x!;
        const dy = target.y! - source.y!;
        const dr = Math.sqrt(dx * dx + dy * dy);
        
        return `M${source.x},${source.y}A${dr},${dr} 0 0,1 ${target.x},${target.y}`;
      })
      .style('fill', 'none')
      .style('stroke', '#999')
      .style('stroke-width', 2)
      .attr('marker-end', 'url(#arrow)');

    // Draw nodes
    const nodes = g.selectAll('.node')
      .data(data.nodes)
      .enter().append('g')
      .attr('class', 'node')
      .attr('transform', (d: GitNode, i: number) => {
        // Simple grid layout
        const x = (i % 10) * 120 + 50;
        const y = Math.floor(i / 10) * 80 + 50;
        (d as any).x = x;
        (d as any).y = y;
        return `translate(${x},${y})`;
      });

    // Add node circles
    nodes.append('circle')
      .attr('r', d => d.isCheckpoint ? 12 : 8)
      .style('fill', d => d.color)
      .style('stroke', d => d.isCurrent ? '#333' : 'none')
      .style('stroke-width', d => d.isCurrent ? 3 : 0)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNode(d);
        onNodeClick?.(d);
      });

    // Add node labels
    nodes.append('text')
      .attr('dx', 12)
      .attr('dy', 4)
      .style('font-size', '12px')
      .style('fill', '#333')
      .text(d => d.label);

    // Add tooltips
    nodes.append('title')
      .text(d => `${d.message}\n${d.timestamp}\nAuthor: ${d.author}`);
  };

  const handleCheckpointRestore = async (checkpointId: string) => {
    if (onCheckpointRestore) {
      onCheckpointRestore(checkpointId);
    } else {
      try {
        const response = await fetch(`/api/git/checkpoint/restore/${checkpointId}`, {
          method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
          fetchVisualizationData(); // Refresh
        }
      } catch (error) {
        console.error('Failed to restore checkpoint:', error);
      }
    }
  };

  const handleTaskRevert = async (taskId: string) => {
    if (onTaskRevert) {
      onTaskRevert(taskId);
    } else {
      try {
        const response = await fetch(`/api/git/task/${taskId}/revert`, {
          method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
          fetchVisualizationData(); // Refresh
        }
      } catch (error) {
        console.error('Failed to revert task:', error);
      }
    }
  };

  if (loading) {
    return <div className="loading">Loading git visualization...</div>;
  }

  if (!data) {
    return <div className="error">Failed to load git visualization</div>;
  }

  return (
    <div className="git-workflow-visualization">
      <div className="header">
        <h2>Git Workflow Visualization</h2>
        <div className="stats">
          <span className="stat">
            <strong>Commits:</strong> {data.stats.totalCommits}
          </span>
          <span className="stat">
            <strong>Tasks:</strong> {data.stats.totalTasks}
          </span>
          <span className="stat">
            <strong>Checkpoints:</strong> {data.stats.totalCheckpoints}
          </span>
          <span className="stat">
            <strong>Current Branch:</strong> {data.currentBranch}
          </span>
        </div>
      </div>

      <div className="visualization-container">
        <svg ref={svgRef} className="git-graph"></svg>
      </div>

      <div className="sidebar">
        <div className="section">
          <h3>Branches</h3>
          <ul className="branch-list">
            {data.branches.map(branch => (
              <li key={branch.name} className={branch.isCurrent ? 'current' : ''}>
                {branch.name} {branch.isCurrent && '(current)'}
              </li>
            ))}
          </ul>
        </div>

        <div className="section">
          <h3>Recent Checkpoints</h3>
          <ul className="checkpoint-list">
            {data.checkpoints.slice(0, 5).map(checkpoint => (
              <li key={checkpoint.id}>
                <div className="checkpoint-info">
                  <strong>{checkpoint.description}</strong>
                  <span className="timestamp">{checkpoint.timestamp}</span>
                </div>
                <button onClick={() => handleCheckpointRestore(checkpoint.id)}>
                  Restore
                </button>
              </li>
            ))}
          </ul>
        </div>

        {selectedNode && (
          <div className="section node-details">
            <h3>Commit Details</h3>
            <div className="details">
              <p><strong>SHA:</strong> {selectedNode.sha.substring(0, 7)}</p>
              <p><strong>Message:</strong> {selectedNode.message}</p>
              <p><strong>Author:</strong> {selectedNode.author}</p>
              <p><strong>Branch:</strong> {selectedNode.branch}</p>
              {selectedNode.taskId && (
                <>
                  <p><strong>Task ID:</strong> {selectedNode.taskId}</p>
                  <button onClick={() => handleTaskRevert(selectedNode.taskId!)}>
                    Revert Task
                  </button>
                </>
              )}
              {selectedNode.agentId && (
                <p><strong>Agent:</strong> {selectedNode.agentId}</p>
              )}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .git-workflow-visualization {
          display: flex;
          flex-direction: column;
          height: 100%;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .header {
          padding: 1rem;
          border-bottom: 1px solid #e0e0e0;
        }

        .header h2 {
          margin: 0 0 1rem 0;
        }

        .stats {
          display: flex;
          gap: 2rem;
        }

        .stat {
          color: #666;
        }

        .visualization-container {
          flex: 1;
          display: flex;
          overflow: auto;
          position: relative;
        }

        .git-graph {
          background: #f9f9f9;
          border: 1px solid #e0e0e0;
        }

        .sidebar {
          width: 300px;
          padding: 1rem;
          border-left: 1px solid #e0e0e0;
          overflow-y: auto;
        }

        .section {
          margin-bottom: 2rem;
        }

        .section h3 {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
        }

        .branch-list,
        .checkpoint-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .branch-list li {
          padding: 0.5rem;
          border-radius: 4px;
        }

        .branch-list li.current {
          background: #e3f2fd;
          font-weight: bold;
        }

        .checkpoint-list li {
          padding: 0.5rem;
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          margin-bottom: 0.5rem;
        }

        .checkpoint-info {
          margin-bottom: 0.5rem;
        }

        .timestamp {
          display: block;
          font-size: 0.85rem;
          color: #666;
        }

        button {
          background: #2196f3;
          color: white;
          border: none;
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.85rem;
        }

        button:hover {
          background: #1976d2;
        }

        .node-details {
          background: #f5f5f5;
          padding: 1rem;
          border-radius: 4px;
        }

        .details p {
          margin: 0.5rem 0;
          word-break: break-all;
        }

        .loading,
        .error {
          padding: 2rem;
          text-align: center;
          color: #666;
        }
      `}</style>
    </div>
  );
};