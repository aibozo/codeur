import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, Maximize2, Download, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

interface ArchitectureDiagramProps {
  className?: string;
  onRefresh?: () => void;
}

const ArchitectureDiagram: React.FC<ArchitectureDiagramProps> = ({ className = '', onRefresh }) => {
  const [diagram, setDiagram] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDiagram();
  }, []);

  const fetchDiagram = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.getArchitectureDiagram();
      if (response.status === 'success' && response.diagram) {
        setDiagram(response.diagram);
        // Render Mermaid diagram
        renderMermaid(response.diagram);
      } else {
        setError(response.error || 'Failed to load diagram');
      }
    } catch (err) {
      setError('Failed to fetch architecture diagram');
      console.error('Diagram error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderMermaid = async (mermaidCode: string) => {
    // Check if mermaid is loaded via CDN
    if (typeof window !== 'undefined' && (window as any).mermaid) {
      const mermaid = (window as any).mermaid;
      mermaid.initialize({ 
        startOnLoad: true,
        theme: 'dark',
        themeVariables: {
          primaryColor: '#9333EA',
          primaryTextColor: '#fff',
          primaryBorderColor: '#7C3AED',
          lineColor: '#6B7280',
          secondaryColor: '#1F2937',
          tertiaryColor: '#374151',
          background: '#111827',
          mainBkg: '#1F2937',
          secondBkg: '#374151',
          tertiaryBkg: '#4B5563',
          primaryBorderColor: '#6B7280',
          secondaryBorderColor: '#4B5563',
          tertiaryBorderColor: '#374151',
          primaryTextColor: '#F3F4F6',
          secondaryTextColor: '#E5E7EB',
          tertiaryTextColor: '#D1D5DB',
          textColor: '#F3F4F6',
          fontSize: '14px'
        }
      });
      
      // Clear previous diagram
      const element = document.getElementById('mermaid-diagram');
      if (element) {
        element.innerHTML = '';
        element.removeAttribute('data-processed');
        
        // Create a div with the mermaid code
        const graphDiv = document.createElement('div');
        graphDiv.className = 'mermaid';
        graphDiv.textContent = mermaidCode;
        element.appendChild(graphDiv);
        
        // Render the diagram
        await mermaid.init();
      }
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      await api.refreshArchitectureAnalysis();
      await fetchDiagram();
      onRefresh?.();
    } catch (err) {
      setError('Failed to refresh analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([diagram], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'architecture-diagram.mmd';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`bg-slate-800 rounded-xl shadow-lg ${isFullscreen ? 'fixed inset-0 z-50' : ''} ${className}`}
    >
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">Architecture Diagram</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh Analysis"
          >
            <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleDownload}
            disabled={!diagram}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            title="Download Diagram"
          >
            <Download className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Toggle Fullscreen"
          >
            <Maximize2 className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
            <p className="text-red-400">{error}</p>
            <button
              onClick={fetchDiagram}
              className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <div 
            id="mermaid-diagram" 
            className="min-h-[400px] overflow-auto bg-slate-900 rounded-lg p-4"
          />
        )}
      </div>
    </div>
  );
};

export default ArchitectureDiagram;