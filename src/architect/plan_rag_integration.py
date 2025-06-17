"""
RAG integration for phased implementation plans.

This module handles indexing plans in the RAG system for semantic retrieval,
allowing agents to find relevant context based on their queries.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

from .plan_models import ImplementationPlan, ImplementationPhase, PlanMilestone, PlanChunk
from .plan_storage import PlanStorage
from ..core.logging import get_logger

logger = get_logger(__name__)


class PlanRAGIntegration:
    """
    Integrates implementation plans with the RAG system for semantic search.
    
    This allows agents to retrieve relevant plan chunks based on their queries,
    providing rich context during task execution.
    """
    
    def __init__(self, rag_client: Any, plan_storage: PlanStorage):
        """
        Initialize RAG integration.
        
        Args:
            rag_client: RAG client for indexing and retrieval
            plan_storage: Plan storage instance
        """
        self.rag_client = rag_client
        self.plan_storage = plan_storage
        self.chunk_index_path = plan_storage.base_path / "plan_chunks"
        self.chunk_index_path.mkdir(exist_ok=True)
        
        # Track indexed chunks
        self.indexed_chunks = self._load_chunk_index()
    
    def _load_chunk_index(self) -> Dict[str, Any]:
        """Load the chunk index tracking what's been indexed."""
        index_file = self.chunk_index_path / "index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load chunk index: {e}")
                return {}
        return {}
    
    def _save_chunk_index(self):
        """Save the chunk index."""
        index_file = self.chunk_index_path / "index.json"
        try:
            with open(index_file, 'w') as f:
                json.dump(self.indexed_chunks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save chunk index: {e}")
    
    def index_plan(self, plan: ImplementationPlan) -> bool:
        """
        Index an entire implementation plan in RAG.
        
        This breaks down the plan into indexable chunks at multiple levels:
        - Plan level: Overall context and objectives
        - Phase level: Phase-specific context and decisions
        - Milestone level: Milestone deliverables and criteria
        - Chunk level: Detailed implementation context
        
        Args:
            plan: The implementation plan to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            documents = []
            
            # Index plan-level context
            plan_doc = {
                "content": self._create_plan_content(plan),
                "metadata": {
                    "type": "plan",
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "project_type": plan.project_type,
                    "scope": plan.scope,
                    "status": plan.status.value,
                    "level": "plan",
                    "technologies": plan.technology_stack,
                    "patterns": plan.architectural_patterns
                }
            }
            documents.append(plan_doc)
            
            # Index each phase
            for phase_idx, phase in enumerate(plan.phases):
                phase_doc = {
                    "content": self._create_phase_content(phase, plan),
                    "metadata": {
                        "type": "plan_phase",
                        "plan_id": plan.id,
                        "plan_name": plan.name,
                        "phase_id": phase.id,
                        "phase_name": phase.name,
                        "phase_type": phase.phase_type.value,
                        "phase_order": phase.order,
                        "level": "phase",
                        "technologies": phase.technologies
                    }
                }
                documents.append(phase_doc)
                
                # Index each milestone
                for milestone_idx, milestone in enumerate(phase.milestones):
                    milestone_doc = {
                        "content": self._create_milestone_content(milestone, phase, plan),
                        "metadata": {
                            "type": "plan_milestone",
                            "plan_id": plan.id,
                            "plan_name": plan.name,
                            "phase_id": phase.id,
                            "phase_name": phase.name,
                            "milestone_id": milestone.id,
                            "milestone_title": milestone.title,
                            "level": "milestone"
                        }
                    }
                    documents.append(milestone_doc)
                    
                    # Index each chunk
                    for chunk in milestone.chunks:
                        chunk_doc = {
                            "content": self._create_chunk_content(chunk, milestone, phase, plan),
                            "metadata": {
                                "type": "plan_chunk",
                                "plan_id": plan.id,
                                "plan_name": plan.name,
                                "phase_id": phase.id,
                                "phase_name": phase.name,
                                "milestone_id": milestone.id,
                                "milestone_title": milestone.title,
                                "chunk_id": chunk.id,
                                "chunk_title": chunk.title,
                                "chunk_type": chunk.chunk_type,
                                "level": "chunk",
                                "priority": chunk.priority,
                                "technologies": chunk.technologies,
                                "relevant_files": chunk.relevant_files,
                                "tags": list(chunk.tags)
                            }
                        }
                        documents.append(chunk_doc)
                        
                        # Track indexed chunk
                        self.indexed_chunks[chunk.id] = {
                            "plan_id": plan.id,
                            "indexed_at": datetime.now().isoformat(),
                            "content_hash": self._hash_content(chunk_doc["content"])
                        }
            
            # Index documents in RAG
            if hasattr(self.rag_client, 'index_documents'):
                self.rag_client.index_documents(documents)
            else:
                # Fallback for different RAG interface
                for doc in documents:
                    self.rag_client.add_document(
                        content=doc["content"],
                        metadata=doc["metadata"]
                    )
            
            # Save chunk index
            self._save_chunk_index()
            
            logger.info(f"Indexed plan '{plan.name}' with {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index plan: {e}")
            return False
    
    def _create_plan_content(self, plan: ImplementationPlan) -> str:
        """Create indexable content for plan-level context."""
        content_parts = [
            f"Implementation Plan: {plan.name}",
            f"Description: {plan.description}",
            f"Project Type: {plan.project_type}",
            f"Scope: {plan.scope}",
            "",
            "Business Objectives:",
            *[f"- {obj}" for obj in plan.business_objectives],
            "",
            "Technical Requirements:",
            *[f"- {req}" for req in plan.technical_requirements],
            "",
            "Technology Stack:",
            *[f"- {tech}" for tech in plan.technology_stack],
            "",
            "Architectural Patterns:",
            *[f"- {pattern}" for pattern in plan.architectural_patterns],
            "",
            "Constraints:",
            *[f"- {constraint}" for constraint in plan.constraints],
            "",
            "Assumptions:",
            *[f"- {assumption}" for assumption in plan.assumptions]
        ]
        
        return "\n".join(content_parts)
    
    def _create_phase_content(self, phase: ImplementationPhase, plan: ImplementationPlan) -> str:
        """Create indexable content for phase-level context."""
        content_parts = [
            f"Phase: {phase.name}",
            f"Type: {phase.phase_type.value}",
            f"Description: {phase.description}",
            f"Part of Plan: {plan.name}",
            "",
            "Phase Objectives:",
            *[f"- {obj}" for obj in phase.objectives],
            "",
            "Key Decisions:",
            *[f"- {decision}" for decision in phase.key_decisions],
            "",
            "Technologies:",
            *[f"- {tech}" for tech in phase.technologies],
            "",
            "Architectural Decisions:",
            *[f"- {decision}" for decision in phase.architectural_decisions],
            "",
            "Risk Factors:",
            *[f"- {risk}" for risk in phase.risk_factors]
        ]
        
        return "\n".join(content_parts)
    
    def _create_milestone_content(self, milestone: PlanMilestone, phase: ImplementationPhase, plan: ImplementationPlan) -> str:
        """Create indexable content for milestone-level context."""
        content_parts = [
            f"Milestone: {milestone.title}",
            f"Description: {milestone.description}",
            f"Phase: {phase.name}",
            f"Plan: {plan.name}",
            "",
            "Deliverables:",
            *[f"- {deliverable}" for deliverable in milestone.deliverables],
            "",
            "Success Criteria:",
            *[f"- {criteria}" for criteria in milestone.success_criteria]
        ]
        
        return "\n".join(content_parts)
    
    def _create_chunk_content(self, chunk: PlanChunk, milestone: PlanMilestone, phase: ImplementationPhase, plan: ImplementationPlan) -> str:
        """Create indexable content for chunk-level context."""
        content_parts = [
            f"Context Chunk: {chunk.title}",
            f"Type: {chunk.chunk_type}",
            f"Milestone: {milestone.title}",
            f"Phase: {phase.name}",
            f"Plan: {plan.name}",
            "",
            "Content:",
            chunk.content,
            ""
        ]
        
        if chunk.technologies:
            content_parts.extend([
                "Technologies:",
                *[f"- {tech}" for tech in chunk.technologies],
                ""
            ])
        
        if chunk.dependencies:
            content_parts.extend([
                "Dependencies:",
                *[f"- {dep}" for dep in chunk.dependencies],
                ""
            ])
        
        if chunk.constraints:
            content_parts.extend([
                "Constraints:",
                *[f"- {constraint}" for constraint in chunk.constraints],
                ""
            ])
        
        if chunk.test_requirements:
            content_parts.extend([
                "Test Requirements:",
                *[f"- {req}" for req in chunk.test_requirements],
                ""
            ])
        
        if chunk.acceptance_criteria:
            content_parts.extend([
                "Acceptance Criteria:",
                *[f"- {criteria}" for criteria in chunk.acceptance_criteria],
                ""
            ])
        
        if chunk.relevant_files:
            content_parts.extend([
                "Relevant Files:",
                *[f"- {file}" for file in chunk.relevant_files],
                ""
            ])
        
        if chunk.relevant_patterns:
            content_parts.extend([
                "Relevant Patterns:",
                *[f"- {pattern}" for pattern in chunk.relevant_patterns],
                ""
            ])
        
        return "\n".join(content_parts)
    
    def _hash_content(self, content: str) -> str:
        """Create a hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def retrieve_context_for_task(self, task_description: str, task_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant plan context for a task.
        
        Args:
            task_description: Description of the task
            task_id: Optional task ID to find directly linked chunks
            limit: Maximum number of results
            
        Returns:
            List of relevant context chunks with metadata
        """
        try:
            results = []
            
            # First, check for directly linked chunks if task_id provided
            if task_id:
                for plan_info in self.plan_storage.list_plans():
                    plan = self.plan_storage.load_plan(plan_info["id"])
                    if plan:
                        linked_chunks = plan.get_chunks_for_task(task_id)
                        for chunk in linked_chunks[:limit]:
                            results.append({
                                "chunk": chunk,
                                "plan_name": plan.name,
                                "relevance_score": 1.0,  # Direct link = highest relevance
                                "match_type": "direct_link"
                            })
            
            # Then do semantic search
            remaining_limit = limit - len(results)
            if remaining_limit > 0:
                # Query RAG for relevant context
                if hasattr(self.rag_client, 'query'):
                    rag_results = self.rag_client.query(
                        task_description,
                        top_k=remaining_limit,
                        filter={"type": ["plan_chunk", "plan_milestone", "plan_phase"]}
                    )
                    
                    for doc in rag_results.get("documents", []):
                        metadata = doc.get("metadata", {})
                        results.append({
                            "content": doc.get("content", ""),
                            "metadata": metadata,
                            "relevance_score": doc.get("score", 0.0),
                            "match_type": "semantic"
                        })
            
            # Sort by relevance
            results.sort(key=lambda r: r.get("relevance_score", 0), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve context for task: {e}")
            return []
    
    def retrieve_context_by_technology(self, technologies: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve plan context related to specific technologies.
        
        Args:
            technologies: List of technology names
            limit: Maximum number of results
            
        Returns:
            List of relevant context chunks
        """
        try:
            # Build query combining technology names
            query = " ".join(technologies)
            
            if hasattr(self.rag_client, 'query'):
                results = self.rag_client.query(
                    query,
                    top_k=limit,
                    filter={"technologies": {"$in": technologies}}
                )
                
                return results.get("documents", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to retrieve context by technology: {e}")
            return []
    
    def retrieve_similar_implementations(self, description: str, project_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar implementations from past plans.
        
        Args:
            description: Description of what to implement
            project_type: Optional project type filter
            limit: Maximum number of results
            
        Returns:
            List of similar implementations with context
        """
        try:
            # Build filter
            filter_dict = {"level": "chunk"}
            if project_type:
                filter_dict["project_type"] = project_type
            
            if hasattr(self.rag_client, 'query'):
                results = self.rag_client.query(
                    description,
                    top_k=limit,
                    filter=filter_dict
                )
                
                return results.get("documents", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar implementations: {e}")
            return []
    
    def update_chunk_index(self, plan_id: str) -> bool:
        """
        Update the RAG index for a specific plan.
        
        Args:
            plan_id: ID of the plan to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            plan = self.plan_storage.load_plan(plan_id)
            if not plan:
                logger.warning(f"Plan {plan_id} not found")
                return False
            
            # Re-index the plan
            return self.index_plan(plan)
            
        except Exception as e:
            logger.error(f"Failed to update chunk index: {e}")
            return False
    
    def remove_plan_from_index(self, plan_id: str) -> bool:
        """
        Remove a plan and all its chunks from the RAG index.
        
        Args:
            plan_id: ID of the plan to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove chunks from tracking
            chunks_to_remove = []
            for chunk_id, chunk_info in self.indexed_chunks.items():
                if chunk_info["plan_id"] == plan_id:
                    chunks_to_remove.append(chunk_id)
            
            for chunk_id in chunks_to_remove:
                del self.indexed_chunks[chunk_id]
            
            # Remove from RAG if supported
            if hasattr(self.rag_client, 'delete_by_metadata'):
                self.rag_client.delete_by_metadata({"plan_id": plan_id})
            
            # Save updated index
            self._save_chunk_index()
            
            logger.info(f"Removed plan {plan_id} from RAG index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove plan from index: {e}")
            return False


# Import for type annotation
from typing import Any