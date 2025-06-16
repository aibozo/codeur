import React, { useState, useEffect, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { 
  ChevronDown, 
  ChevronRight, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Layers,
  GitBranch,
  Hash,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  Filter
} from 'lucide-react';

interface RAGContext {
  chunk_ids: string[];
  search_queries: string[];
  file_patterns: string[];
  symbols: string[];
}

interface TaskNode {
  id: string;
  title: string;
  description: string;
  agent_type: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'pending' | 'ready' | 'in_progress' | 'completed' | 'failed' | 'blocked';
  parent_id?: string;
  subtask_ids: string[];
  granularity: 'epic' | 'task' | 'subtask';
  community_id?: string;
  rag_context: RAGContext;
  estimated_hours: number;
  actual_hours: number;
  expanded: boolean;
  hidden: boolean;
  dependencies: string[];
  dependents: string[];
}

interface TaskCommunity {
  id: string;
  name: string;
  description: string;
  theme: string;
  color: string;
  task_ids: string[];
}

interface TaskGraphData {
  tasks: Record<string, TaskNode>;
  communities: Record<string, TaskCommunity>;
  display_mode: 'sparse' | 'focused' | 'dense' | 'custom';
  focused_task_id?: string;
  expanded_task_ids: string[];
}

type DisplayMode = 'sparse' | 'focused' | 'dense' | 'community';

interface EnhancedTaskGraphProps {
  graphData: TaskGraphData;
  onTaskClick?: (taskId: string) => void;
  onTaskExpand?: (taskId: string) => void;
  onDisplayModeChange?: (mode: DisplayMode) => void;
  onFocusTask?: (taskId: string) => void;
  className?: string;
}

const EnhancedTaskGraph: React.FC<EnhancedTaskGraphProps> = ({
  graphData,
  onTaskClick,
  onTaskExpand,
  onDisplayModeChange,
  onFocusTask,
  className = ''
}) => {
  const [displayMode, setDisplayMode] = useState<DisplayMode>(graphData.display_mode as DisplayMode);
  const [selectedCommunity, setSelectedCommunity] = useState<string | null>(null);
  const [hoveredTask, setHoveredTask] = useState<string | null>(null);
  const [svgDimensions, setSvgDimensions] = useState({ width: 800, height: 600 });

  // Get tasks to display based on mode
  const displayTasks = useMemo(() => {
    const tasks = Object.values(graphData.tasks);
    
    switch (displayMode) {
      case 'sparse':
        // Show only top-level tasks
        return tasks.filter(task => 
          !task.hidden && 
          (!task.parent_id || !graphData.tasks[task.parent_id]) &&
          task.granularity !== 'subtask'
        );
        
      case 'focused':
        // Show focused task and its immediate children
        if (!graphData.focused_task_id) return [];
        const focused = graphData.tasks[graphData.focused_task_id];
        if (!focused) return [];
        
        const focusedTasks = [focused];
        // Add children
        focused.subtask_ids.forEach(id => {
          if (graphData.tasks[id]) focusedTasks.push(graphData.tasks[id]);
        });
        // Add parent for context
        if (focused.parent_id && graphData.tasks[focused.parent_id]) {
          focusedTasks.push(graphData.tasks[focused.parent_id]);
        }
        return focusedTasks;
        
      case 'dense':
        // Show everything
        return tasks.filter(task => !task.hidden);
        
      case 'community':
        // Show tasks in selected community
        if (!selectedCommunity) return [];
        const community = graphData.communities[selectedCommunity];
        if (!community) return [];
        return tasks.filter(task => community.task_ids.includes(task.id));
        
      default:
        return tasks;
    }
  }, [displayMode, graphData, selectedCommunity]);

  // Add expanded subtasks
  const visibleTasks = useMemo(() => {
    const visible = new Set(displayTasks);
    
    // Add subtasks of expanded tasks
    displayTasks.forEach(task => {
      if (task.expanded || graphData.expanded_task_ids.includes(task.id)) {
        task.subtask_ids.forEach(subtaskId => {
          const subtask = graphData.tasks[subtaskId];
          if (subtask && !subtask.hidden) {
            visible.add(subtask);
          }
        });
      }
    });
    
    return Array.from(visible);
  }, [displayTasks, graphData]);

  // Calculate layout
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, any>();
    const links: any[] = [];
    
    // Create node objects
    visibleTasks.forEach((task, index) => {
      const node = {
        id: task.id,
        task,
        x: 0,
        y: 0,
        level: 0,
        index
      };
      nodeMap.set(task.id, node);
    });
    
    // Calculate levels and create links
    nodeMap.forEach(node => {
      const task = node.task;
      
      // Parent-child links
      if (task.parent_id && nodeMap.has(task.parent_id)) {
        const parent = nodeMap.get(task.parent_id);
        node.level = parent.level + 1;
        links.push({
          source: parent,
          target: node,
          type: 'hierarchy'
        });
      }
      
      // Dependency links
      task.dependencies.forEach(depId => {
        if (nodeMap.has(depId)) {
          links.push({
            source: nodeMap.get(depId),
            target: node,
            type: 'dependency'
          });
        }
      });
    });
    
    // Layout nodes by level
    const levels = new Map<number, any[]>();
    nodeMap.forEach(node => {
      if (!levels.has(node.level)) {
        levels.set(node.level, []);
      }
      levels.get(node.level)!.push(node);
    });
    
    // Position nodes
    const levelHeight = 120;
    const nodeWidth = 200;
    const nodeSpacing = 20;
    
    levels.forEach((nodesInLevel, level) => {
      const levelWidth = nodesInLevel.length * (nodeWidth + nodeSpacing);
      const startX = (svgDimensions.width - levelWidth) / 2;
      
      nodesInLevel.forEach((node, index) => {
        node.x = startX + index * (nodeWidth + nodeSpacing) + nodeWidth / 2;
        node.y = 50 + level * levelHeight;
      });
    });
    
    return { nodes: Array.from(nodeMap.values()), links };
  }, [visibleTasks, svgDimensions]);

  // Status colors and icons
  const getStatusStyle = (status: TaskNode['status']) => {
    switch (status) {
      case 'completed':
        return { color: '#10B981', icon: CheckCircle };
      case 'in_progress':
        return { color: '#3B82F6', icon: Clock };
      case 'failed':
      case 'blocked':
        return { color: '#EF4444', icon: AlertCircle };
      case 'ready':
        return { color: '#F59E0B', icon: CheckCircle };
      default:
        return { color: '#6B7280', icon: Clock };
    }
  };

  // Priority colors
  const getPriorityColor = (priority: TaskNode['priority']) => {
    switch (priority) {
      case 'critical': return '#DC2626';
      case 'high': return '#F59E0B';
      case 'medium': return '#3B82F6';
      case 'low': return '#6B7280';
    }
  };

  // Handle display mode change
  const handleDisplayModeChange = (mode: DisplayMode) => {
    setDisplayMode(mode);
    onDisplayModeChange?.(mode);
  };

  // Render task node
  const renderTaskNode = (node: any) => {
    const task = node.task;
    const statusStyle = getStatusStyle(task.status);
    const StatusIcon = statusStyle.icon;
    const hasSubtasks = task.subtask_ids.length > 0;
    const isExpanded = task.expanded || graphData.expanded_task_ids.includes(task.id);
    const community = task.community_id ? graphData.communities[task.community_id] : null;
    
    return (
      <g
        key={task.id}
        transform={`translate(${node.x - 90}, ${node.y - 35})`}
        className="cursor-pointer"
        onClick={() => onTaskClick?.(task.id)}
        onMouseEnter={() => setHoveredTask(task.id)}
        onMouseLeave={() => setHoveredTask(null)}
      >
        {/* Task box */}
        <rect
          width={180}
          height={70}
          rx={8}
          fill={hoveredTask === task.id ? '#374151' : '#1F2937'}
          stroke={community ? community.color : statusStyle.color}
          strokeWidth={2}
          className="transition-all duration-200"
        />
        
        {/* Priority indicator */}
        <rect
          x={0}
          y={0}
          width={4}
          height={70}
          rx={2}
          fill={getPriorityColor(task.priority)}
        />
        
        {/* Task content */}
        <text x={12} y={25} fill="#E5E7EB" fontSize={14} fontWeight={500}>
          {task.title.length > 20 ? task.title.substring(0, 20) + '...' : task.title}
        </text>
        
        {/* Granularity badge */}
        <text x={12} y={45} fill="#9CA3AF" fontSize={11}>
          {task.granularity.toUpperCase()} • {task.agent_type}
        </text>
        
        {/* Status icon */}
        <g transform={`translate(150, 10)`}>
          <StatusIcon size={16} color={statusStyle.color} />
        </g>
        
        {/* Subtask indicator */}
        {hasSubtasks && (
          <g
            transform={`translate(150, 35)`}
            onClick={(e) => {
              e.stopPropagation();
              onTaskExpand?.(task.id);
            }}
          >
            {isExpanded ? (
              <ChevronDown size={16} color="#9CA3AF" />
            ) : (
              <ChevronRight size={16} color="#9CA3AF" />
            )}
            <text x={-15} y={4} fill="#9CA3AF" fontSize={10}>
              {task.subtask_ids.length}
            </text>
          </g>
        )}
        
        {/* RAG indicator */}
        {task.rag_context.chunk_ids.length > 0 && (
          <g transform={`translate(12, 52)`}>
            <Hash size={12} color="#9333EA" />
            <text x={15} y={9} fill="#9333EA" fontSize={10}>
              {task.rag_context.chunk_ids.length}
            </text>
          </g>
        )}
      </g>
    );
  };

  return (
    <div className={`relative ${className}`}>
      {/* Controls */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        {/* Display mode buttons */}
        <div className="bg-slate-800 rounded-lg p-1 flex gap-1">
          <button
            onClick={() => handleDisplayModeChange('sparse')}
            className={`p-2 rounded ${displayMode === 'sparse' ? 'bg-slate-700' : 'hover:bg-slate-700'}`}
            title="Sparse View"
          >
            <Minimize2 size={16} />
          </button>
          <button
            onClick={() => handleDisplayModeChange('dense')}
            className={`p-2 rounded ${displayMode === 'dense' ? 'bg-slate-700' : 'hover:bg-slate-700'}`}
            title="Dense View"
          >
            <Maximize2 size={16} />
          </button>
          <button
            onClick={() => handleDisplayModeChange('focused')}
            className={`p-2 rounded ${displayMode === 'focused' ? 'bg-slate-700' : 'hover:bg-slate-700'}`}
            title="Focused View"
          >
            <Eye size={16} />
          </button>
          <button
            onClick={() => handleDisplayModeChange('community')}
            className={`p-2 rounded ${displayMode === 'community' ? 'bg-slate-700' : 'hover:bg-slate-700'}`}
            title="Community View"
          >
            <Layers size={16} />
          </button>
        </div>
        
        {/* Community selector */}
        {displayMode === 'community' && (
          <select
            value={selectedCommunity || ''}
            onChange={(e) => setSelectedCommunity(e.target.value)}
            className="bg-slate-800 text-white px-3 py-1 rounded"
          >
            <option value="">Select Community</option>
            {Object.values(graphData.communities).map(community => (
              <option key={community.id} value={community.id}>
                {community.name}
              </option>
            ))}
          </select>
        )}
      </div>
      
      {/* Task count */}
      <div className="absolute top-4 right-4 z-10 bg-slate-800 px-3 py-1 rounded text-sm text-gray-400">
        {visibleTasks.length} / {Object.keys(graphData.tasks).length} tasks
      </div>
      
      {/* SVG Graph */}
      <svg
        width={svgDimensions.width}
        height={svgDimensions.height}
        className="w-full h-full"
      >
        <defs>
          {/* Arrow markers for links */}
          <marker
            id="arrow-dependency"
            markerWidth={10}
            markerHeight={10}
            refX={9}
            refY={3}
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M0,0 L0,6 L9,3 z" fill="#6B7280" />
          </marker>
          <marker
            id="arrow-hierarchy"
            markerWidth={10}
            markerHeight={10}
            refX={9}
            refY={3}
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M0,0 L0,6 L9,3 z" fill="#4B5563" />
          </marker>
        </defs>
        
        {/* Links */}
        <g className="links">
          {links.map((link, index) => (
            <line
              key={index}
              x1={link.source.x}
              y1={link.source.y}
              x2={link.target.x}
              y2={link.target.y}
              stroke={link.type === 'hierarchy' ? '#4B5563' : '#6B7280'}
              strokeWidth={link.type === 'hierarchy' ? 2 : 1}
              strokeDasharray={link.type === 'dependency' ? '5,5' : ''}
              markerEnd={`url(#arrow-${link.type})`}
              opacity={0.6}
            />
          ))}
        </g>
        
        {/* Nodes */}
        <g className="nodes">
          {nodes.map(renderTaskNode)}
        </g>
      </svg>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-slate-800/90 p-3 rounded-lg text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-600 rounded" />
            <span className="text-gray-400">Critical</span>
          </div>
          <div className="flex items-center gap-1">
            <CheckCircle size={12} className="text-green-500" />
            <span className="text-gray-400">Complete</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock size={12} className="text-blue-500" />
            <span className="text-gray-400">In Progress</span>
          </div>
          <div className="flex items-center gap-1">
            <Hash size={12} className="text-purple-500" />
            <span className="text-gray-400">RAG Context</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedTaskGraph;