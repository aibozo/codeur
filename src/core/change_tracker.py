"""
Change Tracker Service for monitoring code changes made by agents.

This service tracks diffs approved by coding agents and triggers
architecture re-analysis when change thresholds are met.
"""

import asyncio
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """Simple event for change tracking."""
    type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DiffStats:
    """Statistics for a single diff."""
    file_path: str
    lines_added: int
    lines_removed: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_type: str = ""
    commit_hash: Optional[str] = None
    
    @property
    def total_lines_changed(self) -> int:
        """Total lines changed (added + removed)."""
        return self.lines_added + self.lines_removed


@dataclass
class ChangeMetrics:
    """Accumulated change metrics."""
    total_lines_added: int = 0
    total_lines_removed: int = 0
    files_changed: Set[str] = field(default_factory=set)
    diffs_processed: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_lines_changed(self) -> int:
        """Total lines changed."""
        return self.total_lines_added + self.total_lines_removed
    
    def add_diff(self, diff: DiffStats) -> None:
        """Add a diff to the metrics."""
        self.total_lines_added += diff.lines_added
        self.total_lines_removed += diff.lines_removed
        self.files_changed.add(diff.file_path)
        self.diffs_processed += 1
    
    def reset(self) -> None:
        """Reset metrics."""
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.files_changed.clear()
        self.diffs_processed = 0
        self.last_reset = datetime.utcnow()


@dataclass
class ChangeThresholds:
    """Thresholds for triggering analysis."""
    lines_changed: int = 100
    files_changed: int = 5
    critical_files: List[str] = field(default_factory=lambda: [
        "package.json", "requirements.txt", "pyproject.toml",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
        ".env", "config.json", "settings.py"
    ])
    time_window_hours: int = 24  # Reset if no changes for this long


class ChangeTracker:
    """
    Tracks code changes made by agents and triggers events when thresholds are met.
    """
    
    def __init__(
        self,
        thresholds: Optional[ChangeThresholds] = None
    ):
        """
        Initialize the change tracker.
        
        Args:
            thresholds: Thresholds for triggering analysis
        """
        self.thresholds = thresholds or ChangeThresholds()
        self.metrics = ChangeMetrics()
        self.diff_history: List[DiffStats] = []
        self._callbacks: List[Callable[[ChangeMetrics], None]] = []
        
        logger.info("ChangeTracker initialized")
    
    async def track_diff(
        self,
        diff_content: str,
        file_path: str,
        agent_type: str = "",
        commit_hash: Optional[str] = None
    ) -> DiffStats:
        """
        Track a diff from a coding agent.
        
        Args:
            diff_content: The diff content (unified diff format)
            file_path: Path of the file changed
            agent_type: Type of agent that made the change
            commit_hash: Optional commit hash if change was committed
            
        Returns:
            DiffStats with the parsed statistics
        """
        logger.debug(f"Tracking diff for {file_path}")
        
        # Parse diff to get line counts
        lines_added, lines_removed = self._parse_diff(diff_content)
        
        # Create diff stats
        diff_stats = DiffStats(
            file_path=file_path,
            lines_added=lines_added,
            lines_removed=lines_removed,
            agent_type=agent_type,
            commit_hash=commit_hash
        )
        
        # Add to history
        self.diff_history.append(diff_stats)
        
        # Update metrics
        self.metrics.add_diff(diff_stats)
        
        # Check if it's a critical file
        is_critical = any(
            critical in file_path 
            for critical in self.thresholds.critical_files
        )
        
        # Log the change
        logger.info(
            f"Tracked change: {file_path} "
            f"(+{lines_added}/-{lines_removed}) "
            f"{'[CRITICAL]' if is_critical else ''}"
        )
        
        # Check thresholds
        await self._check_thresholds(is_critical)
        
        return diff_stats
    
    async def track_patch(
        self,
        patch: Dict[str, Any],
        agent_type: str = ""
    ) -> Optional[DiffStats]:
        """
        Track a patch from a coding agent.
        
        Args:
            patch: Patch dictionary with 'path' and 'patch' fields
            agent_type: Type of agent that made the change
            
        Returns:
            DiffStats if patch was tracked, None if skipped
        """
        file_path = patch.get('path', '')
        patch_content = patch.get('patch', '')
        
        if not file_path or not patch_content:
            return None
        
        return await self.track_diff(
            diff_content=patch_content,
            file_path=file_path,
            agent_type=agent_type
        )
    
    def _parse_diff(self, diff_content: str) -> tuple[int, int]:
        """
        Parse a unified diff to count added and removed lines.
        
        Returns:
            Tuple of (lines_added, lines_removed)
        """
        lines_added = 0
        lines_removed = 0
        
        for line in diff_content.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                lines_added += 1
            elif line.startswith('-') and not line.startswith('---'):
                lines_removed += 1
        
        return lines_added, lines_removed
    
    async def _check_thresholds(self, is_critical: bool = False) -> None:
        """Check if any thresholds are met and trigger events."""
        triggered = False
        reasons = []
        
        # Check critical file
        if is_critical:
            triggered = True
            reasons.append("Critical file changed")
        
        # Check line threshold
        if self.metrics.total_lines_changed >= self.thresholds.lines_changed:
            triggered = True
            reasons.append(
                f"Line threshold reached "
                f"({self.metrics.total_lines_changed} >= {self.thresholds.lines_changed})"
            )
        
        # Check file threshold
        if len(self.metrics.files_changed) >= self.thresholds.files_changed:
            triggered = True
            reasons.append(
                f"File threshold reached "
                f"({len(self.metrics.files_changed)} >= {self.thresholds.files_changed})"
            )
        
        if triggered:
            logger.info(f"Change thresholds triggered: {', '.join(reasons)}")
            
            # Log the event (in real system, this would publish to event bridge)
            logger.info(
                f"Change threshold event: {self.metrics.total_lines_changed} lines changed, "
                f"{len(self.metrics.files_changed)} files changed"
            )
            
            # Call callbacks
            for callback in self._callbacks:
                try:
                    callback(self.metrics)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            # Reset metrics after triggering
            self.reset_metrics()
    
    def reset_metrics(self) -> None:
        """Reset the accumulated metrics."""
        logger.info(
            f"Resetting metrics after {self.metrics.diffs_processed} diffs, "
            f"{self.metrics.total_lines_changed} lines changed"
        )
        self.metrics.reset()
    
    def add_threshold_callback(self, callback: Callable[[ChangeMetrics], None]) -> None:
        """
        Add a callback to be called when thresholds are reached.
        
        Args:
            callback: Function to call with current metrics
        """
        self._callbacks.append(callback)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as a dictionary."""
        return {
            "lines_added": self.metrics.total_lines_added,
            "lines_removed": self.metrics.total_lines_removed,
            "total_lines_changed": self.metrics.total_lines_changed,
            "files_changed": list(self.metrics.files_changed),
            "files_changed_count": len(self.metrics.files_changed),
            "diffs_processed": self.metrics.diffs_processed,
            "last_reset": self.metrics.last_reset.isoformat(),
            "time_since_reset": (datetime.utcnow() - self.metrics.last_reset).total_seconds()
        }
    
    def get_recent_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent changes."""
        recent = self.diff_history[-limit:]
        return [
            {
                "file_path": diff.file_path,
                "lines_added": diff.lines_added,
                "lines_removed": diff.lines_removed,
                "total_changed": diff.total_lines_changed,
                "timestamp": diff.timestamp.isoformat(),
                "agent_type": diff.agent_type,
                "commit_hash": diff.commit_hash
            }
            for diff in reversed(recent)
        ]
    
    async def check_time_window(self) -> None:
        """Check if time window has elapsed and reset if needed."""
        time_since_reset = datetime.utcnow() - self.metrics.last_reset
        if time_since_reset.total_seconds() > self.thresholds.time_window_hours * 3600:
            logger.info("Time window elapsed, resetting metrics")
            self.reset_metrics()


# Global instance for easy access
_change_tracker: Optional[ChangeTracker] = None


def get_change_tracker() -> ChangeTracker:
    """Get the global change tracker instance."""
    global _change_tracker
    if _change_tracker is None:
        _change_tracker = ChangeTracker()
    return _change_tracker


def set_change_tracker(tracker: ChangeTracker) -> None:
    """Set the global change tracker instance."""
    global _change_tracker
    _change_tracker = tracker