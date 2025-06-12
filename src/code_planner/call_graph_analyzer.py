"""
NetworkX-based call graph analyzer.

This module provides advanced call graph analysis using NetworkX,
supporting dependency analysis, impact analysis, and graph visualization.
"""

import networkx as nx
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class CallNode:
    """Represents a node in the call graph."""
    id: str  # file:symbol format
    file: str
    symbol: str
    kind: str  # function, method, class
    complexity: int = 1
    lines: Tuple[int, int] = (0, 0)


class CallGraphAnalyzer:
    """Analyzes code dependencies using NetworkX."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_data: Dict[str, CallNode] = {}
    
    def add_symbol(self, file: str, symbol: str, kind: str, 
                   complexity: int = 1, lines: Tuple[int, int] = (0, 0)) -> str:
        """Add a symbol to the graph."""
        node_id = f"{file}:{symbol}"
        
        # Create node data
        node = CallNode(
            id=node_id,
            file=file,
            symbol=symbol,
            kind=kind,
            complexity=complexity,
            lines=lines
        )
        
        # Add to graph
        self.graph.add_node(node_id, **node.__dict__)
        self.node_data[node_id] = node
        
        return node_id
    
    def add_call(self, caller_id: str, callee_id: str, call_type: str = "calls"):
        """Add a call relationship between two symbols."""
        self.graph.add_edge(caller_id, callee_id, type=call_type)
    
    def add_file_dependency(self, from_file: str, to_file: str, import_name: str):
        """Add a file-level dependency."""
        # Create file nodes if they don't exist
        from_id = f"{from_file}:__file__"
        to_id = f"{to_file}:__file__"
        
        if from_id not in self.graph:
            self.add_symbol(from_file, "__file__", "file")
        if to_id not in self.graph:
            self.add_symbol(to_file, "__file__", "file")
        
        self.graph.add_edge(from_id, to_id, type="imports", import_name=import_name)
    
    def get_callers(self, symbol_id: str) -> List[str]:
        """Get all symbols that call the given symbol."""
        return list(self.graph.predecessors(symbol_id))
    
    def get_callees(self, symbol_id: str) -> List[str]:
        """Get all symbols called by the given symbol."""
        return list(self.graph.successors(symbol_id))
    
    def get_impact_set(self, changed_symbols: List[str]) -> Set[str]:
        """
        Get all symbols potentially impacted by changes to the given symbols.
        
        This includes:
        - Direct callers (upstream impact)
        - Transitive callers (full upstream impact)
        """
        impact = set()
        
        for symbol in changed_symbols:
            if symbol in self.graph:
                # Get all ancestors (symbols that depend on this one)
                ancestors = nx.ancestors(self.graph, symbol)
                impact.update(ancestors)
                impact.add(symbol)  # Include the changed symbol itself
        
        return impact
    
    def get_dependency_set(self, symbols: List[str]) -> Set[str]:
        """
        Get all symbols that the given symbols depend on.
        
        This includes:
        - Direct callees (downstream dependencies)
        - Transitive callees (full downstream dependencies)
        """
        dependencies = set()
        
        for symbol in symbols:
            if symbol in self.graph:
                # Get all descendants (symbols this one depends on)
                descendants = nx.descendants(self.graph, symbol)
                dependencies.update(descendants)
        
        return dependencies
    
    def get_strongly_connected_components(self) -> List[Set[str]]:
        """Find strongly connected components (potential circular dependencies)."""
        return [set(scc) for scc in nx.strongly_connected_components(self.graph)]
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find all circular dependencies in the code."""
        cycles = []
        try:
            # Find all simple cycles
            for cycle in nx.simple_cycles(self.graph):
                if len(cycle) > 1:  # Ignore self-loops
                    cycles.append(cycle)
        except nx.NetworkXNoCycle:
            pass
        return cycles
    
    def get_complexity_metrics(self) -> Dict[str, any]:
        """Calculate various complexity metrics for the call graph."""
        metrics = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(1, self.graph.number_of_nodes()),
            "max_in_degree": max(dict(self.graph.in_degree()).values()) if self.graph.number_of_nodes() > 0 else 0,
            "max_out_degree": max(dict(self.graph.out_degree()).values()) if self.graph.number_of_nodes() > 0 else 0,
            "circular_dependencies": len(self.find_circular_dependencies()),
            "connected_components": nx.number_weakly_connected_components(self.graph),
        }
        
        # Find most complex functions (by cyclomatic complexity)
        complex_functions = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get('kind') in ('function', 'method'):
                complex_functions.append((node_id, data.get('complexity', 1)))
        
        complex_functions.sort(key=lambda x: x[1], reverse=True)
        metrics["most_complex_functions"] = complex_functions[:10]
        
        # Find most connected functions (highest degree)
        degree_dict = dict(self.graph.degree())
        connected_functions = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        metrics["most_connected_functions"] = connected_functions
        
        return metrics
    
    def get_call_path(self, from_symbol: str, to_symbol: str) -> Optional[List[str]]:
        """Find the shortest call path between two symbols."""
        try:
            return nx.shortest_path(self.graph, from_symbol, to_symbol)
        except nx.NetworkXNoPath:
            return None
    
    def export_to_json(self) -> str:
        """Export the call graph to JSON format."""
        data = {
            "nodes": [
                {
                    "id": node,
                    **self.graph.nodes[node]
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    **data
                }
                for u, v, data in self.graph.edges(data=True)
            ]
        }
        return json.dumps(data, indent=2)
    
    def export_to_dot(self) -> str:
        """Export the call graph to Graphviz DOT format."""
        lines = ["digraph CallGraph {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')
        
        # Add nodes with labels
        for node_id, data in self.graph.nodes(data=True):
            label = f"{data['symbol']}\\n({data['kind']})"
            color = {
                'class': 'lightblue',
                'function': 'lightgreen',
                'method': 'lightyellow',
                'file': 'lightgray'
            }.get(data['kind'], 'white')
            
            lines.append(f'  "{node_id}" [label="{label}", fillcolor="{color}", style="filled"];')
        
        # Add edges
        for u, v, data in self.graph.edges(data=True):
            edge_type = data.get('type', 'calls')
            style = 'dashed' if edge_type == 'imports' else 'solid'
            lines.append(f'  "{u}" -> "{v}" [style="{style}"];')
        
        lines.append("}")
        return "\n".join(lines)
    
    def get_file_dependencies(self) -> Dict[str, Set[str]]:
        """Get file-level dependencies."""
        file_deps = {}
        
        for u, v, data in self.graph.edges(data=True):
            if data.get('type') == 'imports':
                from_file = self.node_data[u].file
                to_file = self.node_data[v].file
                
                if from_file not in file_deps:
                    file_deps[from_file] = set()
                file_deps[from_file].add(to_file)
        
        return file_deps
    
    def analyze_modularity(self) -> Dict[str, float]:
        """Analyze the modularity of the codebase."""
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()
        
        # Find communities
        try:
            from networkx.algorithms import community
            communities = community.greedy_modularity_communities(undirected)
            modularity_score = community.modularity(undirected, communities)
            
            return {
                "modularity_score": modularity_score,
                "num_communities": len(communities),
                "avg_community_size": sum(len(c) for c in communities) / len(communities) if communities else 0
            }
        except ImportError:
            return {
                "modularity_score": -1,
                "error": "Community detection requires networkx[community]"
            }