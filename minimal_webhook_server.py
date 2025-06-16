#!/usr/bin/env python3
"""
Minimal webhook server for the dashboard frontend.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import project models
sys.path.insert(0, str(Path(__file__).parent))
from src.api.project_models import (
    ProjectInitRequest, ProjectInitResponse, ProjectInfo,
    DirectoryBrowseRequest, DirectoryBrowseResponse, DirectoryEntry
)
from src.core.security import SecurityManager
from src.architect import Architect, TaskGraph, TaskNode, ProjectStructure
from src.analyzer import Analyzer
from src.core.change_tracker import ChangeTracker, get_change_tracker, set_change_tracker
from src.voice_agent.tts_voice_mode import TTSVoiceMode

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Codeur Agent Dashboard API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock agent data
MOCK_AGENTS = [
    {"type": "architect", "status": "active", "model": "claude-3-opus", "current_task": "Designing task graph structure", "last_active": datetime.utcnow().isoformat()},
    {"type": "analyzer", "status": "active", "model": "none", "current_task": "Analyzing architecture", "last_active": datetime.utcnow().isoformat()},
    {"type": "request_planner", "status": "active", "model": "claude-3-sonnet", "current_task": "Planning user request", "last_active": datetime.utcnow().isoformat()},
    {"type": "code_writer", "status": "active", "model": "claude-3-opus", "current_task": "Writing implementation", "last_active": datetime.utcnow().isoformat()},
    {"type": "code_tester", "status": "idle", "model": "claude-3-haiku", "current_task": None, "last_active": (datetime.utcnow() - timedelta(minutes=5)).isoformat()},
    {"type": "code_reviewer", "status": "active", "model": "claude-3-sonnet", "current_task": "Reviewing PR #123", "last_active": datetime.utcnow().isoformat()},
    {"type": "doc_writer", "status": "idle", "model": "claude-3-haiku", "current_task": None, "last_active": (datetime.utcnow() - timedelta(minutes=10)).isoformat()},
]

# API Models
class ModelUpdateRequest(BaseModel):
    model: str

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ArchitectChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    conversation_history: List[ChatMessage] = []
    voice_mode: Optional[bool] = False

class ArchitectAnalysisRequest(BaseModel):
    requirements: str
    constraints: Optional[List[str]] = None

class DiffTrackRequest(BaseModel):
    diff_content: str
    file_path: str
    agent_type: Optional[str] = "coding_agent"
    commit_hash: Optional[str] = None

class PatchTrackRequest(BaseModel):
    patches: List[Dict[str, Any]]
    agent_type: Optional[str] = "coding_agent"

# Store active project info
active_project = None
security_manager = None
architect = None
analyzer = None
change_tracker = None
active_task_graphs = {}
tts_voice_mode = None

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Audio endpoint for TTS files
@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Serve TTS audio files."""
    import tempfile
    from fastapi.responses import FileResponse
    
    # Validate filename to prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Check if file exists in temp directory
    audio_path = Path(tempfile.gettempdir()) / filename
    if not audio_path.exists() or not audio_path.suffix == ".wav":
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        headers={"Cache-Control": "max-age=3600"}
    )

# Agent endpoints
@app.get("/api/agents")
async def get_agents():
    return {"agents": MOCK_AGENTS}

@app.post("/api/agents/{agent_type}/model")
async def update_agent_model(agent_type: str, request: ModelUpdateRequest):
    logger.info(f"Updating model for agent {agent_type} to {request.model}")
    return {"status": "success", "agent_type": agent_type, "model": request.model}

# Jobs endpoints
@app.get("/api/jobs")
async def get_jobs(limit: int = 50, offset: int = 0):
    jobs = []
    for i in range(10):
        job_id = f"job_{i + offset}"
        created_at = datetime.utcnow() - timedelta(minutes=random.randint(1, 60))
        completed_at = created_at + timedelta(seconds=random.randint(10, 300))
        
        jobs.append({
            "job_id": job_id,
            "title": random.choice([
                f"Design task graph for feature #{i + offset}",
                f"Process user request #{i + offset}",
                f"Create project structure #{i + offset}",
                f"Plan implementation #{i + offset}"
            ]),
            "status": random.choice(["completed", "failed", "processing", "pending"]),
            "agent_type": random.choice(["architect", "request_planner", "code_writer", "code_tester"]),
            "created_at": created_at.isoformat(),
            "completed_at": completed_at.isoformat() if random.random() > 0.3 else None,
            "duration": random.randint(10, 300) if random.random() > 0.3 else None,
            "error_message": "Task failed due to timeout" if random.random() < 0.1 else None,
            "diff": "+ Added new functionality\n- Removed old code" if random.random() > 0.5 else None,
            "plan": "1. Analyze request\n2. Generate code\n3. Test implementation" if random.random() > 0.5 else None
        })
    
    return {"jobs": jobs, "total": 100, "limit": limit, "offset": offset}

# Graph endpoints
@app.get("/api/graph")
async def get_graph_data():
    return {
        "nodes": [
            {"id": "architect", "label": "AR", "x": 200, "y": 50, "color": "#9333EA", "type": "orchestrator", "status": "active"},
            {"id": "request_planner", "label": "RP", "x": 200, "y": 150, "color": "#FF0066", "type": "orchestrator", "status": "active"},
            {"id": "code_writer", "label": "CW", "x": 100, "y": 300, "color": "#00D9FF", "type": "worker", "status": "active"},
            {"id": "code_tester", "label": "CT", "x": 300, "y": 300, "color": "#00FF88", "type": "worker", "status": "idle"},
            {"id": "code_reviewer", "label": "CR", "x": 100, "y": 450, "color": "#FFD700", "type": "validator", "status": "active"},
            {"id": "doc_writer", "label": "DW", "x": 300, "y": 450, "color": "#FF00FF", "type": "worker", "status": "idle"}
        ],
        "edges": [
            {"source": "architect", "target": "request_planner", "active": True, "flow": 0.9},
            {"source": "request_planner", "target": "code_writer", "active": True, "flow": 0.8},
            {"source": "request_planner", "target": "code_tester", "active": False, "flow": 0},
            {"source": "code_writer", "target": "code_reviewer", "active": True, "flow": 0.6},
            {"source": "code_tester", "target": "code_reviewer", "active": False, "flow": 0},
            {"source": "code_reviewer", "target": "doc_writer", "active": False, "flow": 0}
        ],
        "stats": {
            "total_nodes": 6,
            "active_nodes": 4,
            "total_edges": 6,
            "active_flows": 3,
            "total_messages": random.randint(100, 1000),
            "avg_flow": 0.4
        }
    }

# Metrics endpoints
@app.get("/api/metrics/system")
async def get_system_metrics():
    return {
        "cpu": {"usage_percent": random.uniform(20, 80), "cores": 8},
        "memory": {"used_gb": random.uniform(2, 8), "total_gb": 16, "percent": random.uniform(20, 60)},
        "disk": {"used_gb": random.uniform(50, 200), "total_gb": 500},
        "network": {"bytes_sent": random.randint(1000000, 10000000), "bytes_recv": random.randint(1000000, 10000000)},
        "process": {"memory_mb": random.uniform(100, 500), "threads": random.randint(10, 50)}
    }

@app.get("/api/metrics/queue")
async def get_queue_metrics():
    return {
        "queue_length": random.randint(0, 20),
        "processing": random.randint(0, 5),
        "success_rate": random.uniform(85, 99),
        "avg_wait_time": random.uniform(0.5, 5),
        "avg_processing_time": random.uniform(10, 60)
    }

@app.get("/api/metrics/history/{metric_name}")
async def get_metric_history(metric_name: str, window: str = "5m", hours: int = 1):
    data_points = []
    now = datetime.utcnow()
    points = 60 if window == "1m" else 12 if window == "5m" else 4
    
    for i in range(points):
        timestamp = now - timedelta(minutes=i * (60 / points))
        value = random.uniform(20, 80) if "cpu" in metric_name else random.uniform(1, 8)
        data_points.append({"timestamp": timestamp.isoformat(), "value": value})
    
    data_points.reverse()
    return {"metric": metric_name, "window": window, "data": data_points}

# Project endpoints
@app.post("/api/project/initialize")
async def initialize_project(request: ProjectInitRequest):
    global active_project, security_manager, architect, analyzer, change_tracker
    
    logger.info(f"[INIT] Starting project initialization for: {request.project_path}")
    
    try:
        # Create security manager for the project
        project_path = Path(request.project_path)
        logger.info(f"[INIT] Creating security manager for: {project_path}")
        
        try:
            security_manager = SecurityManager(project_path)
            logger.info("[INIT] ✓ Security manager created")
        except Exception as e:
            logger.error(f"[INIT] ✗ Security manager failed: {e}")
            return ProjectInitResponse(
                success=False,
                message=f"Security initialization failed: {str(e)}"
            )
        
        # Check if it's a valid project directory
        logger.info("[INIT] Checking if valid project root...")
        try:
            is_valid = security_manager.is_valid_project_root()
            logger.info(f"[INIT] Valid project root: {is_valid}")
            if not is_valid:
                return ProjectInitResponse(
                    success=False,
                    message="Selected directory does not appear to be a valid project"
                )
        except Exception as e:
            logger.error(f"[INIT] ✗ Project validation failed: {e}")
            # Continue anyway
        
        # Store project info
        logger.info("[INIT] Creating project info...")
        active_project = ProjectInfo(
            project_path=str(project_path),
            project_name=project_path.name,
            status="initializing",
            indexed_files=0,
            total_chunks=0
        )
        logger.info(f"[INIT] ✓ Project info created: {active_project.project_name}")
        
        # Initialize change tracker
        logger.info("[INIT] Initializing change tracker...")
        try:
            change_tracker = ChangeTracker()
            set_change_tracker(change_tracker)
            logger.info("[INIT] ✓ Change tracker initialized")
        except Exception as e:
            logger.error(f"[INIT] ✗ Change tracker failed: {e}")
            # Continue without it
        
        # Initialize architect for the project
        logger.info("[INIT] Initializing architect...")
        try:
            architect = Architect(str(project_path))
            logger.info("[INIT] ✓ Architect initialized")
        except Exception as e:
            logger.error(f"[INIT] ✗ Architect failed: {e}")
            architect = None
            # Continue without it
        
        # Initialize analyzer for automatic architecture analysis
        logger.info("[INIT] Initializing analyzer...")
        try:
            # Set auto_analyze=False to prevent blocking
            analyzer = Analyzer(str(project_path), auto_analyze=False)
            logger.info("[INIT] ✓ Analyzer initialized")
            # Start analysis in background
            asyncio.create_task(_analyze_with_logging())
        except Exception as e:
            logger.error(f"[INIT] ✗ Analyzer failed: {e}")
            analyzer = None
            # Continue without it
        
        # Start indexing simulation
        logger.info("[INIT] Starting indexing simulation...")
        asyncio.create_task(_simulate_indexing())
        
        logger.info("[INIT] ✓ All initialization tasks started")
        return ProjectInitResponse(
            success=True,
            message="Project initialization started",
            project=active_project
        )
        
    except Exception as e:
        logger.error(f"[INIT] ✗ Project initialization error: {e}")
        import traceback
        logger.error(f"[INIT] Traceback:\n{traceback.format_exc()}")
        return ProjectInitResponse(
            success=False,
            message=str(e)
        )

@app.get("/api/project/status")
async def get_project_status():
    if not active_project:
        logger.debug("[STATUS] No active project")
        return {"status": "uninitialized", "message": "No project initialized"}
    
    logger.debug(f"[STATUS] Project: {active_project.project_name}, Status: {active_project.status}")
    return {
        "status": active_project.status,
        "project": active_project
    }

@app.post("/api/project/browse")
async def browse_directory(request: DirectoryBrowseRequest):
    try:
        # Default to home directory or current directory
        browse_path = Path(request.path) if request.path else Path.home()
        
        if not browse_path.exists():
            browse_path = Path.cwd()
        
        entries = []
        for item in browse_path.iterdir():
            # Skip hidden files unless requested
            if not request.show_hidden and item.name.startswith('.'):
                continue
                
            try:
                stat = item.stat()
                entries.append(DirectoryEntry(
                    name=item.name,
                    path=str(item),
                    is_directory=item.is_dir(),
                    size=stat.st_size if item.is_file() else None,
                    modified=datetime.fromtimestamp(stat.st_mtime)
                ))
            except:
                # Skip items we can't access
                continue
        
        # Sort directories first, then files
        entries.sort(key=lambda x: (not x.is_directory, x.name.lower()))
        
        return DirectoryBrowseResponse(
            current_path=str(browse_path),
            parent_path=str(browse_path.parent) if browse_path.parent != browse_path else None,
            entries=entries,
            can_write=os.access(browse_path, os.W_OK)
        )
        
    except Exception as e:
        logger.error(f"Directory browse error: {e}")
        return DirectoryBrowseResponse(
            current_path=str(Path.cwd()),
            entries=[],
            can_write=False
        )

async def _analyze_with_logging():
    """Run analyzer with logging."""
    global analyzer
    if analyzer:
        try:
            logger.info("[ANALYZER] Starting background architecture analysis...")
            await analyzer.analyze()
            logger.info("[ANALYZER] ✓ Architecture analysis completed")
        except Exception as e:
            logger.error(f"[ANALYZER] ✗ Architecture analysis failed: {e}")

async def _simulate_indexing():
    """Simulate RAG indexing process."""
    global active_project
    
    if not active_project:
        logger.error("[INDEX] No active project to index")
        return
    
    try:
        logger.info("[INDEX] Starting indexing simulation...")
        
        # Simulate indexing stages
        logger.info("[INDEX] Stage 1: Initializing...")
        await asyncio.sleep(1)
        active_project.status = "indexing"
        logger.info("[INDEX] Status changed to: indexing")
        
        # Simulate file counting
        logger.info("[INDEX] Stage 2: Counting files...")
        await asyncio.sleep(2)
        active_project.indexed_files = random.randint(50, 200)
        active_project.total_chunks = random.randint(500, 2000)
        logger.info(f"[INDEX] Files: {active_project.indexed_files}, Chunks: {active_project.total_chunks}")
        
        # Complete
        logger.info("[INDEX] Stage 3: Finalizing...")
        await asyncio.sleep(1)
        active_project.status = "ready"
        active_project.last_indexed = datetime.utcnow()
        
        logger.info(f"[INDEX] ✓ Indexing completed: {active_project.indexed_files} files, {active_project.total_chunks} chunks")
        
    except Exception as e:
        logger.error(f"[INDEX] ✗ Indexing simulation failed: {e}")
        if active_project:
            active_project.status = "error"
            active_project.error_message = str(e)

# Architect endpoints
@app.post("/api/architect/chat")
async def architect_chat(request: ArchitectChatRequest):
    """Chat with the architect agent about project design."""
    global architect, active_project, active_task_graphs
    
    try:
        # Initialize architect if needed
        if not architect and active_project:
            architect = Architect(active_project.project_path)
        
        response_content = ""
        
        # Debug logging
        logger.info(f"[ARCHITECT CHAT] Architect exists: {architect is not None}")
        if architect:
            logger.info(f"[ARCHITECT CHAT] Has llm_client attr: {hasattr(architect, 'llm_client')}")
            logger.info(f"[ARCHITECT CHAT] llm_client value: {architect.llm_client}")
        
        # If LLM is available, use it for more intelligent responses
        if architect and hasattr(architect, 'llm_client') and architect.llm_client:
            # Use LLM for chat
            try:
                # Build conversation history with voice-friendly prompt if needed
                system_prompt = """You are an expert software architect AI assistant. You help users:
                        - Design system architectures
                        - Create task dependency graphs
                        - Plan project phases and milestones
                        - Define component interfaces and data flows
                        - Make technology recommendations
                        
                        """
                
                if request.voice_mode:
                    system_prompt += "Please be concise and conversational. Your responses will be spoken aloud, so avoid overly technical jargon and keep sentences short and clear."
                else:
                    system_prompt += "Be concise but thorough. When discussing tasks or architecture, be specific and actionable."
                
                messages = [
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ]
                
                # Add conversation history
                for msg in request.conversation_history[-10:]:  # Last 10 messages
                    messages.append({"role": msg.role, "content": msg.content})
                
                # Add current message
                messages.append({"role": "user", "content": request.message})
                
                # Analyze existing architecture if asked about current system
                if any(word in request.message.lower() for word in ['current', 'existing', 'analyze', 'what is', 'show me']):
                    arch_analysis = await architect.analyze_existing_architecture()
                    if 'error' not in arch_analysis:
                        context = f"\n\nCurrent architecture analysis:\n"
                        context += f"- Components: {arch_analysis.get('components', [])}\n"
                        context += f"- Patterns: {arch_analysis.get('patterns', [])}\n"
                        context += f"- Technologies: {arch_analysis.get('technologies', [])}\n"
                        messages[-1]['content'] += context
                
                # Find similar implementations if asked about features
                if any(word in request.message.lower() for word in ['implement', 'add', 'create', 'build', 'feature']):
                    similar = await architect.find_similar_implementations(request.message)
                    if similar:
                        context = f"\n\nSimilar implementations found:\n"
                        for impl in similar[:3]:
                            context += f"- {impl['file']}: {impl['symbols']}\n"
                        messages[-1]['content'] += context
                
                logger.info(f"[ARCHITECT CHAT] Using LLM model: {architect.llm_client.model_card.model_id}")
                
                # Convert messages to prompt format for LLMClient
                system_msg = next((m['content'] for m in messages if m['role'] == 'system'), None)
                user_msgs = [m['content'] for m in messages if m['role'] == 'user']
                prompt = user_msgs[-1] if user_msgs else request.message
                
                response_content = architect.llm_client.generate(
                    prompt=prompt,
                    system_prompt=system_msg,
                    temperature=0.7
                    # max_tokens will use model card defaults
                )
                
                logger.info(f"[ARCHITECT CHAT] LLM response received: {len(response_content)} chars")
                
                # Check if we should create a task graph or architecture
                if any(keyword in request.message.lower() for keyword in ['task', 'plan', 'breakdown', 'dependencies']):
                    # Create task graph
                    project_id = request.project_id or active_project.project_path
                    task_graph = await architect.create_task_graph(
                        project_id=project_id,
                        requirements=request.message
                    )
                    active_task_graphs[project_id] = task_graph
                    response_content += f"\n\nI've created a task graph with {len(task_graph.tasks)} tasks. The critical path contains {len(task_graph.get_critical_path())} tasks."
                
                elif any(keyword in request.message.lower() for keyword in ['architecture', 'design', 'components', 'system']):
                    # Create architecture
                    architecture = await architect.design_architecture(request.message)
                    response_content += f"\n\nI've designed an architecture with {len(architecture.components)} components and {len(architecture.interfaces)} interfaces."
                
            except Exception as e:
                logger.error(f"LLM chat failed: {e}")
                # Fall back to rule-based response
                response_content = _get_fallback_response(request.message, architect)
        
        else:
            # Use rule-based responses when LLM not available
            response_content = _get_fallback_response(request.message, architect)
        
        # Only apply keyword-based responses if we don't have a response yet
        if not response_content:
            if "task" in request.message.lower() or "plan" in request.message.lower():
                response_content = f"I'll create a comprehensive task breakdown for your project. Based on your requirements, I recommend a phased approach with clear dependencies between tasks. Let me design the task graph structure..."
                
                # Create a sample task graph
                if active_project:
                    project_id = request.project_id or active_project.project_path
                    task_graph = await architect.create_task_graph(
                        project_id=project_id,
                        requirements=request.message
                    )
                    active_task_graphs[project_id] = task_graph
                    response_content += f"\n\nI've created a task graph with {len(task_graph.tasks)} tasks across multiple phases. The critical path has {len(task_graph.get_critical_path())} tasks."
            
            elif "architecture" in request.message.lower() or "design" in request.message.lower():
                response_content = "I'll design a scalable architecture for your project. Let me analyze the requirements and create a component-based design with clear interfaces and data flows..."
                
                if architect:
                    architecture = await architect.design_architecture(request.message)
                    response_content += f"\n\nI've designed an architecture with {len(architecture.components)} main components and {len(architecture.interfaces)} interfaces."
        
        # Note: This else block is now handled by the main logic above
        
        # Generate TTS audio if voice mode is enabled
        audio_url = None
        if request.voice_mode and response_content:
            global tts_voice_mode
            try:
                # Initialize TTS if needed
                if not tts_voice_mode:
                    try:
                        tts_voice_mode = TTSVoiceMode()
                    except ValueError as ve:
                        logger.error(f"TTS initialization failed: {ve}")
                        logger.info("Voice mode disabled - GOOGLE_API_KEY not configured")
                        tts_voice_mode = None
                
                if tts_voice_mode:
                    # Generate audio (this will save to a temp file)
                    audio_file = await tts_voice_mode.text_to_speech(response_content, play=False)
                    
                    if audio_file:
                        # In a real deployment, you'd upload to a storage service
                        # For now, we'll serve it as a static file
                        audio_filename = Path(audio_file).name
                        audio_url = f"/api/audio/{audio_filename}"
                        logger.info(f"TTS audio generated: {audio_url}")
                    else:
                        logger.warning("TTS generation returned no audio file")
                        
            except Exception as e:
                logger.error(f"TTS generation error: {e}")
                # Continue without audio
        
        return {
            "response": response_content,
            "task_graph_available": len(active_task_graphs) > 0,
            "architecture_available": architect is not None and len(architect.project_structure.components) > 0,
            "audio_url": audio_url
        }
        
    except Exception as e:
        logger.error(f"Architect chat error: {e}")
        return {
            "response": "I encountered an error while processing your request. Please ensure a project is initialized first.",
            "error": str(e)
        }

@app.post("/api/architect/analyze")
async def architect_analyze(request: ArchitectAnalysisRequest):
    """Analyze project requirements and create initial design."""
    global architect, active_project
    
    try:
        if not architect and active_project:
            architect = Architect(active_project.project_path)
        
        if not architect:
            return {"error": "No project initialized"}
        
        analysis = await architect.analyze_project_requirements(request.requirements)
        
        return {
            "analysis": analysis,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Architect analysis error: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/architect/task-graph/{project_id}")
async def get_task_graph(project_id: str):
    """Get the task graph for a project."""
    if project_id in active_task_graphs:
        return active_task_graphs[project_id].to_dict()
    
    return {"error": "Task graph not found", "project_id": project_id}

@app.get("/api/architect/next-tasks")
async def get_next_tasks(project_id: Optional[str] = None):
    """Get the next tasks ready for execution."""
    global architect, active_project
    
    if not architect:
        return {"tasks": [], "error": "Architect not initialized"}
    
    # Use active project if no project_id specified
    if not project_id and active_project:
        project_id = active_project.project_path
    
    if not project_id:
        return {"tasks": [], "error": "No project specified"}
    
    tasks = await architect.get_next_tasks(project_id)
    
    return {
        "tasks": [task.to_dict() for task in tasks],
        "count": len(tasks)
    }

@app.get("/api/architect/analyze-architecture")
async def analyze_architecture():
    """Analyze the existing project architecture using RAG."""
    global architect
    
    if not architect:
        return {"error": "Architect not initialized"}
    
    try:
        analysis = await architect.analyze_existing_architecture()
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Architecture analysis error: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/architect/find-similar")
async def find_similar_implementations(request: Dict[str, str]):
    """Find similar implementations in the codebase."""
    global architect
    
    if not architect:
        return {"error": "Architect not initialized"}
    
    feature = request.get("feature", "")
    if not feature:
        return {"error": "No feature description provided"}
    
    try:
        similar = await architect.find_similar_implementations(feature)
        return {
            "status": "success",
            "similar_implementations": similar
        }
    except Exception as e:
        logger.error(f"Similar implementation search error: {e}")
        return {"error": str(e), "status": "error"}

# Analyzer endpoints
@app.get("/api/analyzer/report")
async def get_architecture_report():
    """Get the latest architecture analysis report."""
    global analyzer, active_project
    
    if not analyzer:
        return {"error": "Analyzer not initialized"}
    
    try:
        # Check if analysis exists
        report_path = Path(active_project.project_path) / ".architecture" / "architecture-report.json"
        if report_path.exists():
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            return {
                "status": "success",
                "report": report_data
            }
        else:
            # Trigger analysis
            report = await analyzer.analyze()
            return {
                "status": "success",
                "report": report.to_dict()
            }
    except Exception as e:
        logger.error(f"Get architecture report error: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/analyzer/diagram")
async def get_architecture_diagram():
    """Get the architecture diagram in Mermaid format."""
    global analyzer, active_project
    
    logger.info("[DIAGRAM] Request for architecture diagram")
    
    if not active_project:
        logger.error("[DIAGRAM] No active project")
        return {"error": "No project initialized", "status": "error"}
    
    try:
        # Check for existing diagram file first
        diagram_path = Path(active_project.project_path) / ".architecture" / "architecture-diagram.mmd"
        logger.info(f"[DIAGRAM] Checking for diagram at: {diagram_path}")
        
        if diagram_path.exists():
            logger.info("[DIAGRAM] Found existing diagram file")
            diagram = diagram_path.read_text()
            return {
                "status": "success",
                "diagram": diagram,
                "format": "mermaid"
            }
        
        # If analyzer exists, try to get from it
        if analyzer:
            logger.info("[DIAGRAM] Generating diagram from analyzer")
            report = await analyzer.analyze()
            return {
                "status": "success",
                "diagram": report.mermaid_diagram,
                "format": "mermaid"
            }
        
        # No analyzer and no file - try to create one
        logger.info("[DIAGRAM] No analyzer available, trying to initialize one")
        try:
            temp_analyzer = Analyzer(str(active_project.project_path), auto_analyze=False)
            report = await temp_analyzer.analyze()
            return {
                "status": "success",
                "diagram": report.mermaid_diagram,
                "format": "mermaid"
            }
        except Exception as e:
            logger.error(f"[DIAGRAM] Failed to create temporary analyzer: {e}")
            
            # Last resort - return a simple diagram
            logger.info("[DIAGRAM] Returning placeholder diagram")
            return {
                "status": "success",
                "diagram": """graph TB
    A[Project Root] --> B[Source Code]
    A --> C[Configuration]
    A --> D[Documentation]
    B --> E[Components]
    B --> F[Services]
    B --> G[Utils]
    
    style A fill:#9333EA,stroke:#7C3AED,color:#fff
    style B fill:#1F2937,stroke:#374151,color:#F3F4F6
    style C fill:#1F2937,stroke:#374151,color:#F3F4F6
    style D fill:#1F2937,stroke:#374151,color:#F3F4F6
""",
                "format": "mermaid"
            }
            
    except Exception as e:
        logger.error(f"[DIAGRAM] Get architecture diagram error: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/analyzer/refresh")
async def refresh_architecture_analysis():
    """Force a refresh of the architecture analysis."""
    global analyzer
    
    if not analyzer:
        return {"error": "Analyzer not initialized"}
    
    try:
        report = await analyzer.analyze(force=True)
        return {
            "status": "success",
            "message": "Architecture analysis refreshed",
            "summary": report.summary
        }
    except Exception as e:
        logger.error(f"Refresh architecture analysis error: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/analyzer/summary")
async def get_architecture_summary():
    """Get a markdown summary of the architecture."""
    global active_project
    
    if not active_project:
        return {"error": "No project initialized"}
    
    try:
        summary_path = Path(active_project.project_path) / ".architecture" / "ARCHITECTURE.md"
        if summary_path.exists():
            summary = summary_path.read_text()
            return {
                "status": "success",
                "summary": summary,
                "format": "markdown"
            }
        else:
            return {
                "status": "error",
                "error": "Architecture summary not found. Run analysis first."
            }
    except Exception as e:
        logger.error(f"Get architecture summary error: {e}")
        return {"error": str(e), "status": "error"}

# Change Tracker endpoints
@app.post("/api/changes/track-diff")
async def track_diff(request: DiffTrackRequest):
    """Track a diff from a coding agent."""
    global change_tracker
    
    if not change_tracker:
        return {"error": "Change tracker not initialized"}
    
    try:
        stats = await change_tracker.track_diff(
            diff_content=request.diff_content,
            file_path=request.file_path,
            agent_type=request.agent_type,
            commit_hash=request.commit_hash
        )
        
        return {
            "status": "success",
            "stats": {
                "lines_added": stats.lines_added,
                "lines_removed": stats.lines_removed,
                "total_changed": stats.total_lines_changed
            },
            "current_metrics": change_tracker.get_metrics()
        }
    except Exception as e:
        logger.error(f"Track diff error: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/changes/track-patches")
async def track_patches(request: PatchTrackRequest):
    """Track multiple patches from a coding agent."""
    global change_tracker
    
    if not change_tracker:
        return {"error": "Change tracker not initialized"}
    
    try:
        results = []
        for patch in request.patches:
            stats = await change_tracker.track_patch(patch, request.agent_type)
            if stats:
                results.append({
                    "file_path": stats.file_path,
                    "lines_added": stats.lines_added,
                    "lines_removed": stats.lines_removed
                })
        
        return {
            "status": "success",
            "patches_tracked": len(results),
            "results": results,
            "current_metrics": change_tracker.get_metrics()
        }
    except Exception as e:
        logger.error(f"Track patches error: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/changes/metrics")
async def get_change_metrics():
    """Get current change tracking metrics."""
    global change_tracker
    
    if not change_tracker:
        return {"error": "Change tracker not initialized"}
    
    return {
        "status": "success",
        "metrics": change_tracker.get_metrics(),
        "recent_changes": change_tracker.get_recent_changes(limit=10)
    }

@app.post("/api/changes/reset")
async def reset_change_metrics():
    """Reset change tracking metrics."""
    global change_tracker
    
    if not change_tracker:
        return {"error": "Change tracker not initialized"}
    
    change_tracker.reset_metrics()
    
    return {
        "status": "success",
        "message": "Change metrics reset"
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = f"client_{id(websocket)}"
    
    try:
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "subscribe":
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "success",
                        "topics": data.get("topics", []),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")

def _get_fallback_response(message: str, architect) -> str:
    """Get fallback response when LLM is not available."""
    message_lower = message.lower()
    
    if "task" in message_lower or "plan" in message_lower:
        return "I'll create a comprehensive task breakdown for your project. Based on your requirements, I recommend a phased approach with clear dependencies between tasks. Let me design the task graph structure..."
    
    elif "architecture" in message_lower or "design" in message_lower:
        return "I'll design a scalable architecture for your project. Let me analyze the requirements and create a component-based design with clear interfaces and data flows..."
    
    elif "help" in message_lower or "what can you do" in message_lower:
        return """I'm the Architect agent. I can help you with:
- Designing system architecture
- Creating task dependency graphs
- Planning project phases
- Defining component interfaces
- Making technology recommendations

What aspect of your project would you like me to help design?"""
    
    else:
        return "I can help you design your project's architecture and create a detailed task breakdown. What specific aspect would you like to focus on - the system design, task planning, or technology stack?"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088, log_level="info")