/**
 * API client for communicating with the backend
 */

const API_BASE_URL = 'http://localhost:8088/api';

// Types are defined inline in components to avoid module resolution issues
interface ProjectInfo {
  project_path: string;
  project_name: string;
  status: 'uninitialized' | 'initializing' | 'indexing' | 'ready' | 'error';
  indexed_files?: number;
  total_chunks?: number;
  last_indexed?: string;
  error_message?: string;
}

interface DirectoryBrowseResponse {
  current_path: string;
  parent_path?: string;
  entries: DirectoryEntry[];
  can_write: boolean;
}

interface DirectoryEntry {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
  modified?: string;
}

class ApiClient {
  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Project endpoints
  async initializeProject(projectPath: string): Promise<{
    success: boolean;
    message: string;
    project?: ProjectInfo;
  }> {
    return this.fetch('/project/initialize', {
      method: 'POST',
      body: JSON.stringify({ project_path: projectPath }),
    });
  }

  async getProjectStatus(): Promise<{
    status: string;
    project?: ProjectInfo;
    message?: string;
  }> {
    return this.fetch('/project/status');
  }

  async browseDirectory(path?: string, showHidden = false): Promise<DirectoryBrowseResponse> {
    return this.fetch('/project/browse', {
      method: 'POST',
      body: JSON.stringify({ path, show_hidden: showHidden }),
    });
  }

  // Agent endpoints
  async getAgents(): Promise<{ agents: any[] }> {
    return this.fetch('/agents');
  }

  async setAgentModel(agentType: string, model: string): Promise<any> {
    return this.fetch(`/agents/${agentType}/model`, {
      method: 'POST',
      body: JSON.stringify({ model }),
    });
  }

  // Metrics endpoints
  async getSystemMetrics(): Promise<any> {
    return this.fetch('/metrics/system');
  }

  async getQueueMetrics(): Promise<any> {
    return this.fetch('/metrics/queue');
  }

  async getGraphData(): Promise<any> {
    return this.fetch('/graph');
  }

  // Architect endpoints
  async chatWithArchitect(message: string, projectId?: string, conversationHistory?: Array<{role: string; content: string}>): Promise<{
    response: string;
    task_graph_available: boolean;
    architecture_available: boolean;
    error?: string;
  }> {
    return this.fetch('/architect/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        project_id: projectId,
        conversation_history: conversationHistory || []
      }),
    });
  }

  async analyzeRequirements(requirements: string, constraints?: string[]): Promise<any> {
    return this.fetch('/architect/analyze', {
      method: 'POST',
      body: JSON.stringify({ requirements, constraints }),
    });
  }

  async getTaskGraph(projectId: string): Promise<any> {
    return this.fetch(`/architect/task-graph/${projectId}`);
  }

  async getNextTasks(projectId?: string): Promise<{
    tasks: any[];
    count: number;
    error?: string;
  }> {
    const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : '';
    return this.fetch(`/architect/next-tasks${query}`);
  }

  async analyzeArchitecture(): Promise<{
    status: string;
    analysis?: {
      components: any[];
      patterns: string[];
      technologies: string[];
      structure: any;
    };
    error?: string;
  }> {
    return this.fetch('/architect/analyze-architecture');
  }

  async findSimilarImplementations(feature: string): Promise<{
    status: string;
    similar_implementations?: Array<{
      file: string;
      symbols: string[];
      summary: string;
      relevance: number;
    }>;
    error?: string;
  }> {
    return this.fetch('/architect/find-similar', {
      method: 'POST',
      body: JSON.stringify({ feature }),
    });
  }

  // Analyzer endpoints
  async getArchitectureReport(): Promise<{
    status: string;
    report?: any;
    error?: string;
  }> {
    return this.fetch('/analyzer/report');
  }

  async getArchitectureDiagram(): Promise<{
    status: string;
    diagram?: string;
    format?: string;
    error?: string;
  }> {
    return this.fetch('/analyzer/diagram');
  }

  async refreshArchitectureAnalysis(): Promise<{
    status: string;
    message?: string;
    summary?: string;
    error?: string;
  }> {
    return this.fetch('/analyzer/refresh', {
      method: 'POST',
    });
  }

  async getArchitectureSummary(): Promise<{
    status: string;
    summary?: string;
    format?: string;
    error?: string;
  }> {
    return this.fetch('/analyzer/summary');
  }

  // Change Tracker endpoints
  async trackDiff(diff: {
    diff_content: string;
    file_path: string;
    agent_type?: string;
    commit_hash?: string;
  }): Promise<{
    status: string;
    stats?: {
      lines_added: number;
      lines_removed: number;
      total_changed: number;
    };
    current_metrics?: any;
    error?: string;
  }> {
    return this.fetch('/changes/track-diff', {
      method: 'POST',
      body: JSON.stringify(diff),
    });
  }

  async trackPatches(patches: any[], agent_type?: string): Promise<{
    status: string;
    patches_tracked?: number;
    results?: any[];
    current_metrics?: any;
    error?: string;
  }> {
    return this.fetch('/changes/track-patches', {
      method: 'POST',
      body: JSON.stringify({ patches, agent_type }),
    });
  }

  async getChangeMetrics(): Promise<{
    status: string;
    metrics?: any;
    recent_changes?: any[];
    error?: string;
  }> {
    return this.fetch('/changes/metrics');
  }

  async resetChangeMetrics(): Promise<{
    status: string;
    message?: string;
    error?: string;
  }> {
    return this.fetch('/changes/reset', {
      method: 'POST',
    });
  }
}

export const api = new ApiClient();