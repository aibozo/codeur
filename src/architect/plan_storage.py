"""
Plan storage management for phased implementation plans.

This module handles the persistent storage of implementation plans on disk,
providing a structured way to save, load, and manage plans.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .plan_models import (
    ImplementationPlan, ImplementationPhase, PlanMilestone, 
    PlanChunk, PlanStatus
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class PlanStorage:
    """
    Manages persistent storage of implementation plans.
    
    Plans are stored in a structured directory format:
    .agent/plans/
    ├── active/          # Currently active plans
    ├── archived/        # Completed/archived plans
    ├── templates/       # Reusable plan templates
    └── index.json      # Plan metadata index
    """
    
    def __init__(self, base_path: str = ".agent"):
        """
        Initialize plan storage.
        
        Args:
            base_path: Base directory for agent data (default: .agent)
        """
        self.base_path = Path(base_path)
        self.plans_dir = self.base_path / "plans"
        self.active_dir = self.plans_dir / "active"
        self.archived_dir = self.plans_dir / "archived"
        self.templates_dir = self.plans_dir / "templates"
        self.index_path = self.plans_dir / "index.json"
        
        # Create directories
        self._ensure_directories()
        
        # Load or create index
        self.index = self._load_index()
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.archived_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the plan index or create if doesn't exist."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load plan index: {e}")
                return self._create_default_index()
        else:
            return self._create_default_index()
    
    def _create_default_index(self) -> Dict[str, Any]:
        """Create default index structure."""
        index = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "plans": {},
            "templates": {},
            "statistics": {
                "total_plans": 0,
                "active_plans": 0,
                "completed_plans": 0,
                "archived_plans": 0
            }
        }
        self._save_index(index)
        return index
    
    def _save_index(self, index: Dict[str, Any]):
        """Save the plan index."""
        try:
            with open(self.index_path, 'w') as f:
                json.dump(index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plan index: {e}")
    
    def save_plan(self, plan: ImplementationPlan) -> bool:
        """
        Save an implementation plan to disk.
        
        Args:
            plan: The implementation plan to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine directory based on status
            if plan.status in [PlanStatus.COMPLETED, PlanStatus.ARCHIVED]:
                plan_dir = self.archived_dir
            else:
                plan_dir = self.active_dir
            
            # Create plan file
            plan_path = plan_dir / f"{plan.id}.json"
            plan_data = plan.to_dict()
            
            with open(plan_path, 'w') as f:
                json.dump(plan_data, f, indent=2)
            
            # Update index
            self.index["plans"][plan.id] = {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "status": plan.status.value,
                "project_type": plan.project_type,
                "scope": plan.scope,
                "created_at": plan.created_at.isoformat(),
                "updated_at": plan.updated_at.isoformat(),
                "path": str(plan_path.relative_to(self.base_path)),
                "phase_count": len(plan.phases),
                "total_chunks": len(plan.get_all_chunks()),
                "completion_percentage": plan.completion_percentage,
                "task_graph_id": plan.task_graph_id
            }
            
            # Update statistics
            self._update_statistics()
            self._save_index(self.index)
            
            logger.info(f"Saved plan '{plan.name}' (ID: {plan.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save plan: {e}")
            return False
    
    def load_plan(self, plan_id: str) -> Optional[ImplementationPlan]:
        """
        Load an implementation plan from disk.
        
        Args:
            plan_id: ID of the plan to load
            
        Returns:
            The implementation plan or None if not found
        """
        try:
            # Check index for plan location
            if plan_id not in self.index["plans"]:
                logger.warning(f"Plan {plan_id} not found in index")
                return None
            
            plan_info = self.index["plans"][plan_id]
            plan_path = self.base_path / plan_info["path"]
            
            if not plan_path.exists():
                logger.error(f"Plan file not found: {plan_path}")
                return None
            
            # Load plan data
            with open(plan_path, 'r') as f:
                plan_data = json.load(f)
            
            # Create plan object
            plan = ImplementationPlan.from_dict(plan_data)
            
            logger.info(f"Loaded plan '{plan.name}' (ID: {plan.id})")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to load plan {plan_id}: {e}")
            return None
    
    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Dict[str, Any]]:
        """
        List all plans, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of plan summaries
        """
        plans = []
        
        for plan_id, plan_info in self.index["plans"].items():
            if status is None or plan_info["status"] == status.value:
                plans.append(plan_info)
        
        # Sort by updated_at descending
        plans.sort(key=lambda p: p["updated_at"], reverse=True)
        
        return plans
    
    def archive_plan(self, plan_id: str) -> bool:
        """
        Archive a plan by moving it to the archived directory.
        
        Args:
            plan_id: ID of the plan to archive
            
        Returns:
            True if successful, False otherwise
        """
        try:
            plan = self.load_plan(plan_id)
            if not plan:
                return False
            
            # Update status
            plan.status = PlanStatus.ARCHIVED
            plan.updated_at = datetime.now()
            
            # Move file
            old_path = self.active_dir / f"{plan_id}.json"
            new_path = self.archived_dir / f"{plan_id}.json"
            
            if old_path.exists():
                shutil.move(str(old_path), str(new_path))
            
            # Save updated plan
            self.save_plan(plan)
            
            logger.info(f"Archived plan '{plan.name}' (ID: {plan_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive plan {plan_id}: {e}")
            return False
    
    def delete_plan(self, plan_id: str) -> bool:
        """
        Delete a plan from storage.
        
        Args:
            plan_id: ID of the plan to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if plan_id not in self.index["plans"]:
                return False
            
            plan_info = self.index["plans"][plan_id]
            plan_path = self.base_path / plan_info["path"]
            
            # Remove file
            if plan_path.exists():
                plan_path.unlink()
            
            # Remove from index
            del self.index["plans"][plan_id]
            
            # Update statistics
            self._update_statistics()
            self._save_index(self.index)
            
            logger.info(f"Deleted plan {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            return False
    
    def save_template(self, template_name: str, plan: ImplementationPlan) -> bool:
        """
        Save a plan as a reusable template.
        
        Args:
            template_name: Name for the template
            plan: The plan to save as template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear IDs and timestamps from the plan
            template_data = plan.to_dict()
            template_data["id"] = ""
            template_data["created_at"] = ""
            template_data["updated_at"] = ""
            template_data["task_graph_id"] = None
            
            # Clear IDs from phases, milestones, and chunks
            for phase in template_data["phases"]:
                phase["id"] = ""
                for milestone in phase["milestones"]:
                    milestone["id"] = ""
                    for chunk in milestone["chunks"]:
                        chunk["id"] = ""
                        chunk["task_ids"] = []
            
            # Save template
            template_path = self.templates_dir / f"{template_name}.json"
            with open(template_path, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update index
            self.index["templates"][template_name] = {
                "name": template_name,
                "description": plan.description,
                "project_type": plan.project_type,
                "scope": plan.scope,
                "created_at": datetime.now().isoformat(),
                "path": str(template_path.relative_to(self.base_path))
            }
            
            self._save_index(self.index)
            
            logger.info(f"Saved template '{template_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return False
    
    def load_template(self, template_name: str) -> Optional[ImplementationPlan]:
        """
        Load a plan template.
        
        Args:
            template_name: Name of the template to load
            
        Returns:
            The template as an implementation plan or None if not found
        """
        try:
            if template_name not in self.index["templates"]:
                logger.warning(f"Template '{template_name}' not found")
                return None
            
            template_info = self.index["templates"][template_name]
            template_path = self.base_path / template_info["path"]
            
            if not template_path.exists():
                logger.error(f"Template file not found: {template_path}")
                return None
            
            # Load template data
            with open(template_path, 'r') as f:
                template_data = json.load(f)
            
            # Create new plan from template
            plan = ImplementationPlan.from_dict(template_data)
            
            # Generate new IDs
            plan.id = str(uuid.uuid4())
            plan.created_at = datetime.now()
            plan.updated_at = datetime.now()
            
            # Generate new IDs for all components
            for phase in plan.phases:
                phase.id = str(uuid.uuid4())
                for milestone in phase.milestones:
                    milestone.id = str(uuid.uuid4())
                    for chunk in milestone.chunks:
                        chunk.id = str(uuid.uuid4())
            
            logger.info(f"Loaded template '{template_name}'")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return None
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        templates = []
        
        for template_name, template_info in self.index["templates"].items():
            templates.append(template_info)
        
        # Sort by name
        templates.sort(key=lambda t: t["name"])
        
        return templates
    
    def _update_statistics(self):
        """Update plan statistics in the index."""
        stats = {
            "total_plans": len(self.index["plans"]),
            "active_plans": 0,
            "completed_plans": 0,
            "archived_plans": 0
        }
        
        for plan_info in self.index["plans"].values():
            status = plan_info["status"]
            if status in ["draft", "active", "in_progress"]:
                stats["active_plans"] += 1
            elif status == "completed":
                stats["completed_plans"] += 1
            elif status == "archived":
                stats["archived_plans"] += 1
        
        self.index["statistics"] = stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get plan storage statistics."""
        return self.index["statistics"]
    
    def search_plans(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for plans by name or description.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching plan summaries
        """
        results = []
        query_lower = query.lower()
        
        for plan_id, plan_info in self.index["plans"].items():
            if (query_lower in plan_info["name"].lower() or 
                query_lower in plan_info["description"].lower()):
                results.append(plan_info)
        
        # Sort by relevance (name matches first, then by date)
        results.sort(key=lambda p: (
            query_lower not in p["name"].lower(),
            p["updated_at"]
        ), reverse=True)
        
        return results


# Import uuid for template loading
import uuid