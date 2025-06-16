"""
Adaptive Semantic Similarity Gating System.

This module provides sophisticated similarity gating with:
- Rolling statistics for outlier resilience
- Project-specific threshold adaptation
- Quality feedback integration
- Context blindspot detection
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json
from pathlib import Path
import logging

from ..core.logging import get_logger

logger = get_logger(__name__)


class RetrievalResult(NamedTuple):
    """Result from a retrieval operation."""
    chunk_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    included: bool
    reason: str


@dataclass
class GatingStatistics:
    """Rolling statistics for similarity gating."""
    # Rolling windows
    similarity_scores: deque = field(default_factory=lambda: deque(maxlen=1000))
    inclusion_rates: deque = field(default_factory=lambda: deque(maxlen=100))
    quality_scores: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Adaptive thresholds
    base_threshold: float = 0.7
    current_threshold: float = 0.7
    min_threshold: float = 0.5
    max_threshold: float = 0.9
    
    # Statistics
    rolling_mean: float = 0.7
    rolling_std: float = 0.1
    rolling_median: float = 0.7
    mad: float = 0.05  # Median Absolute Deviation
    
    # Quality metrics
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    precision: float = 1.0
    recall: float = 1.0
    
    # Counts
    total_retrievals: int = 0
    total_included: int = 0
    total_excluded: int = 0
    
    def update_statistics(self, scores: List[float]):
        """Update rolling statistics with new scores."""
        self.similarity_scores.extend(scores)
        
        if len(self.similarity_scores) >= 10:
            scores_array = np.array(self.similarity_scores)
            self.rolling_mean = np.mean(scores_array)
            self.rolling_std = np.std(scores_array)
            self.rolling_median = np.median(scores_array)
            
            # Calculate MAD (Median Absolute Deviation)
            deviations = np.abs(scores_array - self.rolling_median)
            self.mad = np.median(deviations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "base_threshold": self.base_threshold,
            "current_threshold": self.current_threshold,
            "rolling_mean": self.rolling_mean,
            "rolling_std": self.rolling_std,
            "rolling_median": self.rolling_median,
            "mad": self.mad,
            "precision": self.precision,
            "recall": self.recall,
            "total_retrievals": self.total_retrievals,
            "total_included": self.total_included,
            "total_excluded": self.total_excluded
        }


@dataclass
class ProjectGatingProfile:
    """Project-specific gating configuration and history."""
    project_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Statistics per retrieval type
    statistics: Dict[str, GatingStatistics] = field(default_factory=dict)
    
    # Feedback history
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Custom rules
    inclusion_rules: List[Dict[str, Any]] = field(default_factory=list)
    exclusion_rules: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance tracking
    avg_chunks_per_retrieval: float = 5.0
    target_chunks_per_retrieval: float = 5.0
    context_quality_score: float = 0.8


class AdaptiveSimilarityGate:
    """
    Adaptive similarity gating with rolling statistics and quality feedback.
    
    Features:
    - Outlier-resistant thresholding using rolling statistics
    - Project-specific threshold adaptation
    - Quality feedback integration
    - Multiple statistical methods for robustness
    """
    
    def __init__(self, 
                 profiles_dir: Optional[Path] = None,
                 adaptation_rate: float = 0.1,
                 outlier_method: str = "mad"):
        """
        Initialize the adaptive similarity gate.
        
        Args:
            profiles_dir: Directory to store project profiles
            adaptation_rate: How quickly to adapt thresholds (0-1)
            outlier_method: Method for outlier detection ("mad", "iqr", "zscore")
        """
        self.profiles_dir = profiles_dir or Path.home() / ".agent" / "similarity_profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.adaptation_rate = adaptation_rate
        self.outlier_method = outlier_method
        
        # Project profiles cache
        self.profiles: Dict[str, ProjectGatingProfile] = {}
        
        # Load existing profiles
        self._load_profiles()
        
        logger.info(f"Initialized adaptive similarity gate with {len(self.profiles)} profiles")
    
    def filter_results(self,
                      results: List[Dict[str, Any]],
                      project_id: str,
                      retrieval_type: str = "default",
                      target_chunks: Optional[int] = None,
                      min_chunks: int = 3,
                      max_chunks: int = 10) -> List[RetrievalResult]:
        """
        Filter retrieval results using adaptive gating.
        
        Args:
            results: Raw retrieval results with similarity scores
            project_id: Project identifier
            retrieval_type: Type of retrieval (e.g., "code", "docs", "context")
            target_chunks: Target number of chunks to retrieve
            min_chunks: Minimum chunks to include
            max_chunks: Maximum chunks to include
            
        Returns:
            Filtered and annotated results
        """
        if not results:
            return []
        
        # Get or create project profile
        profile = self._get_or_create_profile(project_id)
        
        # Get statistics for this retrieval type
        stats = profile.statistics.setdefault(
            retrieval_type, 
            GatingStatistics()
        )
        
        # Extract similarity scores
        scores = [r.get("similarity", 0.0) for r in results]
        stats.update_statistics(scores)
        
        # Determine adaptive threshold
        threshold = self._calculate_adaptive_threshold(
            stats, 
            scores,
            target_chunks or profile.target_chunks_per_retrieval
        )
        
        # Apply gating with multiple strategies
        filtered_results = []
        
        # Sort by similarity (descending)
        sorted_results = sorted(
            results, 
            key=lambda x: x.get("similarity", 0.0), 
            reverse=True
        )
        
        # Strategy 1: Threshold-based filtering
        threshold_filtered = []
        for result in sorted_results:
            score = result.get("similarity", 0.0)
            
            if score >= threshold:
                threshold_filtered.append(result)
            elif len(threshold_filtered) < min_chunks:
                # Ensure minimum chunks
                threshold_filtered.append(result)
        
        # Strategy 2: Outlier detection
        outlier_mask = self._detect_outliers(scores, stats)
        
        # Strategy 3: Elbow method for natural cutoff
        elbow_index = self._find_elbow_point(scores)
        
        # Combine strategies
        for i, result in enumerate(sorted_results):
            score = result.get("similarity", 0.0)
            
            # Determine inclusion
            included = False
            reason = "below_threshold"
            
            # Check if above threshold
            if score >= threshold:
                included = True
                reason = "above_threshold"
            
            # Check if within minimum chunks
            elif i < min_chunks:
                included = True
                reason = "minimum_chunks"
            
            # Check if not an outlier
            elif i < len(outlier_mask) and not outlier_mask[i]:
                included = True
                reason = "not_outlier"
            
            # Check if before elbow point
            elif elbow_index and i < elbow_index:
                included = True
                reason = "before_elbow"
            
            # Apply maximum chunks limit
            if len([r for r in filtered_results if r.included]) >= max_chunks:
                included = False
                reason = "max_chunks_reached"
            
            # Create result
            filtered_results.append(RetrievalResult(
                chunk_id=result.get("id", ""),
                content=result.get("content", ""),
                similarity_score=score,
                metadata=result.get("metadata", {}),
                included=included,
                reason=reason
            ))
        
        # Update statistics
        stats.total_retrievals += 1
        stats.total_included += sum(1 for r in filtered_results if r.included)
        stats.total_excluded += sum(1 for r in filtered_results if not r.included)
        
        inclusion_rate = stats.total_included / max(stats.total_retrievals, 1)
        stats.inclusion_rates.append(inclusion_rate)
        
        # Save profile
        self._save_profile(profile)
        
        logger.debug(
            f"Filtered {len(results)} to {stats.total_included} chunks "
            f"(threshold: {threshold:.3f}, type: {retrieval_type})"
        )
        
        return filtered_results
    
    def _calculate_adaptive_threshold(self,
                                    stats: GatingStatistics,
                                    current_scores: List[float],
                                    target_chunks: float) -> float:
        """
        Calculate adaptive threshold based on statistics and target.
        
        Args:
            stats: Current gating statistics
            current_scores: Current batch of similarity scores
            target_chunks: Target number of chunks
            
        Returns:
            Adaptive threshold
        """
        if len(stats.similarity_scores) < 20:
            # Not enough data, use base threshold
            return stats.base_threshold
        
        # Method 1: Percentile-based (for target chunks)
        if current_scores and target_chunks > 0:
            # Calculate what percentile would give us target chunks
            target_percentile = 1.0 - (target_chunks / len(current_scores))
            target_percentile = max(0.1, min(0.9, target_percentile))
            percentile_threshold = np.percentile(current_scores, target_percentile * 100)
        else:
            percentile_threshold = stats.current_threshold
        
        # Method 2: Statistical threshold (mean - k*std)
        if self.outlier_method == "zscore":
            k = 0.5  # Number of standard deviations
            statistical_threshold = stats.rolling_mean - k * stats.rolling_std
        elif self.outlier_method == "mad":
            k = 1.5
            statistical_threshold = stats.rolling_median - k * stats.mad
        else:  # IQR
            scores_array = np.array(stats.similarity_scores)
            q1, q3 = np.percentile(scores_array, [25, 75])
            iqr = q3 - q1
            statistical_threshold = q1 - 0.5 * iqr
        
        # Method 3: Quality-adjusted threshold
        quality_adjustment = 0.0
        if stats.precision < 0.8:
            # Too many false positives, increase threshold
            quality_adjustment = 0.05
        elif stats.recall < 0.8:
            # Too many false negatives, decrease threshold
            quality_adjustment = -0.05
        
        quality_threshold = stats.current_threshold + quality_adjustment
        
        # Combine methods with weights
        weights = [0.4, 0.4, 0.2]  # percentile, statistical, quality
        thresholds = [percentile_threshold, statistical_threshold, quality_threshold]
        
        combined_threshold = sum(w * t for w, t in zip(weights, thresholds))
        
        # Apply adaptation rate
        new_threshold = (
            stats.current_threshold * (1 - self.adaptation_rate) +
            combined_threshold * self.adaptation_rate
        )
        
        # Clamp to bounds
        new_threshold = max(stats.min_threshold, min(stats.max_threshold, new_threshold))
        
        # Update current threshold
        stats.current_threshold = new_threshold
        
        return new_threshold
    
    def _detect_outliers(self, 
                        scores: List[float], 
                        stats: GatingStatistics) -> List[bool]:
        """
        Detect outliers in similarity scores.
        
        Args:
            scores: List of similarity scores
            stats: Gating statistics
            
        Returns:
            Boolean mask where True indicates outlier
        """
        if len(scores) < 3:
            return [False] * len(scores)
        
        scores_array = np.array(scores)
        
        if self.outlier_method == "mad":
            # Median Absolute Deviation method
            median = np.median(scores_array)
            mad = np.median(np.abs(scores_array - median))
            threshold = median - 3 * mad
            outliers = scores_array < threshold
            
        elif self.outlier_method == "iqr":
            # Interquartile Range method
            q1, q3 = np.percentile(scores_array, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            outliers = scores_array < lower_bound
            
        else:  # zscore
            # Z-score method
            mean = np.mean(scores_array)
            std = np.std(scores_array)
            z_scores = np.abs((scores_array - mean) / (std + 1e-6))
            outliers = z_scores > 2.5
        
        return outliers.tolist()
    
    def _find_elbow_point(self, scores: List[float]) -> Optional[int]:
        """
        Find the elbow point in similarity scores.
        
        Args:
            scores: Sorted list of similarity scores (descending)
            
        Returns:
            Index of elbow point or None
        """
        if len(scores) < 3:
            return None
        
        # Calculate differences between consecutive scores
        diffs = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
        
        if not diffs:
            return None
        
        # Find the point with maximum difference
        max_diff_idx = np.argmax(diffs)
        
        # Only consider it an elbow if the difference is significant
        if diffs[max_diff_idx] > np.mean(diffs) + np.std(diffs):
            return max_diff_idx + 1
        
        return None
    
    def record_feedback(self,
                       project_id: str,
                       retrieval_type: str,
                       feedback: Dict[str, Any]):
        """
        Record quality feedback for a retrieval.
        
        Args:
            project_id: Project identifier
            retrieval_type: Type of retrieval
            feedback: Feedback data including:
                - chunk_ids: List of chunk IDs
                - useful: List of booleans indicating usefulness
                - missing_context: Description of missing context
                - unnecessary_chunks: List of unnecessary chunk IDs
        """
        profile = self._get_or_create_profile(project_id)
        stats = profile.statistics.get(retrieval_type, GatingStatistics())
        
        # Record feedback
        feedback_record = {
            "timestamp": datetime.now().isoformat(),
            "retrieval_type": retrieval_type,
            **feedback
        }
        profile.feedback_history.append(feedback_record)
        
        # Update quality metrics
        if "useful" in feedback and "chunk_ids" in feedback:
            # Calculate precision: useful chunks / retrieved chunks
            useful_chunks = sum(feedback["useful"])
            total_chunks = len(feedback["chunk_ids"])
            
            if total_chunks > 0:
                precision = useful_chunks / total_chunks
                stats.quality_scores.append(precision)
                
                # Update rolling precision
                if len(stats.quality_scores) >= 10:
                    stats.precision = np.mean(stats.quality_scores)
        
        # Adjust thresholds based on feedback
        if feedback.get("missing_context"):
            # Lower threshold to include more context
            stats.base_threshold *= 0.95
            stats.base_threshold = max(stats.min_threshold, stats.base_threshold)
            logger.info(f"Lowered threshold for {project_id}/{retrieval_type} due to missing context")
        
        if feedback.get("unnecessary_chunks"):
            # Raise threshold to exclude more
            unnecessary_ratio = len(feedback["unnecessary_chunks"]) / total_chunks
            if unnecessary_ratio > 0.3:  # More than 30% unnecessary
                stats.base_threshold *= 1.05
                stats.base_threshold = min(stats.max_threshold, stats.base_threshold)
                logger.info(f"Raised threshold for {project_id}/{retrieval_type} due to unnecessary chunks")
        
        # Save updated profile
        profile.updated_at = datetime.now()
        self._save_profile(profile)
    
    def get_statistics(self, 
                      project_id: str, 
                      retrieval_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get gating statistics for a project.
        
        Args:
            project_id: Project identifier
            retrieval_type: Specific retrieval type or None for all
            
        Returns:
            Statistics dictionary
        """
        profile = self.profiles.get(project_id)
        if not profile:
            return {}
        
        if retrieval_type:
            stats = profile.statistics.get(retrieval_type)
            return stats.to_dict() if stats else {}
        
        # Return all statistics
        return {
            "project_id": project_id,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "statistics": {
                rtype: stats.to_dict() 
                for rtype, stats in profile.statistics.items()
            },
            "avg_chunks_per_retrieval": profile.avg_chunks_per_retrieval,
            "context_quality_score": profile.context_quality_score,
            "feedback_count": len(profile.feedback_history)
        }
    
    def _get_or_create_profile(self, project_id: str) -> ProjectGatingProfile:
        """Get or create a project profile."""
        if project_id not in self.profiles:
            # Try to load from disk
            profile_path = self.profiles_dir / f"{project_id}.json"
            if profile_path.exists():
                try:
                    with open(profile_path, 'r') as f:
                        data = json.load(f)
                    profile = self._profile_from_dict(data)
                    self.profiles[project_id] = profile
                except Exception as e:
                    logger.error(f"Failed to load profile for {project_id}: {e}")
                    self.profiles[project_id] = ProjectGatingProfile(project_id=project_id)
            else:
                self.profiles[project_id] = ProjectGatingProfile(project_id=project_id)
        
        return self.profiles[project_id]
    
    def _save_profile(self, profile: ProjectGatingProfile):
        """Save a project profile to disk."""
        profile_path = self.profiles_dir / f"{profile.project_id}.json"
        
        try:
            data = self._profile_to_dict(profile)
            with open(profile_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile for {profile.project_id}: {e}")
    
    def _load_profiles(self):
        """Load all profiles from disk."""
        for profile_path in self.profiles_dir.glob("*.json"):
            try:
                with open(profile_path, 'r') as f:
                    data = json.load(f)
                profile = self._profile_from_dict(data)
                self.profiles[profile.project_id] = profile
            except Exception as e:
                logger.error(f"Failed to load profile from {profile_path}: {e}")
    
    def _profile_to_dict(self, profile: ProjectGatingProfile) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            "project_id": profile.project_id,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "statistics": {
                rtype: stats.to_dict()
                for rtype, stats in profile.statistics.items()
            },
            "feedback_history": profile.feedback_history[-100:],  # Keep last 100
            "inclusion_rules": profile.inclusion_rules,
            "exclusion_rules": profile.exclusion_rules,
            "avg_chunks_per_retrieval": profile.avg_chunks_per_retrieval,
            "target_chunks_per_retrieval": profile.target_chunks_per_retrieval,
            "context_quality_score": profile.context_quality_score
        }
    
    def _profile_from_dict(self, data: Dict[str, Any]) -> ProjectGatingProfile:
        """Create profile from dictionary."""
        profile = ProjectGatingProfile(
            project_id=data["project_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
        
        # Restore statistics
        for rtype, stats_data in data.get("statistics", {}).items():
            stats = GatingStatistics()
            for key, value in stats_data.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            profile.statistics[rtype] = stats
        
        # Restore other fields
        profile.feedback_history = data.get("feedback_history", [])
        profile.inclusion_rules = data.get("inclusion_rules", [])
        profile.exclusion_rules = data.get("exclusion_rules", [])
        profile.avg_chunks_per_retrieval = data.get("avg_chunks_per_retrieval", 5.0)
        profile.target_chunks_per_retrieval = data.get("target_chunks_per_retrieval", 5.0)
        profile.context_quality_score = data.get("context_quality_score", 0.8)
        
        return profile