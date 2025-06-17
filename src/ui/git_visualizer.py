"""
Git History Visualizer for Multi-Agent System.

Provides visual representation of git history with task tracking,
checkpoints, and agent activity.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import re
from enum import Enum

from ..core.logging import get_logger

logger = get_logger(__name__)


class NodeType(Enum):
    """Types of nodes in git graph."""
    COMMIT = "commit"
    MERGE = "merge"
    CHECKPOINT = "checkpoint"
    TASK = "task"
    REVERT = "revert"


class Color:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


@dataclass
class GitNode:
    """Represents a node in the git graph."""
    sha: str
    short_sha: str
    node_type: NodeType
    branch: str
    message: str
    author: str
    timestamp: datetime
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    parent_shas: List[str] = None
    children_shas: List[str] = None
    is_checkpoint: bool = False
    is_current: bool = False
    metadata: Dict[str, Any] = None


@dataclass
class GitGraph:
    """Represents the complete git graph."""
    nodes: Dict[str, GitNode]
    branches: Dict[str, str]  # branch_name -> current_sha
    current_branch: str
    current_sha: str
    main_branch: str = "main"


class GitVisualizer:
    """
    Visualizes git history with enhanced information for multi-agent system.
    """
    
    def __init__(self, repo_path: str, commit_registry: Optional[Dict[str, Any]] = None):
        """Initialize git visualizer."""
        self.repo_path = Path(repo_path)
        self.commit_registry = commit_registry or {}
        
        # Visual symbols
        self.symbols = {
            'commit': '●',
            'merge': '◈',
            'checkpoint': '◆',
            'task': '◉',
            'revert': '◌',
            'branch': '│',
            'branch_merge': '├',
            'branch_end': '└',
            'horizontal': '─'
        }
        
        # Status indicators
        self.status_symbols = {
            'completed': '✓',
            'failed': '✗',
            'in_progress': '⋯',
            'reverted': '↶'
        }
    
    def generate_graph(self, max_commits: int = 50) -> GitGraph:
        """Generate complete git graph data structure."""
        # Get git log data
        log_data = self._get_git_log(max_commits)
        
        # Parse into nodes
        nodes = {}
        for entry in log_data:
            node = self._parse_log_entry(entry)
            nodes[node.sha] = node
        
        # Get branch information
        branches = self._get_branches()
        current_branch = self._get_current_branch()
        current_sha = self._get_current_sha()
        
        # Build parent-child relationships
        self._build_relationships(nodes)
        
        # Mark checkpoint nodes based on branch names
        for branch_name, sha in branches.items():
            if branch_name.startswith('checkpoint/') and sha in nodes:
                nodes[sha].is_checkpoint = True
                # Extract description from branch name
                if '-' in branch_name:
                    desc_part = branch_name.split('-', 3)[-1]  # Get part after timestamp
                    nodes[sha].message = f"Checkpoint: {desc_part.replace('-', ' ')}"
        
        return GitGraph(
            nodes=nodes,
            branches=branches,
            current_branch=current_branch,
            current_sha=current_sha
        )
    
    def render_terminal(self, graph: GitGraph, width: int = 80) -> str:
        """Render git graph for terminal display."""
        lines = []
        
        # Header
        lines.append(self._render_header(graph, width))
        lines.append("─" * width)
        
        # Branch summary
        lines.append(self._render_branch_summary(graph))
        lines.append("─" * width)
        
        # Graph visualization
        graph_lines = self._render_graph(graph)
        lines.extend(graph_lines)
        
        # Legend
        lines.append("─" * width)
        lines.append(self._render_legend())
        
        return '\n'.join(lines)
    
    def render_html(self, graph: GitGraph) -> str:
        """Render git graph as interactive HTML."""
        nodes_json = []
        edges_json = []
        
        # Convert nodes to JSON format
        for sha, node in graph.nodes.items():
            nodes_json.append({
                'id': node.short_sha,
                'label': self._get_node_label(node),
                'type': node.node_type.value,
                'branch': node.branch,
                'task_id': node.task_id,
                'agent_id': node.agent_id,
                'is_checkpoint': node.is_checkpoint,
                'is_current': node.is_current,
                'timestamp': node.timestamp.isoformat(),
                'color': self._get_node_color(node)
            })
            
            # Add edges
            for parent_sha in (node.parent_shas or []):
                if parent_sha in graph.nodes:
                    edges_json.append({
                        'from': graph.nodes[parent_sha].short_sha,
                        'to': node.short_sha
                    })
        
        # Generate HTML with vis.js
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Git History Visualization</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
    <style>
        #gitGraph {{ width: 100%; height: 600px; border: 1px solid #ddd; }}
        .info {{ padding: 10px; background: #f5f5f5; margin-top: 10px; }}
        .legend {{ display: flex; gap: 20px; margin-top: 10px; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 50%; }}
    </style>
</head>
<body>
    <h1>Git History Visualization</h1>
    <div id="gitGraph"></div>
    <div class="info">
        <strong>Current Branch:</strong> {current_branch}<br>
        <strong>Total Commits:</strong> {total_commits}<br>
        <strong>Active Tasks:</strong> {active_tasks}
    </div>
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background: #4CAF50;"></div>
            <span>Completed Task</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #2196F3;"></div>
            <span>Checkpoint</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #FF9800;"></div>
            <span>In Progress</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #F44336;"></div>
            <span>Failed/Reverted</span>
        </div>
    </div>
    
    <script>
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        
        var container = document.getElementById('gitGraph');
        var data = {{ nodes: nodes, edges: edges }};
        
        var options = {{
            layout: {{
                hierarchical: {{
                    direction: 'LR',
                    sortMethod: 'directed',
                    levelSeparation: 150
                }}
            }},
            nodes: {{
                shape: 'dot',
                size: 20,
                font: {{ size: 12 }}
            }},
            edges: {{
                arrows: 'to',
                smooth: {{ type: 'cubicBezier' }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on("selectNode", function(params) {{
            var nodeId = params.nodes[0];
            var node = nodes.get(nodeId);
            alert('Commit: ' + nodeId + '\\nTask: ' + (node.task_id || 'N/A') + 
                  '\\nAgent: ' + (node.agent_id || 'N/A'));
        }});
    </script>
</body>
</html>
"""
        
        # Count active tasks
        active_tasks = sum(1 for n in graph.nodes.values() 
                          if n.task_id and not n.is_checkpoint)
        
        return html_template.format(
            current_branch=graph.current_branch,
            total_commits=len(graph.nodes),
            active_tasks=active_tasks,
            nodes_json=json.dumps(nodes_json),
            edges_json=json.dumps(edges_json)
        )
    
    def get_task_history(self, task_id: str) -> List[GitNode]:
        """Get commit history for a specific task."""
        graph = self.generate_graph(max_commits=100)
        
        task_nodes = []
        for node in graph.nodes.values():
            if node.task_id == task_id:
                task_nodes.append(node)
        
        # Sort by timestamp
        task_nodes.sort(key=lambda n: n.timestamp)
        
        return task_nodes
    
    def get_agent_activity(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for a specific agent."""
        graph = self.generate_graph(max_commits=200)
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        commits = []
        tasks_completed = set()
        checkpoints_created = 0
        reverts = 0
        
        for node in graph.nodes.values():
            if node.agent_id == agent_id and node.timestamp > cutoff_date:
                commits.append(node)
                
                if node.task_id:
                    tasks_completed.add(node.task_id)
                
                if node.is_checkpoint:
                    checkpoints_created += 1
                
                if node.node_type == NodeType.REVERT:
                    reverts += 1
        
        return {
            'agent_id': agent_id,
            'period_days': days,
            'total_commits': len(commits),
            'tasks_completed': len(tasks_completed),
            'checkpoints_created': checkpoints_created,
            'reverts': reverts,
            'recent_commits': commits[:10]
        }
    
    def _get_git_log(self, max_commits: int) -> List[Dict[str, Any]]:
        """Get git log in JSON format."""
        try:
            # Format for easy parsing
            format_str = '%H|%h|%P|%an|%ae|%at|%s|%D'
            
            result = subprocess.run(
                ['git', 'log', f'--format={format_str}', f'--max-count={max_commits}', '--all'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            entries = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 7:
                        entries.append({
                            'sha': parts[0],
                            'short_sha': parts[1],
                            'parents': parts[2].split() if parts[2] else [],
                            'author_name': parts[3],
                            'author_email': parts[4],
                            'timestamp': int(parts[5]),
                            'message': parts[6],
                            'refs': parts[7] if len(parts) > 7 else ''
                        })
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get git log: {e}")
            return []
    
    def _parse_log_entry(self, entry: Dict[str, Any]) -> GitNode:
        """Parse log entry into GitNode."""
        # Determine node type
        node_type = NodeType.COMMIT
        if len(entry.get('parents', [])) > 1:
            node_type = NodeType.MERGE
        
        # Extract metadata from commit message
        message = entry['message']
        task_id = None
        agent_id = None
        is_checkpoint = False
        
        # Parse structured commit message
        # Look for [TASK-xxx] or Task #xxx patterns
        task_match = re.search(r'\[TASK-([^\]]+)\]|Task #(\w+[-\w]*)', message)
        if task_match:
            task_id = task_match.group(1) or task_match.group(2)
            node_type = NodeType.TASK
        
        agent_match = re.search(r'\[(\w+)\]', message)
        if agent_match:
            agent_id = agent_match.group(1).lower()
        
        if 'checkpoint' in message.lower():
            is_checkpoint = True
            node_type = NodeType.CHECKPOINT
        
        if 'revert' in message.lower():
            node_type = NodeType.REVERT
        
        # Get branch from refs
        branch = self._extract_branch_from_refs(entry.get('refs', ''))
        
        # Check if this is current commit
        is_current = entry['sha'] == self._get_current_sha()
        
        # Get additional metadata from registry
        metadata = self.commit_registry.get(entry['sha'], {})
        
        return GitNode(
            sha=entry['sha'],
            short_sha=entry['short_sha'],
            node_type=node_type,
            branch=branch,
            message=message.split('\n')[0],  # First line only
            author=entry['author_name'],
            timestamp=datetime.fromtimestamp(entry['timestamp']),
            task_id=task_id,
            agent_id=agent_id or metadata.get('agent_id'),
            parent_shas=entry.get('parents', []),
            is_checkpoint=is_checkpoint,
            is_current=is_current,
            metadata=metadata
        )
    
    def _build_relationships(self, nodes: Dict[str, GitNode]):
        """Build parent-child relationships between nodes."""
        for sha, node in nodes.items():
            node.children_shas = []
        
        for sha, node in nodes.items():
            for parent_sha in (node.parent_shas or []):
                if parent_sha in nodes:
                    if nodes[parent_sha].children_shas is None:
                        nodes[parent_sha].children_shas = []
                    nodes[parent_sha].children_shas.append(sha)
    
    def _get_branches(self) -> Dict[str, str]:
        """Get all branches and their current commits."""
        try:
            result = subprocess.run(
                ['git', 'branch', '-v', '--no-abbrev'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            branches = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Remove * for current branch
                    line = line.replace('*', '').strip()
                    parts = line.split()
                    if len(parts) >= 2:
                        branch_name = parts[0]
                        commit_sha = parts[1]
                        branches[branch_name] = commit_sha
            
            return branches
            
        except Exception as e:
            logger.error(f"Failed to get branches: {e}")
            return {}
    
    def _get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def _get_current_sha(self) -> str:
        """Get current commit SHA."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def _extract_branch_from_refs(self, refs: str) -> str:
        """Extract branch name from git refs string."""
        if not refs:
            return ""
        
        # Parse refs like "HEAD -> main, origin/main"
        for ref in refs.split(', '):
            if '->' in ref:
                # Current branch
                return ref.split('->')[-1].strip()
            elif not ref.startswith('tag:'):
                # Regular branch
                if '/' in ref:
                    return ref.split('/')[-1]
                return ref
        
        return ""
    
    def _render_header(self, graph: GitGraph, width: int) -> str:
        """Render header section."""
        title = "Git History Visualization"
        padding = (width - len(title)) // 2
        
        header = f"{' ' * padding}{Color.BOLD}{title}{Color.END}"
        
        # Add current branch info
        branch_info = f"Current: {Color.GREEN}{graph.current_branch}{Color.END}"
        if graph.current_branch != graph.main_branch:
            branch_info += f" (tracking {Color.BLUE}{graph.main_branch}{Color.END})"
        
        return f"{header}\n{branch_info}"
    
    def _render_branch_summary(self, graph: GitGraph) -> str:
        """Render branch summary."""
        lines = []
        
        # Count nodes by type
        task_count = sum(1 for n in graph.nodes.values() if n.task_id)
        checkpoint_count = sum(1 for n in graph.nodes.values() if n.is_checkpoint)
        
        lines.append(f"Branches: {len(graph.branches)} | Tasks: {task_count} | Checkpoints: {checkpoint_count}")
        
        # List active branches
        active_branches = []
        for branch, sha in graph.branches.items():
            if branch != graph.main_branch:
                symbol = "►" if branch == graph.current_branch else "•"
                active_branches.append(f"{symbol} {branch}")
        
        if active_branches:
            lines.append("Active: " + ", ".join(active_branches[:5]))
            if len(active_branches) > 5:
                lines.append(f"        ... and {len(active_branches) - 5} more")
        
        return '\n'.join(lines)
    
    def _render_graph(self, graph: GitGraph) -> List[str]:
        """Render the actual git graph."""
        lines = []
        
        # Simple linear representation for now
        # In a full implementation, this would create a proper graph layout
        
        # Start from current commit and work backwards
        current_sha = graph.current_sha
        if current_sha not in graph.nodes:
            return ["No commits to display"]
        
        visited = set()
        to_visit = [current_sha]
        
        while to_visit and len(lines) < 50:
            sha = to_visit.pop(0)
            if sha in visited or sha not in graph.nodes:
                continue
            
            visited.add(sha)
            node = graph.nodes[sha]
            
            # Render node
            line = self._render_node(node)
            lines.append(line)
            
            # Add parents to visit
            for parent_sha in (node.parent_shas or []):
                if parent_sha not in visited:
                    to_visit.append(parent_sha)
        
        return lines
    
    def _render_node(self, node: GitNode) -> str:
        """Render a single node."""
        # Symbol
        symbol = self.symbols.get(node.node_type.value, '●')
        
        # Color based on type
        if node.is_current:
            color = Color.GREEN
        elif node.is_checkpoint:
            color = Color.CYAN
        elif node.node_type == NodeType.TASK:
            color = Color.YELLOW
        elif node.node_type == NodeType.REVERT:
            color = Color.RED
        else:
            color = Color.WHITE
        
        # Build line
        parts = [
            f"{color}{symbol}{Color.END}",
            f"{node.short_sha}",
        ]
        
        # Add branch if not on main
        if node.branch and node.branch != "main":
            parts.append(f"({Color.BLUE}{node.branch}{Color.END})")
        
        # Add task info
        if node.task_id:
            parts.append(f"[{Color.YELLOW}Task {node.task_id}{Color.END}]")
        
        # Add message (truncated)
        message = node.message[:50]
        if len(node.message) > 50:
            message += "..."
        parts.append(message)
        
        # Add agent
        if node.agent_id:
            parts.append(f"<{node.agent_id}>")
        
        # Add timestamp
        time_str = node.timestamp.strftime("%m/%d %H:%M")
        parts.append(f"{Color.WHITE}({time_str}){Color.END}")
        
        return " ".join(parts)
    
    def _render_legend(self) -> str:
        """Render legend."""
        legend_items = [
            f"{self.symbols['commit']} Commit",
            f"{self.symbols['task']} Task",
            f"{self.symbols['checkpoint']} Checkpoint",
            f"{self.symbols['merge']} Merge",
            f"{self.symbols['revert']} Revert",
            f"{self.status_symbols['completed']} Completed",
            f"{self.status_symbols['failed']} Failed"
        ]
        
        return "Legend: " + " | ".join(legend_items)
    
    def _get_node_label(self, node: GitNode) -> str:
        """Get label for node in HTML visualization."""
        if node.task_id:
            return f"Task {node.task_id}"
        elif node.is_checkpoint:
            return "Checkpoint"
        else:
            return node.short_sha
    
    def _get_node_color(self, node: GitNode) -> str:
        """Get color for node in HTML visualization."""
        if node.is_checkpoint:
            return "#2196F3"  # Blue
        elif node.node_type == NodeType.TASK:
            if node.metadata.get('status') == 'completed':
                return "#4CAF50"  # Green
            else:
                return "#FF9800"  # Orange
        elif node.node_type == NodeType.REVERT:
            return "#F44336"  # Red
        else:
            return "#9E9E9E"  # Gray
            
    def get_graph_data_json(self, max_commits: int = 50) -> Dict[str, Any]:
        """
        Get graph data as JSON for frontend consumption.
        
        Returns a dictionary with nodes, edges, and metadata that can be
        easily rendered by frontend visualization libraries.
        """
        graph = self.generate_graph(max_commits)
        
        # Convert nodes to frontend-friendly format
        nodes = []
        for sha, node in graph.nodes.items():
            nodes.append({
                'id': node.short_sha,
                'sha': node.sha,
                'type': node.node_type.value,
                'label': self._get_node_label(node),
                'branch': node.branch,
                'message': node.message,
                'author': node.author,
                'timestamp': node.timestamp.isoformat(),
                'taskId': node.task_id,
                'agentId': node.agent_id,
                'isCheckpoint': node.is_checkpoint,
                'isCurrent': node.is_current,
                'color': self._get_node_color(node),
                'symbol': self.symbols.get(node.node_type.value, '●'),
                'metadata': node.metadata or {}
            })
        
        # Build edges
        edges = []
        for sha, node in graph.nodes.items():
            for parent_sha in (node.parent_shas or []):
                if parent_sha in graph.nodes:
                    edges.append({
                        'id': f"{graph.nodes[parent_sha].short_sha}-{node.short_sha}",
                        'source': graph.nodes[parent_sha].short_sha,
                        'target': node.short_sha,
                        'type': 'commit'
                    })
        
        # Branch information
        branches = []
        for branch_name, sha in graph.branches.items():
            if sha in graph.nodes:
                branches.append({
                    'name': branch_name,
                    'sha': graph.nodes[sha].short_sha,
                    'isCurrent': branch_name == graph.current_branch
                })
        
        # Task summary
        tasks = {}
        for node in graph.nodes.values():
            if node.task_id:
                if node.task_id not in tasks:
                    tasks[node.task_id] = {
                        'id': node.task_id,
                        'commits': [],
                        'agents': set(),
                        'status': 'completed',
                        'firstCommit': node.timestamp.isoformat(),
                        'lastCommit': node.timestamp.isoformat()
                    }
                
                tasks[node.task_id]['commits'].append(node.short_sha)
                if node.agent_id:
                    tasks[node.task_id]['agents'].add(node.agent_id)
                
                # Update timestamps
                if node.timestamp.isoformat() < tasks[node.task_id]['firstCommit']:
                    tasks[node.task_id]['firstCommit'] = node.timestamp.isoformat()
                if node.timestamp.isoformat() > tasks[node.task_id]['lastCommit']:
                    tasks[node.task_id]['lastCommit'] = node.timestamp.isoformat()
                
                # Check if reverted
                if node.node_type == NodeType.REVERT:
                    tasks[node.task_id]['status'] = 'reverted'
        
        # Convert sets to lists for JSON serialization
        for task in tasks.values():
            task['agents'] = list(task['agents'])
        
        # Checkpoints
        checkpoints = []
        for node in graph.nodes.values():
            if node.is_checkpoint:
                checkpoints.append({
                    'id': node.short_sha,
                    'description': node.message,
                    'timestamp': node.timestamp.isoformat(),
                    'branch': node.branch
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'branches': branches,
            'currentBranch': graph.current_branch,
            'currentCommit': graph.current_sha[:7] if graph.current_sha else None,
            'tasks': list(tasks.values()),
            'checkpoints': checkpoints,
            'stats': {
                'totalCommits': len(nodes),
                'totalTasks': len(tasks),
                'totalCheckpoints': len(checkpoints),
                'activeBranches': len(branches)
            }
        }
    
    def get_compact_history(self, max_items: int = 20) -> List[Dict[str, Any]]:
        """
        Get a compact history view for frontend sidebar or activity feed.
        
        Returns a list of recent activities with minimal information.
        """
        graph = self.generate_graph(max_items)
        
        history = []
        for sha, node in sorted(graph.nodes.items(), 
                               key=lambda x: x[1].timestamp, 
                               reverse=True)[:max_items]:
            
            # Determine activity type and icon
            activity_type = 'commit'
            icon = '📝'
            
            if node.is_checkpoint:
                activity_type = 'checkpoint'
                icon = '💾'
            elif node.task_id:
                activity_type = 'task'
                icon = '✅'
            elif node.node_type == NodeType.MERGE:
                activity_type = 'merge'
                icon = '🔀'
            elif node.node_type == NodeType.REVERT:
                activity_type = 'revert'
                icon = '↩️'
            
            history.append({
                'id': node.short_sha,
                'type': activity_type,
                'icon': icon,
                'title': node.message.split('\n')[0][:80],  # First line, truncated
                'author': node.author,
                'timestamp': node.timestamp.isoformat(),
                'relativeTime': self._format_relative_time(node.timestamp),
                'taskId': node.task_id,
                'agentId': node.agent_id,
                'branch': node.branch
            })
        
        return history
    
    def _format_relative_time(self, timestamp: datetime) -> str:
        """Format timestamp as relative time (e.g., '2 hours ago')."""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        delta = now - timestamp
        
        if delta.days > 0:
            if delta.days == 1:
                return "1 day ago"
            return f"{delta.days} days ago"
        
        hours = delta.seconds // 3600
        if hours > 0:
            if hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        
        minutes = delta.seconds // 60
        if minutes > 0:
            if minutes == 1:
                return "1 minute ago"
            return f"{minutes} minutes ago"
        
        return "just now"