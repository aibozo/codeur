"""
Community detection for task grouping using NLP and clustering.

This module provides intelligent grouping of tasks into communities based on:
- Semantic similarity of titles/descriptions
- Common keywords and themes
- Task dependencies and relationships
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# Optional imports for advanced NLP
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .enhanced_task_graph import EnhancedTaskNode, TaskCommunity, EnhancedTaskGraph

logger = logging.getLogger(__name__)


@dataclass
class CommunityTheme:
    """Predefined themes for common task groupings."""
    name: str
    keywords: List[str]
    color: str
    description: str
    

# Predefined themes for common development tasks
COMMON_THEMES = [
    CommunityTheme(
        name="Authentication & Security",
        keywords=["auth", "login", "user", "session", "jwt", "token", "security", "password", "oauth", "permission"],
        color="#DC2626",
        description="User authentication and security features"
    ),
    CommunityTheme(
        name="Database & Models",
        keywords=["db", "database", "schema", "migration", "model", "query", "sql", "orm", "table", "index"],
        color="#059669",
        description="Database operations and data modeling"
    ),
    CommunityTheme(
        name="API & Backend",
        keywords=["api", "endpoint", "route", "rest", "graphql", "controller", "service", "backend", "server"],
        color="#3B82F6",
        description="API endpoints and backend services"
    ),
    CommunityTheme(
        name="Frontend & UI",
        keywords=["ui", "component", "react", "vue", "style", "layout", "frontend", "view", "page", "form"],
        color="#8B5CF6",
        description="User interface and frontend components"
    ),
    CommunityTheme(
        name="Testing & QA",
        keywords=["test", "spec", "unit", "integration", "coverage", "mock", "qa", "quality", "assert"],
        color="#F59E0B",
        description="Testing and quality assurance"
    ),
    CommunityTheme(
        name="Infrastructure & DevOps",
        keywords=["deploy", "ci", "cd", "docker", "kubernetes", "build", "infrastructure", "devops", "pipeline"],
        color="#6B7280",
        description="Deployment and infrastructure"
    ),
    CommunityTheme(
        name="Documentation",
        keywords=["docs", "documentation", "readme", "comment", "guide", "tutorial", "example"],
        color="#10B981",
        description="Documentation and guides"
    ),
    CommunityTheme(
        name="Performance & Optimization",
        keywords=["performance", "optimize", "cache", "speed", "efficiency", "profiling", "benchmark"],
        color="#EF4444",
        description="Performance optimization"
    ),
]


class CommunityDetector:
    """
    Detects and creates communities from tasks using various NLP techniques.
    """
    
    def __init__(self, 
                 use_spacy: bool = True,
                 use_embeddings: bool = True,
                 min_community_size: int = 2):
        """
        Initialize the community detector.
        
        Args:
            use_spacy: Whether to use spaCy for advanced NLP
            use_embeddings: Whether to use sentence embeddings
            min_community_size: Minimum tasks to form a community
        """
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        self.use_embeddings = use_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE
        self.min_community_size = min_community_size
        
        # Initialize NLP models
        if self.use_spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except:
                logger.warning("spaCy model not found, falling back to TF-IDF")
                self.use_spacy = False
                
        if self.use_embeddings:
            try:
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                logger.warning("Sentence transformer not available, using TF-IDF")
                self.use_embeddings = False
                
        # TF-IDF as fallback
        self.tfidf = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
    def detect_communities(self, 
                          graph: EnhancedTaskGraph,
                          method: str = "hybrid") -> List[TaskCommunity]:
        """
        Detect communities in the task graph.
        
        Args:
            graph: The task graph to analyze
            method: Detection method - "theme", "embedding", "dependency", "hybrid"
            
        Returns:
            List of detected communities
        """
        if method == "theme":
            return self._detect_theme_communities(graph)
        elif method == "embedding":
            return self._detect_embedding_communities(graph)
        elif method == "dependency":
            return self._detect_dependency_communities(graph)
        elif method == "hybrid":
            return self._detect_hybrid_communities(graph)
        else:
            raise ValueError(f"Unknown method: {method}")
            
    def _detect_theme_communities(self, graph: EnhancedTaskGraph) -> List[TaskCommunity]:
        """Detect communities based on predefined themes."""
        communities = []
        theme_tasks = defaultdict(set)
        
        # Get unassigned tasks
        unassigned_tasks = [
            (tid, task) for tid, task in graph.tasks.items()
            if not task.community_id
        ]
        
        # Match tasks to themes
        for task_id, task in unassigned_tasks:
            text = f"{task.title} {task.description}".lower()
            
            # Score each theme
            theme_scores = {}
            for theme in COMMON_THEMES:
                score = sum(1 for keyword in theme.keywords if keyword in text)
                if score > 0:
                    theme_scores[theme.name] = score
                    
            # Assign to highest scoring theme
            if theme_scores:
                best_theme = max(theme_scores, key=theme_scores.get)
                theme_tasks[best_theme].add(task_id)
                
        # Create communities for themes with enough tasks
        for theme_name, task_ids in theme_tasks.items():
            if len(task_ids) >= self.min_community_size:
                theme = next(t for t in COMMON_THEMES if t.name == theme_name)
                community = graph.create_community(
                    name=theme.name,
                    theme=theme.name.lower().replace(" & ", "_").replace(" ", "_"),
                    task_ids=task_ids
                )
                community.color = theme.color
                community.description = theme.description
                communities.append(community)
                
        return communities
        
    def _detect_embedding_communities(self, graph: EnhancedTaskGraph) -> List[TaskCommunity]:
        """Detect communities using sentence embeddings and clustering."""
        unassigned_tasks = [
            (tid, task) for tid, task in graph.tasks.items()
            if not task.community_id
        ]
        
        if len(unassigned_tasks) < self.min_community_size:
            return []
            
        # Generate embeddings
        task_texts = [f"{task.title} {task.description}" for _, task in unassigned_tasks]
        
        if self.use_embeddings:
            embeddings = self.sentence_model.encode(task_texts)
        else:
            # Use TF-IDF as fallback
            embeddings = self.tfidf.fit_transform(task_texts).toarray()
            
        # Cluster using DBSCAN
        clustering = DBSCAN(
            eps=0.3,
            min_samples=self.min_community_size,
            metric='cosine'
        ).fit(embeddings)
        
        # Create communities from clusters
        communities = []
        cluster_labels = clustering.labels_
        unique_labels = set(cluster_labels) - {-1}  # Exclude noise
        
        for label in unique_labels:
            cluster_indices = np.where(cluster_labels == label)[0]
            task_ids = {unassigned_tasks[i][0] for i in cluster_indices}
            
            # Generate community name from common words
            cluster_texts = [task_texts[i] for i in cluster_indices]
            community_name = self._generate_community_name(cluster_texts)
            
            community = graph.create_community(
                name=community_name,
                theme=community_name.lower().replace(" ", "_"),
                task_ids=task_ids
            )
            communities.append(community)
            
        return communities
        
    def _detect_dependency_communities(self, graph: EnhancedTaskGraph) -> List[TaskCommunity]:
        """Detect communities based on task dependencies."""
        # Build adjacency matrix
        task_ids = list(graph.tasks.keys())
        n = len(task_ids)
        adj_matrix = np.zeros((n, n))
        
        id_to_idx = {tid: i for i, tid in enumerate(task_ids)}
        
        # Fill adjacency matrix
        for i, task_id in enumerate(task_ids):
            task = graph.tasks[task_id]
            
            # Dependencies
            for dep_id in task.dependencies:
                if dep_id in id_to_idx:
                    j = id_to_idx[dep_id]
                    adj_matrix[i, j] = 1
                    adj_matrix[j, i] = 1  # Make undirected
                    
            # Parent-child relationships
            if task.parent_id and task.parent_id in id_to_idx:
                j = id_to_idx[task.parent_id]
                adj_matrix[i, j] = 1
                adj_matrix[j, i] = 1
                
        # Use hierarchical clustering on connectivity
        if n >= self.min_community_size:
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=0.5,
                linkage='average'
            ).fit(adj_matrix)
            
            # Create communities from clusters
            communities = []
            unique_labels = set(clustering.labels_)
            
            for label in unique_labels:
                cluster_indices = np.where(clustering.labels_ == label)[0]
                task_ids_cluster = {task_ids[i] for i in cluster_indices}
                
                if len(task_ids_cluster) >= self.min_community_size:
                    # Check if tasks are unassigned
                    unassigned = {tid for tid in task_ids_cluster 
                                 if not graph.tasks[tid].community_id}
                    
                    if len(unassigned) >= self.min_community_size:
                        community = graph.create_community(
                            name=f"Connected Tasks {len(communities) + 1}",
                            theme="connected",
                            task_ids=unassigned
                        )
                        communities.append(community)
                        
        return communities
        
    def _detect_hybrid_communities(self, graph: EnhancedTaskGraph) -> List[TaskCommunity]:
        """Use multiple methods and merge results."""
        all_communities = []
        
        # Start with theme-based communities
        theme_communities = self._detect_theme_communities(graph)
        all_communities.extend(theme_communities)
        
        # Then try embedding-based on remaining tasks
        embedding_communities = self._detect_embedding_communities(graph)
        all_communities.extend(embedding_communities)
        
        # Finally, look for dependency clusters in remaining tasks
        dependency_communities = self._detect_dependency_communities(graph)
        all_communities.extend(dependency_communities)
        
        return all_communities
        
    def _generate_community_name(self, texts: List[str]) -> str:
        """Generate a name for a community based on common terms."""
        if self.use_spacy:
            # Extract noun phrases
            noun_phrases = []
            for text in texts[:5]:  # Sample first 5
                doc = self.nlp(text)
                noun_phrases.extend([chunk.text for chunk in doc.noun_chunks])
                
            if noun_phrases:
                # Find most common noun phrase
                from collections import Counter
                most_common = Counter(noun_phrases).most_common(1)
                if most_common:
                    return f"{most_common[0][0].title()} Tasks"
                    
        # Fallback: find common words
        all_words = ' '.join(texts).lower().split()
        word_counts = defaultdict(int)
        
        # Count non-stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        for word in all_words:
            if len(word) > 3 and word not in stopwords:
                word_counts[word] += 1
                
        if word_counts:
            most_common_word = max(word_counts, key=word_counts.get)
            return f"{most_common_word.title()} Related Tasks"
            
        return "Task Group"
        
    def suggest_community_merges(self, 
                                graph: EnhancedTaskGraph,
                                threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """
        Suggest communities that could be merged based on similarity.
        
        Returns:
            List of (community1_id, community2_id, similarity_score)
        """
        suggestions = []
        communities = list(graph.communities.values())
        
        if len(communities) < 2:
            return suggestions
            
        # Generate community embeddings
        community_texts = []
        for community in communities:
            # Aggregate task texts
            tasks = [graph.tasks[tid] for tid in community.task_ids if tid in graph.tasks]
            text = ' '.join([f"{t.title} {t.description}" for t in tasks])
            community_texts.append(text)
            
        # Calculate similarities
        if self.use_embeddings:
            embeddings = self.sentence_model.encode(community_texts)
            similarities = cosine_similarity(embeddings)
        else:
            tfidf_matrix = self.tfidf.fit_transform(community_texts)
            similarities = cosine_similarity(tfidf_matrix)
            
        # Find similar pairs
        for i in range(len(communities)):
            for j in range(i + 1, len(communities)):
                similarity = similarities[i, j]
                if similarity >= threshold:
                    suggestions.append((
                        communities[i].id,
                        communities[j].id,
                        similarity
                    ))
                    
        return sorted(suggestions, key=lambda x: x[2], reverse=True)