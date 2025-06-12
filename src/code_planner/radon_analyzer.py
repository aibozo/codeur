"""
Radon-based complexity analyzer for Python code.

This module provides advanced Python-specific complexity metrics
using the Radon library, including:
- Cyclomatic complexity
- Halstead metrics
- Maintainability index
- Raw metrics (LOC, LLOC, SLOC, etc.)
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import ast

try:
    from radon.complexity import cc_visit, cc_rank, ComplexityVisitor
    from radon.metrics import h_visit, mi_visit, mi_rank
    from radon.raw import analyze
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    print("Warning: Radon not available. Install with 'pip install radon'")


class RadonComplexityAnalyzer:
    """
    Advanced complexity analyzer using Radon for Python files.
    
    Provides detailed complexity metrics including:
    - Cyclomatic complexity (McCabe)
    - Halstead metrics (effort, volume, difficulty)
    - Maintainability index
    - Raw code metrics (LOC, LLOC, comments, etc.)
    """
    
    def __init__(self):
        """Initialize the Radon analyzer."""
        if not RADON_AVAILABLE:
            raise ImportError("Radon is not installed. Run: pip install radon")
    
    def analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a Python file using Radon.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary containing all complexity metrics or None if analysis fails
        """
        if not file_path.exists() or not file_path.suffix == '.py':
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Get all metrics
            result = {
                'cyclomatic_complexity': self._get_cyclomatic_complexity(content),
                'halstead_metrics': self._get_halstead_metrics(content),
                'maintainability_index': self._get_maintainability_index(content),
                'raw_metrics': self._get_raw_metrics(content),
                'functions': self._get_function_complexities(content)
            }
            
            # Calculate aggregate complexity score
            result['total_complexity'] = self._calculate_total_complexity(result)
            
            return result
            
        except Exception as e:
            print(f"Failed to analyze {file_path}: {e}")
            return None
    
    def _get_cyclomatic_complexity(self, code: str) -> Dict[str, Any]:
        """
        Get cyclomatic complexity metrics.
        
        Returns:
            Dictionary with overall and per-function complexity
        """
        try:
            # Get complexity blocks
            blocks = cc_visit(code)
            
            # Calculate metrics
            total_complexity = sum(block.complexity for block in blocks)
            avg_complexity = total_complexity / len(blocks) if blocks else 0
            max_complexity = max((block.complexity for block in blocks), default=0)
            
            # Get complexity distribution
            distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
            for block in blocks:
                rank = cc_rank(block.complexity)
                distribution[rank] += 1
            
            return {
                'total': total_complexity,
                'average': round(avg_complexity, 2),
                'max': max_complexity,
                'blocks': len(blocks),
                'distribution': distribution
            }
        except:
            return {
                'total': 0,
                'average': 0,
                'max': 0,
                'blocks': 0,
                'distribution': {}
            }
    
    def _get_halstead_metrics(self, code: str) -> Dict[str, Any]:
        """
        Get Halstead complexity metrics.
        
        Returns:
            Dictionary with Halstead metrics
        """
        try:
            h_metrics = h_visit(code)
            
            # Check if we got valid metrics
            if hasattr(h_metrics, 'volume'):
                return {
                    'volume': round(h_metrics.volume, 2),
                    'difficulty': round(h_metrics.difficulty, 2),
                    'effort': round(h_metrics.effort, 2),
                    'time': round(h_metrics.time, 2),
                    'bugs': round(h_metrics.bugs, 3),
                    'vocabulary': h_metrics.vocabulary,
                    'length': h_metrics.length,
                    'calculated_length': round(h_metrics.calculated_length, 2)
                }
            else:
                # h_visit might return a list of metrics for multiple functions
                total_volume = 0
                total_effort = 0
                total_bugs = 0
                
                if isinstance(h_metrics, list):
                    for metric in h_metrics:
                        if hasattr(metric, 'volume'):
                            total_volume += metric.volume
                            total_effort += metric.effort
                            total_bugs += metric.bugs
                
                # If we still have no metrics, return defaults
                if total_volume == 0:
                    return {
                        'volume': 0,
                        'difficulty': 0,
                        'effort': 0,
                        'time': 0,
                        'bugs': 0,
                        'vocabulary': 0,
                        'length': 0,
                        'calculated_length': 0
                    }
                
                return {
                    'volume': round(total_volume, 2),
                    'difficulty': 0,  # Can't aggregate difficulty
                    'effort': round(total_effort, 2),
                    'time': round(total_effort / 18, 2),  # Standard conversion
                    'bugs': round(total_bugs, 3),
                    'vocabulary': 0,
                    'length': 0,
                    'calculated_length': 0
                }
        except Exception as e:
            # For debugging
            import traceback
            traceback.print_exc()
            return {
                'volume': 0,
                'difficulty': 0,
                'effort': 0,
                'time': 0,
                'bugs': 0,
                'vocabulary': 0,
                'length': 0,
                'calculated_length': 0
            }
    
    def _get_maintainability_index(self, code: str) -> Dict[str, Any]:
        """
        Get maintainability index.
        
        Returns:
            Dictionary with maintainability metrics
        """
        try:
            mi_score = mi_visit(code, multi=True)
            rank = mi_rank(mi_score)
            
            return {
                'score': round(mi_score, 2),
                'rank': rank,
                'maintainable': mi_score >= 20,
                'description': self._get_mi_description(rank)
            }
        except:
            return {
                'score': 0,
                'rank': 'F',
                'maintainable': False,
                'description': 'Unable to calculate'
            }
    
    def _get_mi_description(self, rank: str) -> str:
        """Get human-readable description for maintainability rank."""
        descriptions = {
            'A': 'Very high maintainability',
            'B': 'High maintainability',
            'C': 'Moderate maintainability',
            'D': 'Low maintainability',
            'E': 'Very low maintainability',
            'F': 'Unmaintainable'
        }
        return descriptions.get(rank, 'Unknown')
    
    def _get_raw_metrics(self, code: str) -> Dict[str, Any]:
        """
        Get raw code metrics.
        
        Returns:
            Dictionary with LOC, comments, etc.
        """
        try:
            raw = analyze(code)
            
            return {
                'loc': raw.loc,           # Lines of code
                'lloc': raw.lloc,         # Logical lines of code
                'sloc': raw.sloc,         # Source lines of code
                'comments': raw.comments,
                'single_comments': raw.single_comments,
                'multi': raw.multi,       # Multi-line strings
                'blank': raw.blank,       # Blank lines
                'comment_ratio': round(raw.comments / raw.sloc if raw.sloc > 0 else 0, 2)
            }
        except:
            return {
                'loc': 0,
                'lloc': 0,
                'sloc': 0,
                'comments': 0,
                'single_comments': 0,
                'multi': 0,
                'blank': 0,
                'comment_ratio': 0
            }
    
    def _get_function_complexities(self, code: str) -> List[Dict[str, Any]]:
        """
        Get complexity for each function/method.
        
        Returns:
            List of function complexity details
        """
        try:
            blocks = cc_visit(code)
            
            functions = []
            for block in blocks:
                # Determine block type
                block_type = 'function'
                if hasattr(block, 'is_method') and block.is_method:
                    block_type = 'method'
                elif block.__class__.__name__ == 'Class':
                    block_type = 'class'
                
                functions.append({
                    'name': block.name,
                    'type': block_type,
                    'complexity': block.complexity,
                    'rank': cc_rank(block.complexity),
                    'lineno': block.lineno,
                    'endline': block.endline,
                    'classname': getattr(block, 'classname', None)
                })
            
            # Sort by complexity (highest first)
            functions.sort(key=lambda x: x['complexity'], reverse=True)
            
            return functions
        except Exception as e:
            import traceback
            traceback.print_exc()
            return []
    
    def _calculate_total_complexity(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate an aggregate complexity score.
        
        This combines various metrics into a single score for comparison.
        """
        # Weights for different metrics
        cc_weight = 0.4  # Cyclomatic complexity
        mi_weight = 0.3  # Maintainability index
        h_weight = 0.3   # Halstead effort
        
        # Normalize cyclomatic complexity (assume 10 is high)
        cc_score = min(metrics['cyclomatic_complexity']['average'] / 10, 1.0)
        
        # Normalize maintainability index (100 to 0 scale, invert)
        mi_score = 1.0 - (metrics['maintainability_index']['score'] / 100)
        
        # Normalize Halstead effort (assume 1000 is high)
        h_score = min(metrics['halstead_metrics']['effort'] / 1000, 1.0)
        
        # Calculate weighted score
        total = (cc_score * cc_weight + 
                mi_score * mi_weight + 
                h_score * h_weight)
        
        return round(total * 100, 2)  # Convert to 0-100 scale
    
    def analyze_directory(self, directory: Path) -> Dict[str, Dict[str, Any]]:
        """
        Analyze all Python files in a directory.
        
        Args:
            directory: Directory path
            
        Returns:
            Dictionary mapping file paths to their metrics
        """
        results = {}
        
        for py_file in directory.rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            metrics = self.analyze_file(py_file)
            if metrics:
                results[str(py_file)] = metrics
        
        return results
    
    def get_summary_stats(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for multiple file analyses.
        
        Args:
            analyses: Dictionary of file analyses
            
        Returns:
            Summary statistics
        """
        if not analyses:
            return {}
        
        # Aggregate metrics
        total_complexity = sum(a['cyclomatic_complexity']['total'] for a in analyses.values())
        total_loc = sum(a['raw_metrics']['sloc'] for a in analyses.values())
        all_functions = []
        for a in analyses.values():
            all_functions.extend(a['functions'])
        
        # Find most complex functions
        most_complex = sorted(all_functions, key=lambda x: x['complexity'], reverse=True)[:10]
        
        # Calculate averages
        avg_mi = sum(a['maintainability_index']['score'] for a in analyses.values()) / len(analyses)
        avg_complexity = sum(a['cyclomatic_complexity']['average'] for a in analyses.values()) / len(analyses)
        
        return {
            'total_files': len(analyses),
            'total_complexity': total_complexity,
            'total_sloc': total_loc,
            'average_maintainability': round(avg_mi, 2),
            'average_complexity': round(avg_complexity, 2),
            'most_complex_functions': most_complex,
            'total_functions': len(all_functions),
            'complexity_distribution': self._aggregate_distributions(analyses)
        }
    
    def _aggregate_distributions(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """Aggregate complexity distributions across files."""
        total_dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
        
        for analysis in analyses.values():
            dist = analysis['cyclomatic_complexity']['distribution']
            for rank, count in dist.items():
                total_dist[rank] += count
        
        return total_dist


class RadonIntegration:
    """
    Integration layer for Radon analyzer with existing AST analyzer.
    
    Enhances Python analysis with Radon's advanced metrics while
    maintaining compatibility with the existing system.
    """
    
    def __init__(self):
        """Initialize Radon integration."""
        self.analyzer = RadonComplexityAnalyzer() if RADON_AVAILABLE else None
    
    def enhance_python_analysis(self, file_path: str, base_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance Python file analysis with Radon metrics.
        
        Args:
            file_path: Path to Python file
            base_analysis: Existing analysis from tree-sitter/AST
            
        Returns:
            Enhanced analysis with Radon metrics
        """
        if not self.analyzer or not file_path.endswith('.py'):
            return base_analysis
        
        # Get Radon metrics
        radon_metrics = self.analyzer.analyze_file(Path(file_path))
        if not radon_metrics:
            return base_analysis
        
        # Enhance the analysis
        enhanced = base_analysis.copy()
        
        # Add Radon metrics
        enhanced['radon_metrics'] = radon_metrics
        
        # Update complexity scores with Radon's more accurate values
        if 'symbols' in enhanced:
            # Map function complexities
            func_complexities = {f['name']: f['complexity'] 
                               for f in radon_metrics['functions']}
            
            for symbol in enhanced['symbols']:
                if symbol.get('kind') in ['function', 'method']:
                    symbol_name = symbol['name'].split('.')[-1]  # Get just function name
                    if symbol_name in func_complexities:
                        symbol['complexity'] = func_complexities[symbol_name]
                        symbol['complexity_rank'] = cc_rank(func_complexities[symbol_name])
        
        # Update overall complexity
        enhanced['complexity'] = radon_metrics['total_complexity']
        enhanced['maintainability_score'] = radon_metrics['maintainability_index']['score']
        
        return enhanced
    
    def get_complexity_report(self, file_path: str) -> str:
        """
        Generate a human-readable complexity report.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Formatted complexity report
        """
        if not self.analyzer:
            return "Radon not available"
        
        metrics = self.analyzer.analyze_file(Path(file_path))
        if not metrics:
            return "Unable to analyze file"
        
        report = []
        report.append(f"Complexity Report for {file_path}")
        report.append("=" * 50)
        
        # Maintainability
        mi = metrics['maintainability_index']
        report.append(f"\nMaintainability Index: {mi['score']} ({mi['rank']}) - {mi['description']}")
        
        # Cyclomatic Complexity
        cc = metrics['cyclomatic_complexity']
        report.append(f"\nCyclomatic Complexity:")
        report.append(f"  Total: {cc['total']}")
        report.append(f"  Average: {cc['average']}")
        report.append(f"  Max: {cc['max']}")
        
        # Halstead Metrics
        h = metrics['halstead_metrics']
        report.append(f"\nHalstead Metrics:")
        report.append(f"  Volume: {h['volume']}")
        report.append(f"  Difficulty: {h['difficulty']}")
        report.append(f"  Effort: {h['effort']}")
        report.append(f"  Estimated bugs: {h['bugs']}")
        
        # Raw Metrics
        raw = metrics['raw_metrics']
        report.append(f"\nCode Metrics:")
        report.append(f"  Lines of code: {raw['sloc']}")
        report.append(f"  Comments: {raw['comments']} ({raw['comment_ratio']*100:.1f}%)")
        
        # Most complex functions
        if metrics['functions']:
            report.append(f"\nMost Complex Functions:")
            for func in metrics['functions'][:5]:
                report.append(f"  {func['name']}: {func['complexity']} ({func['rank']})")
        
        return "\n".join(report)