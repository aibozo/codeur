"""
Agent network graph for visualizing agent relationships and message flows.

This module defines the agent dependency graph and provides data
for visualization in the dashboard. Also includes codebase search functionality.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
import asyncio
import networkx as nx

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NodeData:
    """Data associated with a graph node (agent)."""
    id: str
    label: str
    type: str  # orchestrator, planner, executor, service
    description: str
    position: Tuple[float, float]
    color: str
    icon: str


@dataclass
class EdgeData:
    """Data associated with a graph edge (relationship)."""
    source: str
    target: str
    type: str  # delegates, queries, assigns, uses, indexes
    weight: float = 1.0
    description: str = ""


class AgentGraph:
    """
    Manages the agent dependency graph for visualization.
    
    This graph represents the static structure of agent relationships
    and is used as the base for dynamic flow visualization.
    """
    
    def __init__(self):
        """Initialize the agent graph."""
        self.graph = nx.DiGraph()
        self._node_data: Dict[str, NodeData] = {}
        self._initialize_graph()
        
    def _initialize_graph(self):
        """Initialize the agent dependency graph with default structure."""
        # Define nodes with their properties
        nodes = [
            NodeData(
                id='architect',
                label='AR',
                type='orchestrator',
                description='Architect - Designs project structure and task graphs',
                position=(200, 50),
                color='#9333EA',
                icon='🏗️'
            ),
            NodeData(
                id='request_planner',
                label='RP',
                type='orchestrator',
                description='Request Planner - Orchestrates task execution',
                position=(200, 150),
                color='#FF0066',
                icon='📋'
            ),
            NodeData(
                id='code_planner',
                label='CP',
                type='planner',
                description='Code Planner - Plans implementation approach',
                position=(400, 250),
                color='#FFB800',
                icon='🔧'
            ),
            NodeData(
                id='coding_agent',
                label='CA',
                type='executor',
                description='Coding Agent - Implements code changes',
                position=(600, 250),
                color='#00FF88',
                icon='✏️'
            ),
            NodeData(
                id='rag_service',
                label='RAG',
                type='service',
                description='RAG Service - Semantic code search',
                position=(300, 400),
                color='#B794F4',
                icon='🔍'
            ),
            NodeData(
                id='git_operations',
                label='Git',
                type='service',
                description='Git Operations - Version control',
                position=(500, 400),
                color='#4299E1',
                icon='📦'
            ),
            NodeData(
                id='analyzer',
                label='AN',
                type='service',
                description='Analyzer - Automatic architecture analysis',
                position=(100, 50),
                color='#10B981',
                icon='🔬'
            ),
        ]
        
        # Add nodes to graph
        for node in nodes:
            self._node_data[node.id] = node
            self.graph.add_node(node.id, **{
                'label': node.label,
                'type': node.type,
                'description': node.description
            })
        
        # Define edges (relationships between agents)
        edges = [
            EdgeData(
                source='architect',
                target='request_planner',
                type='delegates',
                weight=1.0,
                description='Delegates task planning and execution'
            ),
            EdgeData(
                source='architect',
                target='rag_service',
                type='queries',
                weight=0.7,
                description='Queries project structure and context'
            ),
            EdgeData(
                source='request_planner',
                target='code_planner',
                type='delegates',
                weight=1.0,
                description='Delegates implementation planning'
            ),
            EdgeData(
                source='request_planner',
                target='rag_service',
                type='queries',
                weight=0.5,
                description='Queries for context'
            ),
            EdgeData(
                source='code_planner',
                target='coding_agent',
                type='assigns',
                weight=1.0,
                description='Assigns coding tasks'
            ),
            EdgeData(
                source='code_planner',
                target='rag_service',
                type='queries',
                weight=0.7,
                description='Searches for examples'
            ),
            EdgeData(
                source='coding_agent',
                target='git_operations',
                type='uses',
                weight=0.8,
                description='Commits changes'
            ),
            EdgeData(
                source='coding_agent',
                target='rag_service',
                type='queries',
                weight=0.6,
                description='Finds related code'
            ),
            EdgeData(
                source='rag_service',
                target='git_operations',
                type='indexes',
                weight=0.3,
                description='Indexes repository'
            ),
            EdgeData(
                source='analyzer',
                target='rag_service',
                type='uses',
                weight=0.8,
                description='Stores analysis results'
            ),
            EdgeData(
                source='architect',
                target='analyzer',
                type='queries',
                weight=0.6,
                description='Retrieves architecture insights'
            ),
        ]
        
        # Add edges to graph
        for edge in edges:
            self.graph.add_edge(
                edge.source,
                edge.target,
                type=edge.type,
                weight=edge.weight,
                description=edge.description
            )
    
    def get_graph_data(self, active_flows: Optional[Dict[Tuple[str, str], float]] = None) -> Dict[str, Any]:
        """
        Get graph data formatted for visualization.
        
        Args:
            active_flows: Dictionary of (source, target) -> intensity for active message flows
            
        Returns:
            Dictionary with nodes and edges formatted for frontend
        """
        nodes = []
        edges = []
        
        # Process nodes
        for node_id, node_data in self._node_data.items():
            nodes.append({
                'id': node_id,
                'label': node_data.label,
                'type': node_data.type,
                'description': node_data.description,
                'x': node_data.position[0],
                'y': node_data.position[1],
                'color': node_data.color,
                'icon': node_data.icon
            })
        
        # Process edges
        for source, target, data in self.graph.edges(data=True):
            edge_data = {
                'id': f"{source}-{target}",
                'source': source,
                'target': target,
                'type': data['type'],
                'weight': data['weight'],
                'description': data.get('description', ''),
                'active': False,
                'flow': 0
            }
            
            # Add flow information if available
            if active_flows and (source, target) in active_flows:
                edge_data['flow'] = active_flows[(source, target)]
                edge_data['active'] = edge_data['flow'] > 0
            
            edges.append(edge_data)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific node."""
        if node_id not in self._node_data:
            return None
            
        node = self._node_data[node_id]
        
        # Get connected nodes
        predecessors = list(self.graph.predecessors(node_id))
        successors = list(self.graph.successors(node_id))
        
        return {
            'id': node.id,
            'label': node.label,
            'type': node.type,
            'description': node.description,
            'position': node.position,
            'color': node.color,
            'icon': node.icon,
            'connections': {
                'incoming': predecessors,
                'outgoing': successors
            }
        }
    
    def get_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Get shortest path between two agents."""
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None
    
    def get_all_paths(self, source: str, target: str) -> List[List[str]]:
        """Get all possible paths between two agents."""
        try:
            return list(nx.all_simple_paths(self.graph, source, target))
        except nx.NetworkXNoPath:
            return []
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistical information about the graph."""
        return {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'is_dag': nx.is_directed_acyclic_graph(self.graph),
            'weakly_connected': nx.is_weakly_connected(self.graph),
            'center': list(nx.center(self.graph.to_undirected())) if nx.is_connected(self.graph.to_undirected()) else [],
            'degree_centrality': nx.degree_centrality(self.graph)
        }


# Codebase search functionality
async def search_codebase_with_graph(
    query: str,
    project_path: Path,
    file_pattern: str = "**/*.py",
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Search codebase using intelligent pattern matching.
    
    This is a simplified implementation that uses basic search.
    In a full implementation, this would integrate with the agent graph.
    
    Args:
        query: Search query
        project_path: Path to project
        file_pattern: Glob pattern for files
        max_results: Maximum results to return
    
    Returns:
        List of search results with file path, content, and relevance
    """
    results = []
    
    try:
        # Convert query to search pattern
        search_pattern = _query_to_pattern(query)
        
        # Search files
        for file_path in project_path.rglob(file_pattern):
            if file_path.is_file() and not _should_skip_file(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Search for matches
                    matches = _find_matches(content, search_pattern, query)
                    
                    if matches:
                        # Get context around matches
                        for match in matches[:2]:  # Limit matches per file
                            context = _extract_context(content, match['line_num'])
                            
                            results.append({
                                "file_path": str(file_path.relative_to(project_path)),
                                "line_number": match['line_num'],
                                "match_type": match['type'],
                                "content": context['content'],
                                "context": context['full'],
                                "relevance": match['relevance']
                            })
                            
                            if len(results) >= max_results:
                                break
                    
                except Exception as e:
                    logger.debug(f"Error reading {file_path}: {e}")
                
                if len(results) >= max_results:
                    break
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        
        return results[:max_results]
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []


def _query_to_pattern(query: str) -> Dict[str, Any]:
    """Convert natural language query to search patterns."""
    query_lower = query.lower()
    
    # Extract key terms
    patterns = {
        "exact": [],
        "fuzzy": [],
        "type": "general"
    }
    
    # Check for specific query types
    if "class" in query_lower:
        # Extract class name
        words = query.split()
        for i, word in enumerate(words):
            if word.lower() == "class" and i + 1 < len(words):
                class_name = words[i + 1].strip("?.,")
                patterns["exact"].append(f"class {class_name}")
                patterns["fuzzy"].append(class_name)
                patterns["type"] = "class"
                break
    
    elif "function" in query_lower or "def" in query_lower:
        # Extract function name
        words = query.split()
        for word in words:
            if word.isidentifier() and word not in ["function", "def", "method"]:
                patterns["exact"].append(f"def {word}")
                patterns["fuzzy"].append(word)
                patterns["type"] = "function"
                break
    
    elif "import" in query_lower:
        # Extract import
        if "from" in query_lower:
            match = re.search(r'from\s+(\S+)', query)
            if match:
                patterns["exact"].append(f"from {match.group(1)}")
                patterns["type"] = "import"
        else:
            match = re.search(r'import\s+(\S+)', query)
            if match:
                patterns["exact"].append(f"import {match.group(1)}")
                patterns["type"] = "import"
    
    else:
        # General search - extract meaningful terms
        stopwords = {"what", "is", "the", "does", "where", "how", "a", "an", "in", "of", "to", "for"}
        words = [w for w in query.split() if w.lower() not in stopwords and len(w) > 2]
        patterns["fuzzy"] = words
    
    return patterns


def _find_matches(content: str, patterns: Dict[str, Any], original_query: str) -> List[Dict[str, Any]]:
    """Find matches in content based on patterns."""
    matches = []
    lines = content.split('\n')
    
    # Search for exact patterns
    for pattern in patterns.get("exact", []):
        for i, line in enumerate(lines):
            if pattern in line:
                relevance = 10  # High relevance for exact matches
                if patterns["type"] == "class" and line.strip().startswith("class"):
                    relevance = 15  # Even higher for class definitions
                elif patterns["type"] == "function" and line.strip().startswith("def"):
                    relevance = 15
                
                matches.append({
                    "line_num": i + 1,
                    "type": patterns["type"],
                    "relevance": relevance
                })
    
    # Search for fuzzy patterns
    for term in patterns.get("fuzzy", []):
        term_lower = term.lower()
        for i, line in enumerate(lines):
            if term_lower in line.lower():
                # Calculate relevance based on context
                relevance = 5
                if line.strip().startswith(("class", "def")):
                    relevance = 8
                elif line.strip().startswith("#"):
                    relevance = 3  # Comments are less relevant
                
                # Check if already found with exact match
                if not any(m["line_num"] == i + 1 for m in matches):
                    matches.append({
                        "line_num": i + 1,
                        "type": "fuzzy",
                        "relevance": relevance
                    })
    
    return matches


def _extract_context(content: str, line_num: int, context_lines: int = 5) -> Dict[str, str]:
    """Extract context around a line number."""
    lines = content.split('\n')
    
    # Get the specific line
    if line_num <= 0 or line_num > len(lines):
        return {"content": "", "full": ""}
    
    target_line = lines[line_num - 1]
    
    # Get surrounding context
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    
    context_lines = lines[start:end]
    
    # Try to find complete function or class
    if target_line.strip().startswith(("def ", "class ")):
        # Extend to get full definition
        indent = len(target_line) - len(target_line.lstrip())
        extended_end = line_num
        
        for i in range(line_num, min(len(lines), line_num + 20)):
            line = lines[i]
            if line.strip() and not line.startswith(' ' * (indent + 1)):
                break
            extended_end = i + 1
        
        context_lines = lines[line_num - 1:extended_end]
    
    return {
        "content": target_line.strip(),
        "full": '\n'.join(context_lines)
    }


def _should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    skip_dirs = {
        "__pycache__", ".git", ".venv", "venv", "env",
        "node_modules", ".tox", ".pytest_cache", ".mypy_cache"
    }
    
    skip_patterns = {
        ".pyc", ".pyo", ".so", ".dylib", ".dll",
        ".egg-info", ".dist-info", ".coverage"
    }
    
    # Check directory
    for parent in file_path.parents:
        if parent.name in skip_dirs:
            return True
    
    # Check file patterns
    for pattern in skip_patterns:
        if pattern in str(file_path):
            return True
    
    return False