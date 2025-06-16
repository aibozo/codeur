import React, { useEffect, useRef, useState } from 'react';
import { GitBranch, CheckCircle, Clock, AlertCircle, Lock } from 'lucide-react';

interface TaskNode {
  id: string;
  title: string;
  description: string;
  agent_type: string;
  status: string;
  priority: string;
  dependencies: string[];
  dependents: string[];
  x?: number;
  y?: number;
}

interface TaskGraphProps {
  tasks: Record<string, TaskNode>;
  onTaskClick?: (taskId: string) => void;
}

const TaskGraph: React.FC<TaskGraphProps> = ({ tasks, onTaskClick }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredTask, setHoveredTask] = useState<string | null>(null);
  const [taskPositions, setTaskPositions] = useState<Record<string, { x: number; y: number }>>({});

  // Status colors
  const statusColors = {
    pending: '#6B7280',
    ready: '#3B82F6',
    in_progress: '#8B5CF6',
    completed: '#10B981',
    failed: '#EF4444',
    blocked: '#F59E0B',
  };

  // Priority colors
  const priorityBorders = {
    critical: '#DC2626',
    high: '#F59E0B',
    medium: '#3B82F6',
    low: '#6B7280',
  };

  // Calculate task positions using a simple force-directed layout
  useEffect(() => {
    const taskIds = Object.keys(tasks);
    if (taskIds.length === 0) return;

    const positions: Record<string, { x: number; y: number }> = {};
    const width = 800;
    const height = 600;
    const nodeRadius = 40;

    // Initialize positions randomly
    taskIds.forEach((id, index) => {
      positions[id] = {
        x: Math.random() * (width - 2 * nodeRadius) + nodeRadius,
        y: Math.random() * (height - 2 * nodeRadius) + nodeRadius,
      };
    });

    // Simple force simulation
    for (let iteration = 0; iteration < 100; iteration++) {
      const forces: Record<string, { x: number; y: number }> = {};
      
      // Initialize forces
      taskIds.forEach(id => {
        forces[id] = { x: 0, y: 0 };
      });

      // Repulsion between all nodes
      for (let i = 0; i < taskIds.length; i++) {
        for (let j = i + 1; j < taskIds.length; j++) {
          const id1 = taskIds[i];
          const id2 = taskIds[j];
          const dx = positions[id2].x - positions[id1].x;
          const dy = positions[id2].y - positions[id1].y;
          const distance = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 5000 / (distance * distance);
          
          forces[id1].x -= (dx / distance) * force;
          forces[id1].y -= (dy / distance) * force;
          forces[id2].x += (dx / distance) * force;
          forces[id2].y += (dy / distance) * force;
        }
      }

      // Attraction along edges
      taskIds.forEach(id => {
        const task = tasks[id];
        task.dependencies.forEach(depId => {
          if (positions[depId]) {
            const dx = positions[depId].x - positions[id].x;
            const dy = positions[depId].y - positions[id].y;
            const distance = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = distance * 0.1;
            
            forces[id].x += (dx / distance) * force;
            forces[id].y += (dy / distance) * force;
            forces[depId].x -= (dx / distance) * force;
            forces[depId].y -= (dy / distance) * force;
          }
        });
      });

      // Apply forces with damping
      taskIds.forEach(id => {
        positions[id].x += forces[id].x * 0.01;
        positions[id].y += forces[id].y * 0.01;
        
        // Keep within bounds
        positions[id].x = Math.max(nodeRadius, Math.min(width - nodeRadius, positions[id].x));
        positions[id].y = Math.max(nodeRadius, Math.min(height - nodeRadius, positions[id].y));
      });
    }

    setTaskPositions(positions);
  }, [tasks]);

  // Draw the graph
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw edges (dependencies)
    Object.entries(tasks).forEach(([taskId, task]) => {
      const startPos = taskPositions[taskId];
      if (!startPos) return;

      task.dependencies.forEach(depId => {
        const endPos = taskPositions[depId];
        if (!endPos) return;

        ctx.beginPath();
        ctx.moveTo(startPos.x, startPos.y);
        ctx.lineTo(endPos.x, endPos.y);
        ctx.strokeStyle = '#4B5563';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw arrowhead
        const angle = Math.atan2(startPos.y - endPos.y, startPos.x - endPos.x);
        const arrowLength = 10;
        ctx.beginPath();
        ctx.moveTo(startPos.x - 40 * Math.cos(angle), startPos.y - 40 * Math.sin(angle));
        ctx.lineTo(
          startPos.x - 40 * Math.cos(angle) - arrowLength * Math.cos(angle - Math.PI / 6),
          startPos.y - 40 * Math.sin(angle) - arrowLength * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
          startPos.x - 40 * Math.cos(angle) - arrowLength * Math.cos(angle + Math.PI / 6),
          startPos.y - 40 * Math.sin(angle) - arrowLength * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fillStyle = '#4B5563';
        ctx.fill();
      });
    });
  }, [tasks, taskPositions]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5" />;
      case 'in_progress':
        return <Clock className="w-5 h-5 animate-pulse" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5" />;
      case 'blocked':
        return <Lock className="w-5 h-5" />;
      default:
        return <GitBranch className="w-5 h-5" />;
    }
  };

  return (
    <div className="relative w-full h-[600px] bg-slate-800 rounded-lg overflow-hidden">
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="absolute inset-0"
      />
      
      {/* Render task nodes */}
      {Object.entries(tasks).map(([taskId, task]) => {
        const pos = taskPositions[taskId];
        if (!pos) return null;

        const isHovered = hoveredTask === taskId;
        const statusColor = statusColors[task.status] || statusColors.pending;
        const priorityColor = priorityBorders[task.priority] || priorityBorders.medium;

        return (
          <div
            key={taskId}
            className={`absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-200 ${
              isHovered ? 'scale-110 z-10' : ''
            }`}
            style={{
              left: `${pos.x}px`,
              top: `${pos.y}px`,
            }}
            onMouseEnter={() => setHoveredTask(taskId)}
            onMouseLeave={() => setHoveredTask(null)}
            onClick={() => onTaskClick?.(taskId)}
          >
            <div
              className={`w-20 h-20 rounded-full flex items-center justify-center cursor-pointer shadow-lg border-2`}
              style={{
                backgroundColor: `${statusColor}20`,
                borderColor: priorityColor,
              }}
            >
              <div className="text-center">
                <div style={{ color: statusColor }}>{getStatusIcon(task.status)}</div>
                <div className="text-xs text-white mt-1 font-medium">
                  {task.agent_type.split('_').map(w => w[0].toUpperCase()).join('')}
                </div>
              </div>
            </div>
            
            {/* Tooltip */}
            {isHovered && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 bg-slate-700 rounded-lg shadow-xl p-3 pointer-events-none">
                <h4 className="font-semibold text-white text-sm mb-1">{task.title}</h4>
                <p className="text-xs text-gray-300 mb-2">{task.description}</p>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Status: <span style={{ color: statusColor }}>{task.status}</span></span>
                  <span className="text-gray-400">Priority: <span style={{ color: priorityColor }}>{task.priority}</span></span>
                </div>
              </div>
            )}
          </div>
        );
      })}
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-slate-700/90 rounded-lg p-3">
        <h4 className="text-xs font-semibold text-white mb-2">Task Status</h4>
        <div className="space-y-1">
          {Object.entries(statusColors).map(([status, color]) => (
            <div key={status} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-xs text-gray-300">{status.replace('_', ' ')}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TaskGraph;