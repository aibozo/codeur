"""
Demo API endpoints for Git visualization in the frontend.

This shows how to expose Git workflow visualization data through
API endpoints that can be consumed by a React frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.core.agent_factory import create_integrated_agent_system

app = FastAPI(title="Git Workflow Visualization API")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent system instance
agent_system = None


@app.on_event("startup")
async def startup():
    """Initialize the agent system on startup."""
    global agent_system
    
    # Create agent system with git workflow
    project_path = "/path/to/your/project"  # Change this to your project
    result = await create_integrated_agent_system(project_path)
    agent_system = result["factory"]
    
    print(f"Agent system initialized with working branch: {result['working_branch']}")


@app.get("/api/git/visualization")
async def get_git_visualization(max_commits: int = 50) -> Dict[str, Any]:
    """
    Get git visualization data for the frontend graph.
    
    Returns nodes, edges, and metadata for rendering with D3.js or vis.js.
    """
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        data = agent_system.get_git_visualization_data(max_commits)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/activity")
async def get_git_activity(max_items: int = 20) -> Dict[str, Any]:
    """
    Get recent git activity for activity feed.
    
    Returns a compact list of recent commits, tasks, and checkpoints.
    """
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        activities = agent_system.get_git_activity_history(max_items)
        return {
            "success": True,
            "activities": activities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/branches")
async def get_branches() -> Dict[str, Any]:
    """Get current branch information."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        # Get visualization data and extract branch info
        data = agent_system.get_git_visualization_data(max_commits=1)
        return {
            "success": True,
            "branches": data.get("branches", []),
            "currentBranch": data.get("currentBranch"),
            "workingBranch": agent_system.working_branch
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/checkpoints")
async def get_checkpoints() -> Dict[str, Any]:
    """Get all available checkpoints."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        checkpoints = agent_system.list_checkpoints()
        return {
            "success": True,
            "checkpoints": checkpoints
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/checkpoint/create")
async def create_checkpoint(description: str) -> Dict[str, Any]:
    """Create a new checkpoint."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        checkpoint = await agent_system.create_checkpoint(description)
        return {
            "success": True,
            "checkpoint": checkpoint
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/checkpoint/restore/{checkpoint_id}")
async def restore_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    """Restore to a specific checkpoint."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        success = await agent_system.restore_checkpoint(checkpoint_id)
        return {
            "success": success,
            "message": f"Restored to checkpoint {checkpoint_id}" if success else "Failed to restore"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/task/{task_id}")
async def get_task_info(task_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific task."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        info = agent_system.get_task_info(task_id)
        if not info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "success": True,
            "task": info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/task/{task_id}/revert")
async def revert_task(task_id: str, cascade: bool = True) -> Dict[str, Any]:
    """Revert a specific task."""
    if not agent_system:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    try:
        success = await agent_system.revert_task(task_id, cascade)
        return {
            "success": success,
            "message": f"Reverted task {task_id}" if success else "Failed to revert"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Example React component that would consume this API:
"""
// GitVisualization.jsx
import React, { useEffect, useState } from 'react';
import { Network } from 'vis-network/standalone';

function GitVisualization() {
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        fetchGitVisualization();
    }, []);
    
    const fetchGitVisualization = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/git/visualization');
            const result = await response.json();
            if (result.success) {
                setGraphData(result.data);
            }
        } catch (error) {
            console.error('Failed to fetch git visualization:', error);
        } finally {
            setLoading(false);
        }
    };
    
    useEffect(() => {
        if (graphData && !loading) {
            // Initialize vis.js network
            const container = document.getElementById('git-network');
            const data = {
                nodes: graphData.nodes.map(node => ({
                    id: node.id,
                    label: node.label,
                    color: node.color,
                    title: `${node.message}\n${node.timestamp}`,
                    shape: node.isCheckpoint ? 'diamond' : 'dot'
                })),
                edges: graphData.edges
            };
            
            const options = {
                layout: {
                    hierarchical: {
                        direction: 'LR',
                        sortMethod: 'directed'
                    }
                },
                physics: false,
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                }
            };
            
            new Network(container, data, options);
        }
    }, [graphData, loading]);
    
    if (loading) return <div>Loading git history...</div>;
    
    return (
        <div>
            <h2>Git Workflow Visualization</h2>
            <div className="stats">
                <span>Commits: {graphData?.stats.totalCommits}</span>
                <span>Tasks: {graphData?.stats.totalTasks}</span>
                <span>Checkpoints: {graphData?.stats.totalCheckpoints}</span>
            </div>
            <div id="git-network" style={{ height: '500px', border: '1px solid #ddd' }} />
        </div>
    );
}
"""


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Git Visualization API server...")
    print("API will be available at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)