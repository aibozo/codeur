import React, { useState, useEffect } from 'react';
import { X, Folder, FolderOpen, File, ChevronUp, Home, HardDrive } from 'lucide-react';
import { api } from '../api/client';

interface DirectoryEntry {
  name: string;
  path: string;
  is_directory: boolean;
  size?: number;
  modified?: string;
}

interface DirectoryBrowseResponse {
  current_path: string;
  parent_path?: string;
  entries: DirectoryEntry[];
  can_write: boolean;
}

interface DirectoryBrowserProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (path: string) => void;
}

const DirectoryBrowser: React.FC<DirectoryBrowserProps> = ({ isOpen, onClose, onSelect }) => {
  const [currentPath, setCurrentPath] = useState('');
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<DirectoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDirectory();
    }
  }, [isOpen]);

  const loadDirectory = async (path?: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.browseDirectory(path);
      setCurrentPath(response.current_path);
      setParentPath(response.parent_path || null);
      setEntries(response.entries);
    } catch (err) {
      setError('Failed to load directory');
      console.error('Directory browse error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDirectoryClick = (entry: DirectoryEntry) => {
    if (entry.is_directory) {
      loadDirectory(entry.path);
    }
  };

  const handleSelect = () => {
    onSelect(currentPath);
    onClose();
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl shadow-2xl w-[800px] max-w-[90vw] h-[600px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Select Project Directory</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Path bar */}
        <div className="p-4 border-b border-slate-700 flex items-center gap-2">
          <button
            onClick={() => loadDirectory()}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            title="Home"
          >
            <Home className="w-4 h-4 text-gray-400" />
          </button>
          
          {parentPath && (
            <button
              onClick={() => loadDirectory(parentPath)}
              className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
              title="Up"
            >
              <ChevronUp className="w-4 h-4 text-gray-400" />
            </button>
          )}
          
          <div className="flex-1 bg-slate-700/50 rounded-lg px-3 py-2">
            <p className="text-sm text-gray-300 truncate">{currentPath || '/'}</p>
          </div>
        </div>

        {/* Directory listing */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-red-400">{error}</p>
            </div>
          ) : entries.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Empty directory</p>
            </div>
          ) : (
            <div className="space-y-1">
              {entries.map((entry) => (
                <div
                  key={entry.path}
                  onClick={() => handleDirectoryClick(entry)}
                  className={`flex items-center gap-3 p-3 rounded-lg hover:bg-slate-700 transition-colors ${
                    entry.is_directory ? 'cursor-pointer' : 'cursor-default opacity-60'
                  }`}
                >
                  {entry.is_directory ? (
                    <FolderOpen className="w-5 h-5 text-blue-400" />
                  ) : (
                    <File className="w-5 h-5 text-gray-400" />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{entry.name}</p>
                  </div>
                  
                  {!entry.is_directory && (
                    <p className="text-xs text-gray-500">
                      {formatFileSize(entry.size)}
                    </p>
                  )}
                  
                  <p className="text-xs text-gray-500">
                    {formatDate(entry.modified)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 flex items-center justify-between">
          <p className="text-sm text-gray-400">
            {entries.filter(e => e.is_directory).length} folders, {entries.filter(e => !e.is_directory).length} files
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSelect}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-lg transition-all duration-150"
            >
              Select This Directory
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DirectoryBrowser;