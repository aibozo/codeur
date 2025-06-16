"""
WebSocket-based voice agent for Gemini with tool calling support.

This implementation uses the raw WebSocket API for better control over
audio streaming and supports text input and function calling.
"""

import os
import asyncio
import base64
import json
import re
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from datetime import datetime
import uuid

from websockets.asyncio.client import connect
import pyaudio
import numpy as np

from ..core.logging import get_logger
from ..core.agent_graph import search_codebase_with_graph

logger = get_logger(__name__)

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # Input: 16kHz
RECEIVE_SAMPLE_RATE = 24000  # Output: 24kHz
CHUNK_SIZE = 512  # Match the working example

# Suppress ALSA errors
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
try:
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    pass

# Set PulseAudio if needed
if not os.environ.get("PULSE_SERVER"):
    os.environ["PULSE_SERVER"] = "unix:/mnt/wslg/PulseServer"


class WebSocketVoiceAgent:
    """
    Voice agent using WebSocket API with tool calling and architecture context.
    """
    
    def __init__(
        self,
        project_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp"
    ):
        """Initialize WebSocket voice agent."""
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.model = model
        
        # Get API key
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY required")
        
        # WebSocket URI - using v1beta as specified
        self.uri = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={self.api_key}"
        
        # Audio queue for responses
        self.audio_queue = asyncio.Queue()
        
        # WebSocket connection
        self.ws = None
        
        # Tool handlers
        self.tools = self._define_tools()
        
        # Architecture context
        self.architecture_context = None
        self._load_architecture()
        
        # State
        self.is_running = False
        self.text_mode = False  # For text input support
        
        logger.info(f"Initialized WebSocket Voice Agent for {self.project_path}")
    
    def _load_architecture(self):
        """Load architecture files for context."""
        arch_files = [
            self.project_path / "ARCHITECTURE.md",
            self.project_path / "docs/ARCHITECTURE.md",
            self.project_path / "README.md",
            self.project_path / ".claude_docs/architecture.md"
        ]
        
        for arch_file in arch_files:
            if arch_file.exists():
                self.architecture_context = arch_file.read_text()[:2000]  # First 2000 chars
                logger.info(f"Loaded architecture from {arch_file}")
                break
        
        if not self.architecture_context:
            # Generate basic structure
            self.architecture_context = self._generate_basic_architecture()
    
    def _generate_basic_architecture(self) -> str:
        """Generate basic project structure."""
        try:
            dirs = [d.name for d in self.project_path.iterdir() 
                   if d.is_dir() and not d.name.startswith('.')]
            py_files = list(self.project_path.rglob("*.py"))[:10]
            
            return f"""Project Structure:
- Location: {self.project_path}
- Main directories: {', '.join(dirs)}
- Python files: {len(list(self.project_path.rglob('*.py')))}
- Key files: {', '.join(f.name for f in py_files)}
"""
        except Exception as e:
            logger.error(f"Error generating architecture: {e}")
            return f"Project at {self.project_path}"
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define comprehensive tools for codebase exploration and understanding."""
        return [{
            "functionDeclarations": [
                {
                    "name": "search_codebase",
                    "description": "Search the codebase using semantic search with RAG service for files, functions, classes, or concepts",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query - can be code patterns, function names, concepts, or natural language"
                            },
                            "file_pattern": {
                                "type": "string", 
                                "description": "Optional file pattern (e.g., '*.py', '*.tsx')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 5)"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "analyze_component",
                    "description": "Analyze a specific component or module to understand its architecture, dependencies, and purpose",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "component_path": {
                                "type": "string",
                                "description": "Path to component directory or main file"
                            },
                            "depth": {
                                "type": "string",
                                "enum": ["summary", "detailed", "full"],
                                "description": "Level of analysis detail"
                            }
                        },
                        "required": ["component_path"]
                    }
                },
                {
                    "name": "trace_data_flow",
                    "description": "Trace how data flows through the system for a specific feature or API endpoint",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entry_point": {
                                "type": "string",
                                "description": "Starting point - can be API endpoint, function name, or file path"
                            },
                            "flow_type": {
                                "type": "string",
                                "enum": ["request", "event", "data", "all"],
                                "description": "Type of flow to trace"
                            }
                        },
                        "required": ["entry_point"]
                    }
                },
                {
                    "name": "find_dependencies",
                    "description": "Find all dependencies and connections for a specific module, class, or function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "Module, class, or function to analyze"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["imports", "imported_by", "both"],
                                "description": "Direction of dependencies to find"
                            }
                        },
                        "required": ["target"]
                    }
                },
                {
                    "name": "explain_system_flow",
                    "description": "Explain how a specific system feature works end-to-end",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "feature": {
                                "type": "string",
                                "description": "Feature name or description (e.g., 'task creation', 'webhook handling')"
                            }
                        },
                        "required": ["feature"]
                    }
                },
                {
                    "name": "get_agent_info",
                    "description": "Get detailed information about a specific agent in the system",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent (e.g., 'coding_agent', 'architect', 'analyzer')"
                            }
                        },
                        "required": ["agent_name"]
                    }
                },
                {
                    "name": "find_similar_code",
                    "description": "Find code patterns similar to a given example using RAG vector search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code_snippet": {
                                "type": "string",
                                "description": "Code example to find similar patterns for"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context about what you're looking for"
                            }
                        },
                        "required": ["code_snippet"]
                    }
                },
                {
                    "name": "read_file",
                    "description": "Read contents of a specific file with syntax highlighting context",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file relative to project root"
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Optional starting line"
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Optional ending line"
                            }
                        },
                        "required": ["file_path"]
                    }
                },
                {
                    "name": "list_directory",
                    "description": "List contents of a directory with file type analysis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory path relative to project root"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Include subdirectories"
                            }
                        },
                        "required": ["directory"]
                    }
                },
                {
                    "name": "get_project_stats",
                    "description": "Get statistics and metrics about the codebase",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["overview", "languages", "complexity", "agents", "dependencies"],
                                "description": "Type of statistics to retrieve"
                            }
                        },
                        "required": ["category"]
                    }
                }
            ]
        }]
    
    async def _handle_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call from the model."""
        tool_name = tool_call.get("name")
        args = tool_call.get("arguments") or {}
        
        logger.info(f"Tool call: {tool_name} with args: {args}")
        
        try:
            if tool_name == "search_codebase":
                # Check required args
                if not args.get("query"):
                    return {"error": "Missing required argument: query"}
                    
                results = await search_codebase_with_graph(
                    query=args.get("query", ""),
                    project_path=self.project_path,
                    file_pattern=args.get("file_pattern", "**/*.py"),
                    max_results=args.get("max_results", 5)
                )
                return {
                    "results": results,
                    "count": len(results)
                }
            
            elif tool_name == "analyze_component":
                component_path = self.project_path / args["component_path"]
                depth = args.get("depth", "summary")
                
                # Analyze the component structure
                analysis = await self._analyze_component(component_path, depth)
                return analysis
            
            elif tool_name == "trace_data_flow":
                entry_point = args["entry_point"]
                flow_type = args.get("flow_type", "all")
                
                # Trace data flow through the system
                flow = await self._trace_data_flow(entry_point, flow_type)
                return flow
            
            elif tool_name == "find_dependencies":
                target = args["target"]
                direction = args.get("direction", "both")
                
                # Find dependencies for the target
                deps = await self._find_dependencies(target, direction)
                return deps
            
            elif tool_name == "explain_system_flow":
                feature = args["feature"]
                
                # Explain how a feature works
                explanation = await self._explain_system_flow(feature)
                return explanation
            
            elif tool_name == "get_agent_info":
                agent_name = args["agent_name"]
                
                # Get information about a specific agent
                info = await self._get_agent_info(agent_name)
                return info
            
            elif tool_name == "find_similar_code":
                code_snippet = args["code_snippet"]
                context = args.get("context", "")
                
                # Find similar code patterns
                similar = await self._find_similar_code(code_snippet, context)
                return similar
            
            elif tool_name == "read_file":
                file_path = self.project_path / args["file_path"]
                if not file_path.exists():
                    return {"error": f"File not found: {args['file_path']}"}
                
                content = file_path.read_text()
                lines = content.split('\n')
                
                start = args.get("start_line", 1) - 1
                end = args.get("end_line", len(lines))
                
                # Add language detection for syntax context
                lang = self._detect_language(file_path)
                
                return {
                    "content": '\n'.join(lines[start:end]),
                    "total_lines": len(lines),
                    "file_path": str(file_path.relative_to(self.project_path)),
                    "language": lang
                }
            
            elif tool_name == "list_directory":
                dir_path = self.project_path / args["directory"]
                if not dir_path.exists():
                    return {"error": f"Directory not found: {args['directory']}"}
                
                recursive = args.get("recursive", False)
                items = await self._list_directory_with_analysis(dir_path, recursive)
                
                return {
                    "path": str(dir_path.relative_to(self.project_path)),
                    "items": items,
                    "total_files": sum(1 for i in items if i["type"] == "file"),
                    "total_dirs": sum(1 for i in items if i["type"] == "directory")
                }
            
            elif tool_name == "get_project_stats":
                category = args["category"]
                
                # Get project statistics
                stats = await self._get_project_stats(category)
                return stats
            
        except KeyError as e:
            logger.error(f"Missing required argument: {e}")
            return {"error": f"Missing required argument: {e}"}
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return {"error": str(e)}
        
        return {"error": "Unknown tool"}
    
    async def connect(self):
        """Connect to Gemini WebSocket."""
        logger.info("Connecting to Gemini WebSocket...")
        self.ws = await connect(
            self.uri,
            additional_headers={"Content-Type": "application/json"}
        )
        
        # Send setup matching the Live API documentation format
        setup_msg = {
            "setup": {
                "model": f"models/{self.model}",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],  # Just audio for now
                    "temperature": 0.7,
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Aoede"  # Default voice
                            }
                        }
                    }
                },
                "systemInstruction": {
                    "parts": [{
                        "text": f"""You are a helpful voice assistant. Start with a brief greeting and wait for the user to speak.

You have tools available to help answer questions about this codebase, but only use them when specifically asked about the code.

When using tools, don't narrate the process. Just provide the answer naturally.

Project: {self.project_path.name}"""
                    }]
                },
                "tools": self.tools
            }
        }
        
        await self.ws.send(json.dumps(setup_msg))
        # Don't decode the setup response, just like the working example
        setup_response = await self.ws.recv(decode=False)
        logger.info(f"Setup complete, response size: {len(setup_response)} bytes")
    
    async def _capture_audio(self):
        """Capture and stream audio from microphone."""
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        
        logger.info("Audio capture started")
        
        try:
            while self.is_running:
                if not self.text_mode:  # Only capture audio when not in text mode
                    try:
                        data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
                        
                        # Use the working message format
                        await self.ws.send(json.dumps({
                            "realtime_input": {
                                "media_chunks": [{
                                    "data": base64.b64encode(data).decode(),
                                    "mime_type": "audio/pcm"
                                }]
                            }
                        }))
                        
                    except Exception as e:
                        logger.error(f"Audio capture error: {e}")
                        await asyncio.sleep(0.1)
                else:
                    # In text mode, wait briefly
                    await asyncio.sleep(0.01)  # Much shorter sleep to avoid interruptions
                    
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
    
    async def _handle_responses(self):
        """Handle responses from Gemini."""
        logger.info("Response handler started")
        
        async for msg in self.ws:
            try:
                response = json.loads(msg)
                
                # Handle tool calls
                if "toolCall" in response:
                    logger.info("Received tool call request")
                    print("\n🔧 Tool call requested by model")
                    tool_calls = response["toolCall"].get("functionCalls", [])
                    
                    # Don't pause audio - let VAD handle it
                    # self.processing_tool = True
                    
                    function_responses = []
                    for call in tool_calls:
                        print(f"   Executing: {call.get('name')} with args: {call.get('arguments')}")
                        logger.info(f"Executing tool: {call.get('name')} with args: {call.get('arguments')}")
                        result = await self._handle_tool_call(call)
                        function_responses.append({
                            "id": call.get("id"),
                            "name": call.get("name"),
                            "response": {
                                "name": call.get("name"),
                                "content": result
                            }
                        })
                    
                    # Send the result back in correct format
                    print("   Sending tool response back to model...")
                    await self.ws.send(json.dumps({
                        "toolResponse": {
                            "functionResponses": function_responses
                        }
                    }))
                    
                    # Don't need to resume since we didn't pause
                    # self.processing_tool = False
                    continue
                
                # Handle audio responses
                try:
                    audio_data = response["serverContent"]["modelTurn"]["parts"][0]["inlineData"]["data"]
                    await self.audio_queue.put(base64.b64decode(audio_data))
                except KeyError:
                    pass
                
                # Handle text responses
                try:
                    text = response["serverContent"]["modelTurn"]["parts"][0]["text"]
                    # Filter out tool-related narrations
                    if not any(phrase in text.lower() for phrase in [
                        "calling", "executing", "tool", "function", "search_codebase",
                        "read_file", "list_directory", "get_", "using tool"
                    ]):
                        print(f"\n📝 Assistant: {text}")
                except KeyError:
                    pass
                
                # Handle turn completion
                try:
                    if response.get("serverContent", {}).get("turnComplete"):
                        print("\n✅ Model turn complete")
                        # Clear audio queue for interruptions
                        while not self.audio_queue.empty():
                            self.audio_queue.get_nowait()
                except KeyError:
                    pass
                
                # Handle interruption
                try:
                    if response.get("serverContent", {}).get("interrupted"):
                        print("\n⚠️  Model was interrupted!")
                        logger.warning("Model generation interrupted")
                        # Clear audio queue when interrupted
                        while not self.audio_queue.empty():
                            self.audio_queue.get_nowait()
                except KeyError:
                    pass
                    
            except Exception as e:
                logger.error(f"Response handling error: {e}")
    
    async def _play_audio(self):
        """Play audio responses."""
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True
        )
        
        logger.info("Audio playback started")
        
        try:
            while self.is_running:
                data = await self.audio_queue.get()
                await asyncio.to_thread(stream.write, data)
                
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
    
    
    async def run(self):
        """Run the voice agent."""
        try:
            # Connect to WebSocket
            await self.connect()
            
            print("\n🎙️  WebSocket Voice Agent")
            print("=" * 50)
            print(f"📁 Project: {self.project_path}")
            print(f"🧠 Model: {self.model}")
            print(f"📄 Architecture: {len(self.architecture_context)} chars loaded")
            print(f"🔧 Tools: {len(self.tools[0]['functionDeclarations']) if self.tools else 0} available")
            print("\n🎤 Start speaking! (Press Ctrl+C to stop)")
            print("\n📌 Note: The agent has context about your project structure")
            print("   and can answer questions about the codebase.\n")
            
            self.is_running = True
            
            # Run all tasks concurrently
            try:
                # Use asyncio.gather for Python 3.10 compatibility
                await asyncio.gather(
                    self._capture_audio(),
                    self._handle_responses(),
                    self._play_audio()
                )
            except asyncio.CancelledError:
                pass
                
        except KeyboardInterrupt:
            print("\n\n👋 Voice agent stopped")
        except Exception as e:
            logger.error(f"Voice agent error: {e}")
            raise
        finally:
            self.is_running = False
            if self.ws:
                await self.ws.close()
            print("\n✅ Cleanup complete")


    # Helper methods for advanced tools
    
    async def _analyze_component(self, component_path: Path, depth: str) -> Dict[str, Any]:
        """Analyze a component's structure and purpose."""
        if not component_path.exists():
            return {"error": f"Component not found: {component_path}"}
        
        result = {
            "path": str(component_path.relative_to(self.project_path)),
            "type": "directory" if component_path.is_dir() else "file"
        }
        
        if component_path.is_file():
            # Analyze single file
            content = component_path.read_text()
            result.update({
                "language": self._detect_language(component_path),
                "lines": len(content.split('\n')),
                "imports": self._extract_imports(content, component_path),
                "exports": self._extract_exports(content, component_path),
                "classes": self._extract_classes(content),
                "functions": self._extract_functions(content)
            })
        else:
            # Analyze directory
            files = list(component_path.rglob("*"))
            py_files = [f for f in files if f.suffix == ".py"]
            
            result.update({
                "total_files": len([f for f in files if f.is_file()]),
                "python_files": len(py_files),
                "subdirectories": len([f for f in files if f.is_dir()]),
                "main_files": [f.name for f in component_path.glob("*.py") if f.name in ["__init__.py", "main.py", "app.py"]]
            })
            
            if depth in ["detailed", "full"]:
                # Get more details
                result["structure"] = self._get_directory_structure(component_path, max_depth=2 if depth == "detailed" else 5)
        
        return result
    
    async def _trace_data_flow(self, entry_point: str, flow_type: str) -> Dict[str, Any]:
        """Trace data flow through the system."""
        # Search for the entry point
        results = await search_codebase_with_graph(
            query=entry_point,
            project_path=self.project_path,
            max_results=10
        )
        
        if not results:
            return {"error": f"Entry point not found: {entry_point}"}
        
        # Simplified flow tracing
        flow = {
            "entry_point": entry_point,
            "type": flow_type,
            "traces": []
        }
        
        # Add known flow patterns based on sys_summary.txt
        if "webhook" in entry_point.lower():
            flow["traces"] = [
                "Webhook endpoint receives request",
                "Security validation (tokens/signatures)",
                "Platform-specific handler parses payload",
                "Task created and queued",
                "Request Planner processes task",
                "Task Graph updated",
                "Specialized agents assigned",
                "Results published via events"
            ]
        elif "request" in entry_point.lower() or "planner" in entry_point.lower():
            flow["traces"] = [
                "Request Planner receives natural language request",
                "RAG service searches for context",
                "LLM generates structured plan",
                "Task Graph created with dependencies",
                "Tasks assigned to agents",
                "Execution monitored",
                "Results aggregated"
            ]
        
        return flow
    
    async def _find_dependencies(self, target: str, direction: str) -> Dict[str, Any]:
        """Find dependencies for a target module/class/function."""
        # Search for the target
        results = await search_codebase_with_graph(
            query=target,
            project_path=self.project_path,
            max_results=10
        )
        
        dependencies = {
            "target": target,
            "direction": direction,
            "dependencies": []
        }
        
        for result in results:
            file_path = Path(result.get("file_path", ""))
            if file_path.exists():
                content = file_path.read_text()
                
                if direction in ["imports", "both"]:
                    imports = self._extract_imports(content, file_path)
                    dependencies["dependencies"].extend([
                        {"type": "imports", "module": imp} for imp in imports
                    ])
                
                if direction in ["imported_by", "both"]:
                    # Search for files that import this target
                    import_search = await search_codebase_with_graph(
                        query=f"import {target}",
                        project_path=self.project_path,
                        max_results=5
                    )
                    dependencies["dependencies"].extend([
                        {"type": "imported_by", "file": r["file_path"]} 
                        for r in import_search
                    ])
        
        return dependencies
    
    async def _explain_system_flow(self, feature: str) -> Dict[str, Any]:
        """Explain how a system feature works."""
        explanations = {
            "task creation": {
                "overview": "Tasks are created through Request Planner from natural language",
                "steps": [
                    "User submits request via frontend/webhook",
                    "Request Planner parses intent using LLM",
                    "RAG service provides codebase context",
                    "Structured plan created with subtasks",
                    "Task Graph manages dependencies",
                    "Scheduler assigns to specialized agents",
                    "Agents execute and report progress"
                ],
                "key_components": ["request_planner", "task_graph", "scheduler", "agents"]
            },
            "webhook handling": {
                "overview": "External platforms integrate via webhook endpoints",
                "steps": [
                    "Webhook server receives POST request",
                    "Security middleware validates tokens",
                    "Platform handler parses payload",
                    "Task created from webhook data",
                    "Queued for async execution",
                    "Results sent back or via WebSocket"
                ],
                "key_components": ["webhook/server.py", "webhook/handlers.py", "webhook/security.py"]
            },
            "code generation": {
                "overview": "Coding Agent generates code changes from tasks",
                "steps": [
                    "Receives CodingTask with goals",
                    "Creates feature branch",
                    "RAG finds similar code patterns",
                    "LLM generates patches/rewrites",
                    "Validates syntax and tests",
                    "Commits changes with message",
                    "Reports completion"
                ],
                "key_components": ["coding_agent", "rag_service", "validator", "git_integration"]
            }
        }
        
        feature_lower = feature.lower()
        for key, explanation in explanations.items():
            if key in feature_lower or feature_lower in key:
                return explanation
        
        # Default explanation
        return {
            "overview": f"Feature '{feature}' - searching for information",
            "suggestion": "Try more specific terms like 'task creation', 'webhook handling', or 'code generation'"
        }
    
    async def _get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Get information about a specific agent."""
        agents = {
            "coding_agent": {
                "name": "Coding Agent",
                "location": "src/coding_agent/",
                "purpose": "Converts coding tasks into actual code changes and git commits",
                "key_features": [
                    "Smart context gathering with RAG",
                    "Patch generation or full file rewriting",
                    "Multi-stage validation pipeline",
                    "Git integration with branching",
                    "Automated commit messages"
                ],
                "main_files": ["agent.py", "patch_generator.py", "validator.py"]
            },
            "architect": {
                "name": "Architect Agent",
                "location": "src/architect/",
                "purpose": "High-level system design and conversation management",
                "key_features": [
                    "Context-aware conversations",
                    "Hierarchical task organization",
                    "Community detection in tasks",
                    "Long conversation compression",
                    "RAG integration"
                ],
                "main_files": ["architect.py", "context_aware_architect.py", "context_graph.py"]
            },
            "analyzer": {
                "name": "Analyzer Agent",
                "location": "src/analyzer/",
                "purpose": "Automatic architecture analysis and documentation",
                "key_features": [
                    "Component discovery",
                    "Dependency analysis",
                    "Pattern detection",
                    "Mermaid diagram generation",
                    "Change monitoring"
                ],
                "main_files": ["analyzer.py", "models.py"]
            },
            "request_planner": {
                "name": "Request Planner",
                "location": "src/request_planner/",
                "purpose": "Main orchestrator converting natural language to actionable plans",
                "key_features": [
                    "Natural language parsing",
                    "Context retrieval with RAG",
                    "Structured plan generation",
                    "Task graph creation",
                    "Agent assignment"
                ],
                "main_files": ["planner.py", "integrated_planner.py", "llm.py"]
            }
        }
        
        agent_key = agent_name.lower().replace(" ", "_")
        if agent_key in agents:
            return agents[agent_key]
        
        return {
            "error": f"Unknown agent: {agent_name}",
            "available_agents": list(agents.keys())
        }
    
    async def _find_similar_code(self, code_snippet: str, context: str) -> Dict[str, Any]:
        """Find similar code patterns using basic search."""
        # Extract key patterns from the snippet
        patterns = self._extract_patterns(code_snippet)
        
        all_results = []
        for pattern in patterns[:3]:  # Limit to top 3 patterns
            results = await search_codebase_with_graph(
                query=pattern,
                project_path=self.project_path,
                max_results=3
            )
            all_results.extend(results)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for r in all_results:
            key = r.get("file_path", "")
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        return {
            "query": code_snippet[:100] + "..." if len(code_snippet) > 100 else code_snippet,
            "context": context,
            "patterns_searched": patterns,
            "similar_code": unique_results[:5]
        }
    
    async def _list_directory_with_analysis(self, dir_path: Path, recursive: bool) -> List[Dict[str, Any]]:
        """List directory contents with analysis."""
        items = []
        
        if recursive:
            paths = list(dir_path.rglob("*"))[:100]  # Limit for performance
        else:
            paths = list(dir_path.iterdir())
        
        for item in paths:
            item_info = {
                "name": item.name,
                "path": str(item.relative_to(self.project_path)),
                "type": "directory" if item.is_dir() else "file"
            }
            
            if item.is_file():
                item_info.update({
                    "size": item.stat().st_size,
                    "extension": item.suffix,
                    "language": self._detect_language(item) if item.suffix in ['.py', '.js', '.ts', '.tsx'] else None
                })
            
            items.append(item_info)
        
        return items
    
    async def _get_project_stats(self, category: str) -> Dict[str, Any]:
        """Get project statistics."""
        if category == "overview":
            py_files = list(self.project_path.rglob("*.py"))
            js_files = list(self.project_path.rglob("*.js")) + list(self.project_path.rglob("*.ts")) + list(self.project_path.rglob("*.tsx"))
            
            return {
                "category": "overview",
                "total_files": len(list(self.project_path.rglob("*.*"))),
                "python_files": len(py_files),
                "javascript_files": len(js_files),
                "directories": len([d for d in self.project_path.rglob("*") if d.is_dir()]),
                "main_components": ["request_planner", "coding_agent", "architect", "analyzer", "rag_service", "webhook", "frontend"]
            }
        
        elif category == "agents":
            return {
                "category": "agents",
                "agents": [
                    {"name": "Request Planner", "type": "orchestrator", "location": "src/request_planner/"},
                    {"name": "Coding Agent", "type": "executor", "location": "src/coding_agent/"},
                    {"name": "Architect", "type": "planner", "location": "src/architect/"},
                    {"name": "Analyzer", "type": "service", "location": "src/analyzer/"}
                ],
                "total": 4
            }
        
        elif category == "languages":
            return {
                "category": "languages",
                "primary": "Python",
                "frontend": "TypeScript/React",
                "config": ["YAML", "JSON", "TOML"]
            }
        
        return {"category": category, "message": "Statistics not implemented for this category"}
    
    # Utility methods
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript-react',
            '.jsx': 'javascript-react',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c-header',
            '.hpp': 'cpp-header',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.jl': 'julia',
            '.sh': 'shell',
            '.bash': 'bash',
            '.ps1': 'powershell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.less': 'less',
            '.sql': 'sql',
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.tex': 'latex',
            '.vim': 'vim',
            '.lua': 'lua',
            '.pl': 'perl',
            '.ex': 'elixir',
            '.exs': 'elixir',
            '.clj': 'clojure',
            '.cljs': 'clojurescript',
            '.dart': 'dart',
            '.nim': 'nim',
            '.nims': 'nim',
            '.cr': 'crystal',
            '.fs': 'fsharp',
            '.fsx': 'fsharp',
            '.ml': 'ocaml',
            '.mli': 'ocaml',
            '.pas': 'pascal',
            '.pp': 'pascal',
            '.d': 'd',
            '.zig': 'zig',
            '.v': 'vlang',
            '.pony': 'pony'
        }
        return ext_map.get(file_path.suffix.lower(), 'text')
    
    def _extract_imports(self, content: str, file_path: Path) -> List[str]:
        """Extract import statements from code."""
        imports = []
        
        if file_path.suffix == '.py':
            # Python imports
            import_lines = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$', content, re.MULTILINE)
            for from_module, import_names in import_lines:
                if from_module:
                    imports.append(from_module)
                else:
                    # Handle comma-separated imports
                    for name in import_names.split(','):
                        imports.append(name.strip().split(' as ')[0])
        
        elif file_path.suffix in ['.js', '.ts', '.tsx', '.jsx']:
            # JavaScript/TypeScript imports
            import_lines = re.findall(r"(?:import\s+(?:{[^}]+}|\S+)\s+from\s+['\"]([^'\"]+)['\"])|(?:require\(['\"]([^'\"]+)['\"]\))", content)
            imports.extend([imp for group in import_lines for imp in group if imp])
        
        return list(set(imports))
    
    def _extract_exports(self, content: str, file_path: Path) -> List[str]:
        """Extract export statements from code."""
        exports = []
        
        if file_path.suffix == '.py':
            # Look for __all__ definition
            all_match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if all_match:
                exports = re.findall(r'["\'](\w+)["\']', all_match.group(1))
        
        elif file_path.suffix in ['.js', '.ts', '.tsx', '.jsx']:
            # JavaScript/TypeScript exports
            export_lines = re.findall(r'export\s+(?:default\s+)?(?:const|let|var|function|class|interface|type|enum)?\s*(\w+)', content)
            exports.extend(export_lines)
        
        return list(set(exports))
    
    def _extract_classes(self, content: str) -> List[str]:
        """Extract class definitions from code."""
        # Works for Python, JavaScript, TypeScript, Java, etc.
        classes = re.findall(r'class\s+(\w+)', content)
        return list(set(classes))
    
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function definitions from code."""
        functions = []
        
        # Python functions
        functions.extend(re.findall(r'def\s+(\w+)\s*\(', content))
        
        # JavaScript/TypeScript functions
        functions.extend(re.findall(r'function\s+(\w+)\s*\(', content))
        functions.extend(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>', content))
        
        return list(set(functions))
    
    def _extract_patterns(self, code_snippet: str) -> List[str]:
        """Extract key patterns from a code snippet for searching."""
        patterns = []
        
        # Extract function/method calls
        patterns.extend(re.findall(r'(\w+)\s*\(', code_snippet))
        
        # Extract class names
        patterns.extend(re.findall(r'class\s+(\w+)', code_snippet))
        
        # Extract imports
        patterns.extend(re.findall(r'import\s+(\w+)', code_snippet))
        patterns.extend(re.findall(r'from\s+(\w+)', code_snippet))
        
        # Extract variable assignments
        patterns.extend(re.findall(r'(\w+)\s*=', code_snippet))
        
        # Remove common keywords
        keywords = {'def', 'class', 'import', 'from', 'return', 'if', 'else', 'for', 'while', 'try', 'except', 'with', 'as', 'in', 'is', 'not', 'and', 'or'}
        patterns = [p for p in patterns if p not in keywords and len(p) > 2]
        
        return list(set(patterns))[:10]
    
    def _get_directory_structure(self, path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
        """Get directory structure recursively."""
        if current_depth >= max_depth:
            return {"name": path.name, "type": "directory", "children": "..."}
        
        structure = {
            "name": path.name,
            "type": "directory" if path.is_dir() else "file"
        }
        
        if path.is_dir():
            children = []
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue
                child = self._get_directory_structure(item, max_depth, current_depth + 1)
                children.append(child)
            structure["children"] = children[:20]  # Limit children
        
        return structure


def create_simplified_voice_agent(
    project_path: Optional[Path] = None,
    thinking_mode: bool = False,
    voice_name: str = "Zephyr"
) -> WebSocketVoiceAgent:
    """Create a WebSocket-based voice agent (replaces old implementation)."""
    # Note: thinking_mode and voice_name kept for compatibility but not used in WebSocket version
    return WebSocketVoiceAgent(project_path=project_path)


# Alias for compatibility
SimplifiedNativeAudioAgent = WebSocketVoiceAgent