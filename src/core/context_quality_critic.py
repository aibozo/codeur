"""
Context Quality Critic Agent.

This module provides an agent that critiques context quality to provide
feedback for the adaptive similarity gating system.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import re

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ContextChunk:
    """Represents a chunk of context."""
    chunk_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: Optional[datetime] = None


@dataclass
class ContextCritique:
    """Critique results for a context window."""
    overall_quality: float  # 0-1 score
    relevance_scores: Dict[str, float]  # chunk_id -> relevance score
    blindspots: List[str]  # Identified missing context
    unnecessary_chunks: List[str]  # chunk_ids that aren't needed
    suggestions: List[str]  # Improvement suggestions
    metrics: Dict[str, float] = field(default_factory=dict)
    

class ContextQualityCritic:
    """
    Agent that critiques context quality for continuous improvement.
    
    This critic analyzes:
    - Relevance of included chunks
    - Completeness of context
    - Redundancy and noise
    - Information gaps (blindspots)
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize the context quality critic.
        
        Args:
            llm_client: LLM client for advanced analysis
        """
        self.llm_client = llm_client
        self.critique_history: List[Dict[str, Any]] = []
        
        # Heuristic patterns for common issues
        self.redundancy_patterns = [
            r"import\s+statements",
            r"docstring\s+duplication",
            r"repeated\s+definitions",
            r"similar\s+code\s+blocks"
        ]
        
        self.blindspot_indicators = [
            r"undefined\s+(?:variable|function|class)",
            r"missing\s+(?:import|dependency|context)",
            r"reference\s+to\s+(.+?)\s+not\s+found",
            r"need\s+more\s+context\s+about"
        ]
        
        logger.info("Initialized context quality critic")
    
    async def critique_context(self,
                              query: str,
                              context_chunks: List[ContextChunk],
                              response: Optional[str] = None,
                              task_type: str = "general") -> ContextCritique:
        """
        Critique the quality of a context window.
        
        Args:
            query: The original query/question
            context_chunks: List of context chunks provided
            response: Optional response generated with this context
            task_type: Type of task (code, documentation, planning, etc.)
            
        Returns:
            Detailed critique of context quality
        """
        critique_start = datetime.now()
        
        # Analyze each chunk
        relevance_scores = {}
        unnecessary_chunks = []
        
        for chunk in context_chunks:
            relevance = await self._analyze_chunk_relevance(
                chunk, query, task_type
            )
            chunk_id = chunk.get('chunk_id', str(hash(str(chunk)))) if isinstance(chunk, dict) else getattr(chunk, 'chunk_id', str(hash(chunk)))
            relevance_scores[chunk_id] = relevance
            
            if relevance < 0.3:  # Low relevance threshold
                unnecessary_chunks.append(chunk_id)
        
        # Detect blindspots
        blindspots = await self._detect_blindspots(
            query, context_chunks, response, task_type
        )
        
        # Calculate metrics
        metrics = self._calculate_quality_metrics(
            context_chunks, relevance_scores, blindspots
        )
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            metrics, blindspots, unnecessary_chunks, task_type
        )
        
        # Overall quality score
        overall_quality = self._calculate_overall_quality(
            metrics, len(blindspots), len(unnecessary_chunks)
        )
        
        critique = ContextCritique(
            overall_quality=overall_quality,
            relevance_scores=relevance_scores,
            blindspots=blindspots,
            unnecessary_chunks=unnecessary_chunks,
            suggestions=suggestions,
            metrics=metrics
        )
        
        # Record critique
        self._record_critique(query, critique, task_type)
        
        critique_time = (datetime.now() - critique_start).total_seconds()
        logger.debug(f"Context critique completed in {critique_time:.2f}s")
        
        return critique
    
    async def _analyze_chunk_relevance(self,
                                     chunk: ContextChunk,
                                     query: str,
                                     task_type: str) -> float:
        """
        Analyze relevance of a single chunk.
        
        Args:
            chunk: Context chunk to analyze
            query: Original query
            task_type: Type of task
            
        Returns:
            Relevance score (0-1)
        """
        # Start with similarity score as base
        if isinstance(chunk, dict):
            relevance = chunk.get('similarity_score', 0.5)
            content = chunk.get('content', '')
            chunk_id = chunk.get('chunk_id', '')
        else:
            relevance = getattr(chunk, 'similarity_score', 0.5)
            content = getattr(chunk, 'content', '')
            chunk_id = getattr(chunk, 'chunk_id', '')
        
        # Heuristic adjustments
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Check for direct keyword matches
        query_terms = set(re.findall(r'\w+', query_lower))
        content_terms = set(re.findall(r'\w+', content_lower))
        term_overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
        
        # Adjust relevance based on term overlap
        relevance = 0.7 * relevance + 0.3 * term_overlap
        
        # Task-specific adjustments
        if task_type == "code":
            # Check for code-specific relevance
            if self._is_import_block(chunk.content) and "import" not in query_lower:
                relevance *= 0.5  # Reduce relevance of imports unless specifically asked
            
            if self._is_test_code(chunk.content) and "test" not in query_lower:
                relevance *= 0.6  # Reduce relevance of tests unless needed
                
        elif task_type == "documentation":
            # Boost relevance of documentation chunks
            if any(marker in content_lower for marker in ["description", "usage", "example", "api"]):
                relevance *= 1.2
                
        # Use LLM for more sophisticated analysis if available
        if self.llm_client and relevance > 0.4 and relevance < 0.7:
            # Only use LLM for borderline cases to save cost
            try:
                llm_relevance = await self._llm_analyze_relevance(
                    chunk.content, query, task_type
                )
                # Weighted average with heuristic
                relevance = 0.6 * llm_relevance + 0.4 * relevance
            except Exception as e:
                logger.warning(f"LLM relevance analysis failed: {e}")
        
        return min(1.0, relevance)
    
    async def _detect_blindspots(self,
                               query: str,
                               context_chunks: List[ContextChunk],
                               response: Optional[str] = None,
                               task_type: str = "general") -> List[str]:
        """
        Detect missing context (blindspots).
        
        Args:
            query: Original query
            context_chunks: Provided context chunks
            response: Generated response (if available)
            task_type: Type of task
            
        Returns:
            List of identified blindspots
        """
        blindspots = []
        
        # Combine all context
        full_context = "\n".join(
            chunk.get('content', '') if isinstance(chunk, dict) else getattr(chunk, 'content', '')
            for chunk in context_chunks
        )
        
        # Check for undefined references in response
        if response:
            for pattern in self.blindspot_indicators:
                matches = re.findall(pattern, response, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if match and match not in full_context:
                        blindspots.append(f"Missing context for: {match}")
        
        # Task-specific blindspot detection
        if task_type == "code":
            blindspots.extend(self._detect_code_blindspots(
                query, full_context, context_chunks
            ))
        elif task_type == "planning":
            blindspots.extend(self._detect_planning_blindspots(
                query, full_context
            ))
        
        # Use LLM for comprehensive analysis if available
        if self.llm_client and len(context_chunks) > 2:
            try:
                llm_blindspots = await self._llm_detect_blindspots(
                    query, full_context, task_type
                )
                blindspots.extend(llm_blindspots)
            except Exception as e:
                logger.warning(f"LLM blindspot detection failed: {e}")
        
        # Deduplicate
        return list(set(blindspots))
    
    def _detect_code_blindspots(self,
                               query: str,
                               full_context: str,
                               chunks: List[ContextChunk]) -> List[str]:
        """Detect code-specific blindspots."""
        blindspots = []
        
        # Check for missing imports
        used_modules = re.findall(r'(\w+)\.', full_context)
        imported_modules = re.findall(r'import\s+(\w+)', full_context)
        imported_modules.extend(re.findall(r'from\s+(\w+)', full_context))
        
        missing_imports = set(used_modules) - set(imported_modules)
        for module in missing_imports:
            if module not in ['self', 'cls', 'super']:
                blindspots.append(f"Missing import for module: {module}")
        
        # Check for undefined functions/classes
        called_functions = re.findall(r'(\w+)\s*\(', full_context)
        defined_functions = re.findall(r'def\s+(\w+)', full_context)
        defined_functions.extend(re.findall(r'class\s+(\w+)', full_context))
        
        undefined = set(called_functions) - set(defined_functions)
        for func in undefined:
            if func not in ['print', 'len', 'str', 'int', 'float', 'list', 'dict']:
                blindspots.append(f"Missing definition for: {func}")
        
        return blindspots
    
    def _detect_planning_blindspots(self, query: str, full_context: str) -> List[str]:
        """Detect planning-specific blindspots."""
        blindspots = []
        
        # Check for missing requirements context
        if "requirement" in query.lower() and "requirement" not in full_context.lower():
            blindspots.append("Missing requirements context")
        
        # Check for missing architecture context
        if any(term in query.lower() for term in ["architecture", "design", "structure"]):
            if not any(term in full_context.lower() for term in ["component", "module", "layer"]):
                blindspots.append("Missing architectural context")
        
        return blindspots
    
    def _calculate_quality_metrics(self,
                                 chunks: List[ContextChunk],
                                 relevance_scores: Dict[str, float],
                                 blindspots: List[str]) -> Dict[str, float]:
        """Calculate quality metrics for the context."""
        if not chunks:
            return {
                "avg_relevance": 0.0,
                "coverage": 0.0,
                "redundancy": 0.0,
                "noise_ratio": 0.0,
                "completeness": 0.0
            }
        
        # Average relevance
        avg_relevance = sum(relevance_scores.values()) / len(relevance_scores)
        
        # Coverage (based on similarity score distribution)
        similarity_scores = []
        for c in chunks:
            if isinstance(c, dict):
                similarity_scores.append(c.get('similarity_score', 0.5))
            else:
                similarity_scores.append(getattr(c, 'similarity_score', 0.5))
        
        coverage = 1.0 - (max(similarity_scores) - min(similarity_scores)) if similarity_scores else 0.0
        
        # Redundancy (check for duplicate content)
        contents = []
        for c in chunks:
            if isinstance(c, dict):
                contents.append(c.get('content', ''))
            else:
                contents.append(getattr(c, 'content', ''))
        unique_contents = set(contents)
        redundancy = 1.0 - (len(unique_contents) / len(contents))
        
        # Noise ratio (low relevance chunks)
        noise_count = sum(1 for score in relevance_scores.values() if score < 0.3)
        noise_ratio = noise_count / len(chunks)
        
        # Completeness (inverse of blindspot count)
        completeness = 1.0 / (1.0 + len(blindspots))
        
        return {
            "avg_relevance": avg_relevance,
            "coverage": coverage,
            "redundancy": redundancy,
            "noise_ratio": noise_ratio,
            "completeness": completeness
        }
    
    def _generate_suggestions(self,
                            metrics: Dict[str, float],
                            blindspots: List[str],
                            unnecessary_chunks: List[str],
                            task_type: str) -> List[str]:
        """Generate improvement suggestions based on analysis."""
        suggestions = []
        
        # Based on metrics
        if metrics.get("avg_relevance", 0) < 0.5:
            suggestions.append("Consider adjusting similarity threshold - average relevance is low")
        
        if metrics.get("redundancy", 0) > 0.3:
            suggestions.append("High redundancy detected - consider deduplication strategies")
        
        if metrics.get("noise_ratio", 0) > 0.2:
            suggestions.append(f"Remove {len(unnecessary_chunks)} low-relevance chunks to reduce noise")
        
        if metrics.get("completeness", 0) < 0.7:
            suggestions.append("Expand search to include missing context areas")
        
        # Based on blindspots
        if blindspots:
            suggestions.append(f"Address {len(blindspots)} identified context gaps")
            if len(blindspots) > 5:
                suggestions.append("Consider broader initial retrieval for comprehensive context")
        
        # Task-specific suggestions
        if task_type == "code":
            if any("import" in b for b in blindspots):
                suggestions.append("Include file headers and imports in retrieval")
        elif task_type == "documentation":
            suggestions.append("Prioritize documentation and example chunks")
        
        return suggestions
    
    def _calculate_overall_quality(self,
                                 metrics: Dict[str, float],
                                 blindspot_count: int,
                                 unnecessary_count: int) -> float:
        """Calculate overall context quality score."""
        # Weighted average of metrics
        weights = {
            "avg_relevance": 0.3,
            "coverage": 0.1,
            "redundancy": -0.1,  # Negative weight
            "noise_ratio": -0.2,  # Negative weight
            "completeness": 0.3
        }
        
        score = 0.0
        for metric, weight in weights.items():
            value = metrics.get(metric, 0.0)
            if weight < 0:
                # For negative weights, invert the metric
                value = 1.0 - value
                weight = abs(weight)
            score += weight * value
        
        # Penalties
        blindspot_penalty = min(0.2, blindspot_count * 0.02)
        unnecessary_penalty = min(0.1, unnecessary_count * 0.02)
        
        score = score - blindspot_penalty - unnecessary_penalty
        
        return max(0.0, min(1.0, score))
    
    async def _llm_analyze_relevance(self,
                                   content: str,
                                   query: str,
                                   task_type: str) -> float:
        """Use LLM to analyze chunk relevance."""
        if not self.llm_client:
            return 0.5
        
        prompt = f"""Analyze the relevance of this context chunk to the query.
Task type: {task_type}
Query: {query}

Context chunk:
{content[:500]}...

Rate relevance from 0.0 (completely irrelevant) to 1.0 (highly relevant).
Consider:
- Direct answers to the query
- Necessary background information
- Related concepts that aid understanding

Respond with just the numeric score."""
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            return float(score_text)
        except:
            return 0.5
    
    async def _llm_detect_blindspots(self,
                                   query: str,
                                   context: str,
                                   task_type: str) -> List[str]:
        """Use LLM to detect context blindspots."""
        if not self.llm_client:
            return []
        
        prompt = f"""Analyze this context for missing information needed to address the query.
Task type: {task_type}
Query: {query}

Provided context:
{context[:1000]}...

Identify specific missing context that would be helpful. List each gap concisely.
Focus on:
- Undefined references
- Missing prerequisites
- Incomplete information
- Related context that would improve understanding

Respond with a JSON list of missing context descriptions."""
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            # Try to parse as JSON, fall back to line splitting
            try:
                return json.loads(content)
            except:
                return [line.strip() for line in content.split('\n') if line.strip()]
        except:
            return []
    
    def _record_critique(self, query: str, critique: ContextCritique, task_type: str):
        """Record critique for historical analysis."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "task_type": task_type,
            "overall_quality": critique.overall_quality,
            "metrics": critique.metrics,
            "blindspot_count": len(critique.blindspots),
            "unnecessary_count": len(critique.unnecessary_chunks),
            "suggestion_count": len(critique.suggestions)
        }
        
        self.critique_history.append(record)
        
        # Keep only recent history
        if len(self.critique_history) > 1000:
            self.critique_history = self.critique_history[-1000:]
    
    def _is_import_block(self, content: str) -> bool:
        """Check if content is primarily imports."""
        lines = content.strip().split('\n')
        if not lines:
            return False
        
        import_lines = sum(1 for line in lines if line.strip().startswith(('import ', 'from ')))
        return import_lines / len(lines) > 0.7
    
    def _is_test_code(self, content: str) -> bool:
        """Check if content is test code."""
        test_indicators = ['def test_', 'class Test', '@pytest', 'assertEqual', 'mock']
        return any(indicator in content for indicator in test_indicators)
    
    def get_critique_summary(self) -> Dict[str, Any]:
        """Get summary of critique history."""
        if not self.critique_history:
            return {"message": "No critique history available"}
        
        recent = self.critique_history[-100:]  # Last 100 critiques
        
        avg_quality = sum(r["overall_quality"] for r in recent) / len(recent)
        avg_blindspots = sum(r["blindspot_count"] for r in recent) / len(recent)
        avg_unnecessary = sum(r["unnecessary_count"] for r in recent) / len(recent)
        
        task_breakdown = {}
        for record in recent:
            task_type = record["task_type"]
            if task_type not in task_breakdown:
                task_breakdown[task_type] = {"count": 0, "total_quality": 0}
            task_breakdown[task_type]["count"] += 1
            task_breakdown[task_type]["total_quality"] += record["overall_quality"]
        
        for task_type in task_breakdown:
            count = task_breakdown[task_type]["count"]
            total = task_breakdown[task_type]["total_quality"]
            task_breakdown[task_type]["avg_quality"] = total / count
        
        return {
            "total_critiques": len(self.critique_history),
            "recent_critiques": len(recent),
            "avg_quality": avg_quality,
            "avg_blindspots": avg_blindspots,
            "avg_unnecessary_chunks": avg_unnecessary,
            "task_breakdown": task_breakdown,
            "quality_trend": self._calculate_quality_trend()
        }
    
    def _calculate_quality_trend(self) -> str:
        """Calculate quality trend over time."""
        if len(self.critique_history) < 20:
            return "insufficient_data"
        
        # Compare first half vs second half averages
        mid = len(self.critique_history) // 2
        first_half = self.critique_history[:mid]
        second_half = self.critique_history[mid:]
        
        first_avg = sum(r["overall_quality"] for r in first_half) / len(first_half)
        second_avg = sum(r["overall_quality"] for r in second_half) / len(second_half)
        
        diff = second_avg - first_avg
        if abs(diff) < 0.05:
            return "stable"
        elif diff > 0:
            return "improving"
        else:
            return "declining"