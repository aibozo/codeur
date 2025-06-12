"""
Parallel AST analysis using ProcessPoolExecutor.

This module provides parallel processing capabilities for analyzing
multiple files concurrently, significantly improving performance on
large codebases.
"""

import os
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any
import multiprocessing as mp
from dataclasses import dataclass

# Import analyzers at module level for pickling
from .tree_sitter_analyzer import TreeSitterAnalyzer
from .ast_analyzer import FileAnalysis, Symbol


@dataclass
class AnalysisTask:
    """Represents a file analysis task."""
    file_path: str
    repo_path: str
    language: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of analyzing a file."""
    file_path: str
    analysis: Optional[FileAnalysis]
    error: Optional[str] = None
    duration: float = 0.0


def analyze_file_worker(task: AnalysisTask) -> AnalysisResult:
    """
    Worker function for parallel analysis.
    
    This function runs in a separate process and must be picklable.
    """
    start_time = time.time()
    
    try:
        # Create analyzer in the worker process
        analyzer = TreeSitterAnalyzer()
        
        # Detect language if not provided
        language = task.language
        if not language:
            language = analyzer.detect_language(task.file_path)
        
        if not language:
            return AnalysisResult(
                file_path=task.file_path,
                analysis=None,
                error=f"Unsupported language for {task.file_path}",
                duration=time.time() - start_time
            )
        
        # Analyze file
        full_path = Path(task.repo_path) / task.file_path
        analysis = analyzer.analyze_file(full_path, language)
        
        if analysis:
            # Update path to be relative
            analysis.path = task.file_path
        
        return AnalysisResult(
            file_path=task.file_path,
            analysis=analysis,
            error=None if analysis else "Analysis failed",
            duration=time.time() - start_time
        )
        
    except Exception as e:
        return AnalysisResult(
            file_path=task.file_path,
            analysis=None,
            error=str(e),
            duration=time.time() - start_time
        )


class ParallelAnalyzer:
    """
    Parallel AST analyzer using ProcessPoolExecutor.
    
    Provides significant performance improvements when analyzing
    multiple files by utilizing all available CPU cores.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize parallel analyzer.
        
        Args:
            max_workers: Maximum number of worker processes.
                        If None, uses cpu_count().
        """
        self.max_workers = max_workers or mp.cpu_count()
        self._executor = None
    
    def __enter__(self):
        """Context manager entry."""
        self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def analyze_files(
        self, 
        file_paths: List[str], 
        repo_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, AnalysisResult]:
        """
        Analyze multiple files in parallel.
        
        Args:
            file_paths: List of file paths to analyze
            repo_path: Repository root path
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        if not self._executor:
            raise RuntimeError("ParallelAnalyzer must be used as context manager")
        
        # Create tasks
        tasks = [
            AnalysisTask(file_path=fp, repo_path=repo_path)
            for fp in file_paths
        ]
        
        # Submit tasks
        future_to_task = {
            self._executor.submit(analyze_file_worker, task): task
            for task in tasks
        }
        
        # Collect results
        results = {}
        completed = 0
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results[result.file_path] = result
            except Exception as e:
                results[task.file_path] = AnalysisResult(
                    file_path=task.file_path,
                    analysis=None,
                    error=f"Worker exception: {str(e)}"
                )
            
            completed += 1
            if progress_callback:
                progress_callback(completed, len(tasks))
        
        return results
    
    def analyze_files_batch(
        self,
        file_paths: List[str],
        repo_path: str,
        batch_size: int = 50
    ) -> Dict[str, AnalysisResult]:
        """
        Analyze files in batches to avoid overwhelming the system.
        
        Args:
            file_paths: List of file paths to analyze
            repo_path: Repository root path
            batch_size: Number of files per batch
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        if not self._executor:
            raise RuntimeError("ParallelAnalyzer must be used as context manager")
        
        all_results = {}
        
        # Process in batches
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            batch_results = self.analyze_files(batch, repo_path)
            all_results.update(batch_results)
        
        return all_results
    
    def get_optimal_workers(self, num_files: int) -> int:
        """
        Calculate optimal number of workers based on file count.
        
        Args:
            num_files: Number of files to analyze
            
        Returns:
            Optimal worker count
        """
        cpu_count = mp.cpu_count()
        
        # Use fewer workers for small file counts
        if num_files < cpu_count:
            return max(1, num_files)
        
        # Leave one CPU free for the main process
        return max(1, cpu_count - 1)


class ParallelASTAnalyzer:
    """
    Enhanced AST analyzer with parallel processing support.
    
    This class wraps the existing analyzer infrastructure with
    parallel processing capabilities.
    """
    
    def __init__(self, repo_path: str, max_workers: Optional[int] = None):
        self.repo_path = Path(repo_path)
        self.max_workers = max_workers
        self._results_cache: Dict[str, FileAnalysis] = {}
    
    def analyze_directory(
        self,
        directory: str = ".",
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, FileAnalysis]:
        """
        Analyze all files in a directory in parallel.
        
        Args:
            directory: Directory to analyze (relative to repo_path)
            extensions: File extensions to include (e.g., ['.py', '.js'])
            exclude_patterns: Patterns to exclude (e.g., ['test_', '__pycache__'])
            
        Returns:
            Dictionary mapping file paths to analysis results
        """
        # Find all files
        target_dir = self.repo_path / directory
        if not target_dir.exists():
            return {}
        
        file_paths = []
        for root, dirs, files in os.walk(target_dir):
            # Filter directories
            if exclude_patterns:
                dirs[:] = [d for d in dirs if not any(p in d for p in exclude_patterns)]
            
            for file in files:
                # Check extension
                if extensions and not any(file.endswith(ext) for ext in extensions):
                    continue
                
                # Check exclude patterns
                if exclude_patterns and any(p in file for p in exclude_patterns):
                    continue
                
                # Get relative path
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.repo_path)
                file_paths.append(str(rel_path))
        
        # Analyze in parallel
        return self.analyze_files(file_paths)
    
    def analyze_files(
        self,
        file_paths: List[str],
        show_progress: bool = True
    ) -> Dict[str, FileAnalysis]:
        """
        Analyze multiple files in parallel.
        
        Args:
            file_paths: List of file paths to analyze
            show_progress: Whether to show progress
            
        Returns:
            Dictionary mapping file paths to FileAnalysis objects
        """
        # Filter out already cached files
        to_analyze = [fp for fp in file_paths if fp not in self._results_cache]
        
        if not to_analyze:
            # All files cached
            return {fp: self._results_cache[fp] for fp in file_paths}
        
        print(f"Analyzing {len(to_analyze)} files in parallel...")
        start_time = time.time()
        
        # Progress callback
        def progress(completed, total):
            if show_progress:
                pct = (completed / total) * 100
                print(f"  Progress: {completed}/{total} ({pct:.1f}%)", end='\r')
        
        # Use parallel analyzer
        with ParallelAnalyzer(max_workers=self.max_workers) as analyzer:
            results = analyzer.analyze_files(
                to_analyze,
                str(self.repo_path),
                progress_callback=progress if show_progress else None
            )
        
        if show_progress:
            print()  # New line after progress
        
        # Process results
        successful = 0
        failed = 0
        analyses = {}
        
        for file_path, result in results.items():
            if result.analysis:
                analyses[file_path] = result.analysis
                self._results_cache[file_path] = result.analysis
                successful += 1
            else:
                failed += 1
                if result.error:
                    print(f"  Failed: {file_path} - {result.error}")
        
        # Add cached results
        for fp in file_paths:
            if fp in self._results_cache and fp not in analyses:
                analyses[fp] = self._results_cache[fp]
        
        duration = time.time() - start_time
        print(f"Analyzed {successful} files in {duration:.2f}s ({failed} failed)")
        print(f"Average: {duration/len(to_analyze):.3f}s per file")
        
        return analyses
    
    def clear_cache(self):
        """Clear the results cache."""
        self._results_cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the cache."""
        return {
            "cached_files": len(self._results_cache),
            "total_symbols": sum(
                len(analysis.symbols) 
                for analysis in self._results_cache.values()
            ),
            "total_complexity": sum(
                analysis.complexity 
                for analysis in self._results_cache.values()
            )
        }