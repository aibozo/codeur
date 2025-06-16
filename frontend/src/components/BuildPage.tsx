import React, { useState, useEffect } from 'react';
import { Folder, FolderOpen, Send, Bot, FileCode, CheckCircle, Clock, AlertCircle, GitBranch, Building, Mic, MicOff, Volume2 } from 'lucide-react';
import DirectoryBrowser from './DirectoryBrowser';
import TaskGraph from './TaskGraph';
import ArchitectureDiagram from './ArchitectureDiagram';
import ChangeMetrics from './ChangeMetrics';
import { api } from '../api/client';

interface ProjectInfo {
  project_path: string;
  project_name: string;
  status: 'uninitialized' | 'initializing' | 'indexing' | 'ready' | 'error';
  indexed_files?: number;
  total_chunks?: number;
  last_indexed?: string;
  error_message?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Task {
  id: string;
  title: string;
  description: string;
  agent: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'low' | 'medium' | 'high';
}

const BuildPage: React.FC = () => {
  const [projectPath, setProjectPath] = useState('');
  const [projectStatus, setProjectStatus] = useState<'uninitialized' | 'initializing' | 'indexing' | 'ready' | 'error'>('uninitialized');
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskGraph, setTaskGraph] = useState<any>(null);
  const [showTaskGraph, setShowTaskGraph] = useState(false);
  const [showArchitecture, setShowArchitecture] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showDirectoryBrowser, setShowDirectoryBrowser] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [voiceMode, setVoiceMode] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any>(null);

  // Check project status on mount and periodically
  useEffect(() => {
    checkProjectStatus();
    
    // Poll for status updates while initializing/indexing
    const interval = setInterval(() => {
      if (projectStatus === 'initializing' || projectStatus === 'indexing') {
        checkProjectStatus();
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [projectStatus]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).webkitSpeechRecognition) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-US';
      
      recognitionInstance.onresult = (event: any) => {
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          }
        }
        
        if (finalTranscript) {
          setInputMessage(finalTranscript);
        }
      };
      
      recognitionInstance.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };
      
      recognitionInstance.onend = () => {
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
    }
  }, []);

  const checkProjectStatus = async () => {
    try {
      const response = await api.getProjectStatus();
      
      if (response.project) {
        setProjectInfo(response.project);
        setProjectStatus(response.project.status);
        setProjectPath(response.project.project_path);
        
        // Update status message based on state
        if (response.project.status === 'indexing') {
          setStatusMessage(`Indexing: ${response.project.indexed_files || 0} files processed...`);
        } else if (response.project.status === 'ready') {
          setStatusMessage(`Ready: ${response.project.indexed_files || 0} files, ${response.project.total_chunks || 0} chunks`);
        }
      } else {
        setProjectStatus('uninitialized');
      }
    } catch (error) {
      console.error('Failed to check project status:', error);
    }
  };

  const handleBrowseProject = () => {
    setShowDirectoryBrowser(true);
  };

  const handleDirectorySelect = async (selectedPath: string) => {
    try {
      setProjectStatus('initializing');
      setStatusMessage('Initializing project...');
      
      const response = await api.initializeProject(selectedPath);
      
      if (response.success && response.project) {
        setProjectInfo(response.project);
        setProjectPath(response.project.project_path);
        setProjectStatus(response.project.status);
      } else {
        setProjectStatus('error');
        setStatusMessage(response.message || 'Failed to initialize project');
      }
    } catch (error) {
      console.error('Project initialization error:', error);
      setProjectStatus('error');
      setStatusMessage('Failed to initialize project');
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;
    if (projectStatus !== 'ready') {
      alert('Please initialize a project first');
      return;
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages([...messages, newMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Call architect API with voice mode flag
      const response = await api.chatWithArchitect(
        inputMessage,
        projectPath,
        messages.map(m => ({ role: m.role, content: m.content })),
        voiceMode // Pass voice mode flag
      );

      const architectResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, architectResponse]);

      // If voice mode is enabled and we have TTS audio
      if (voiceMode && response.audio_url) {
        playAudioResponse(response.audio_url);
      }

      // If a task graph was created, fetch it
      if (response.task_graph_available) {
        try {
          const graphResponse = await api.getTaskGraph(projectPath);
          setTaskGraph(graphResponse);
          
          // Also get the next tasks for the list view
          const nextTasksResponse = await api.getNextTasks(projectPath);
          if (nextTasksResponse.tasks && nextTasksResponse.tasks.length > 0) {
            const formattedTasks: Task[] = nextTasksResponse.tasks.map((task, index) => ({
              id: task.id,
              title: task.title,
              description: task.description,
              agent: task.agent_type.charAt(0).toUpperCase() + task.agent_type.slice(1).replace('_', ' '),
              status: task.status === 'ready' ? 'pending' : task.status,
              priority: task.priority,
            }));
            setTasks(formattedTasks);
          }
        } catch (err) {
          console.error('Failed to fetch task graph:', err);
        }
      }
    } catch (error) {
      console.error('Architect chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I encountered an error while processing your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const playAudioResponse = async (audioUrl: string) => {
    try {
      setIsSpeaking(true);
      const audio = new Audio(audioUrl);
      audio.addEventListener('ended', () => {
        setIsSpeaking(false);
      });
      audio.addEventListener('error', () => {
        console.error('Audio playback error');
        setIsSpeaking(false);
      });
      await audio.play();
    } catch (error) {
      console.error('Failed to play audio:', error);
      setIsSpeaking(false);
    }
  };

  const toggleVoiceInput = () => {
    if (!recognition) {
      alert('Speech recognition not supported in this browser. Try Chrome or Edge.');
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      try {
        recognition.start();
        setIsListening(true);
      } catch (error) {
        console.error('Failed to start speech recognition:', error);
      }
    }
  };

  const getTaskStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'completed': return 'text-green-400 bg-green-400/20';
      case 'in_progress': return 'text-blue-400 bg-blue-400/20';
      case 'pending': return 'text-gray-400 bg-gray-400/20';
    }
  };

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-gray-400';
    }
  };

  const getProjectStatusDisplay = () => {
    switch (projectStatus) {
      case 'uninitialized':
        return {
          icon: <AlertCircle className="w-5 h-5 text-gray-400" />,
          text: 'No Project Initialized',
          bgColor: 'bg-slate-700',
          borderColor: 'border-slate-600',
          textColor: 'text-gray-300',
        };
      case 'initializing':
        return {
          icon: <Clock className="w-5 h-5 text-blue-400 animate-pulse" />,
          text: 'Initializing...',
          bgColor: 'bg-slate-700/70',
          borderColor: 'border-blue-600/30',
          textColor: 'text-blue-300',
        };
      case 'indexing':
        return {
          icon: <Clock className="w-5 h-5 text-purple-400 animate-pulse" />,
          text: 'Indexing Project...',
          bgColor: 'bg-slate-700/70',
          borderColor: 'border-purple-600/30',
          textColor: 'text-purple-300',
        };
      case 'ready':
        return {
          icon: <CheckCircle className="w-5 h-5 text-emerald-400" />,
          text: projectPath.split('/').pop() || 'Project Ready',
          bgColor: 'bg-slate-700/50',
          borderColor: 'border-emerald-600/30',
          textColor: 'text-emerald-300',
        };
      case 'error':
        return {
          icon: <AlertCircle className="w-5 h-5 text-red-400" />,
          text: 'Initialization Failed',
          bgColor: 'bg-slate-700/70',
          borderColor: 'border-red-600/30',
          textColor: 'text-red-300',
        };
    }
  };

  const statusDisplay = getProjectStatusDisplay();

  return (
    <>
      <DirectoryBrowser
        isOpen={showDirectoryBrowser}
        onClose={() => setShowDirectoryBrowser(false)}
        onSelect={handleDirectorySelect}
      />
      
      <div className="space-y-6 lg:space-y-8">
      {/* Header with Project Status */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Build with AI Architect</h1>
          <p className="text-gray-400 mt-1">Chat with the architect agent to plan and build your project</p>
        </div>
        
        {/* Project Status Card */}
        <div className={`${statusDisplay.bgColor} ${statusDisplay.borderColor} border rounded-lg p-3 flex items-center gap-3 min-w-[200px]`}>
          {statusDisplay.icon}
          <div className="flex-1">
            <p className={`text-sm font-medium ${statusDisplay.textColor}`}>{statusDisplay.text}</p>
            {(projectStatus === 'ready' || projectStatus === 'indexing') && statusMessage && (
              <p className="text-xs text-gray-500">{statusMessage}</p>
            )}
            {projectStatus === 'error' && statusMessage && (
              <p className="text-xs text-red-400">{statusMessage}</p>
            )}
          </div>
          {projectStatus === 'uninitialized' && (
            <button
              onClick={handleBrowseProject}
              className="bg-slate-600 hover:bg-slate-500 text-white text-sm px-3 py-1.5 rounded font-medium transition-colors"
            >
              Browse
            </button>
          )}
        </div>
      </div>
      
      {/* Add Architecture Diagram Button */}
      {projectStatus === 'ready' && (
        <div className="mb-6">
          <button
            onClick={() => setShowArchitecture(!showArchitecture)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
          >
            <Building className="w-5 h-5" />
            {showArchitecture ? 'Hide' : 'Show'} Architecture Diagram
          </button>
        </div>
      )}
      
      {/* Architecture Diagram */}
      {showArchitecture && (
        <div className="mb-6">
          <ArchitectureDiagram className="h-[600px]" />
        </div>
      )}
      
      {/* Change Metrics - Show when project is ready */}
      {projectStatus === 'ready' && (
        <div className="mb-6">
          <ChangeMetrics compact />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 lg:gap-8">
        {/* Chat Interface */}
        <div className="bg-slate-800 rounded-xl shadow-lg flex flex-col h-[600px]">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <Bot className="w-5 h-5 text-purple-400" />
              Architect Agent Chat
            </h2>
            <div className="flex items-center gap-3">
              {isListening && (
                <div className="flex items-center gap-2 text-red-400">
                  <Mic className="w-4 h-4 animate-pulse" />
                  <span className="text-sm">Listening...</span>
                </div>
              )}
              {isSpeaking && (
                <div className="flex items-center gap-2 text-emerald-400">
                  <Volume2 className="w-4 h-4 animate-pulse" />
                  <span className="text-sm">Speaking...</span>
                </div>
              )}
              <button
                onClick={() => setVoiceMode(!voiceMode)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-150 ${
                  voiceMode 
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white' 
                    : 'bg-slate-700 hover:bg-slate-600 text-gray-300'
                }`}
                title={voiceMode ? 'Disable voice mode' : 'Enable voice mode'}
              >
                {voiceMode ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                <span className="text-sm font-medium">Voice Mode</span>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <Bot className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p>Start a conversation with the architect agent</p>
                <p className="text-sm mt-2">Describe your project goals and requirements...</p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'
                        : 'bg-slate-700 text-gray-300'
                    }`}
                  >
                    <p className="text-sm">{message.content}</p>
                    <p className="text-xs mt-2 opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-700 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <div className="animate-pulse flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-slate-700">
            <div className="flex gap-2">
              {voiceMode && recognition && (
                <button
                  onClick={toggleVoiceInput}
                  className={`p-2 rounded-lg transition-all duration-150 ${
                    isListening 
                      ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse' 
                      : 'bg-slate-700 hover:bg-slate-600 text-gray-300'
                  }`}
                  title={isListening ? 'Stop listening' : 'Start voice input'}
                >
                  <Mic className="w-5 h-5" />
                </button>
              )}
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={isListening ? "Listening..." : "Describe what you want to build..."}
                className="flex-1 bg-slate-700 text-white px-4 py-2 rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-all duration-150"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Task List / Graph Toggle */}
        <div className="bg-slate-800 rounded-xl shadow-lg flex flex-col h-[600px]">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <FileCode className="w-5 h-5 text-purple-400" />
              Generated Tasks
            </h2>
            {taskGraph && (
              <button
                onClick={() => setShowTaskGraph(!showTaskGraph)}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
              >
                <GitBranch className="w-4 h-4" />
                {showTaskGraph ? 'List View' : 'Graph View'}
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {showTaskGraph && taskGraph ? (
              <TaskGraph
                tasks={taskGraph.tasks || {}}
                onTaskClick={(taskId) => {
                  console.log('Task clicked:', taskId);
                  // Could open task details or switch to list view
                }}
              />
            ) : tasks.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <FileCode className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                <p>No tasks generated yet</p>
                <p className="text-sm mt-2">Chat with the architect to create a build plan</p>
              </div>
            ) : (
              <div className="space-y-3">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className="bg-slate-700/50 rounded-lg p-4 hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-white">{task.title}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full ${getTaskStatusColor(task.status)}`}>
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mb-3">{task.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Bot className="w-4 h-4 text-purple-400" />
                        <span className="text-sm text-gray-300">{task.agent}</span>
                      </div>
                      <span className={`text-xs ${getPriorityColor(task.priority)}`}>
                        {task.priority} priority
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          {tasks.length > 0 && (
            <div className="p-4 border-t border-slate-700">
              <button className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white py-2 rounded-lg font-medium transition-all duration-150">
                Execute Build Plan
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
    </>
  );
};

export default BuildPage;