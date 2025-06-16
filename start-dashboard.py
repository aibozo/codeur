#!/usr/bin/env python3
"""
Cross-platform dashboard launcher.
Starts both frontend and backend services.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
import platform

class DashboardLauncher:
    def __init__(self):
        self.processes = []
        self.root_dir = Path(__file__).parent
        self.frontend_dir = self.root_dir / "frontend"
        self.is_windows = platform.system() == "Windows"
        
    def cleanup(self, signum=None, frame=None):
        """Clean up all processes on exit."""
        print("\n🛑 Shutting down services...")
        for process in self.processes:
            try:
                if self.is_windows:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], 
                                 capture_output=True)
                else:
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
        sys.exit(0)
        
    def check_dependencies(self):
        """Check if all dependencies are installed."""
        print("🔍 Checking dependencies...")
        
        # Check Python dependencies
        try:
            import fastapi
            import uvicorn
            print("✅ Python dependencies OK")
        except ImportError:
            print("📦 Installing Python dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                         cwd=self.root_dir)
            subprocess.run([sys.executable, "-m", "pip", "install", 
                          "networkx", "psutil", "GPUtil", "redis"], 
                         cwd=self.root_dir)
        
        # Check frontend dependencies
        node_modules = self.frontend_dir / "node_modules"
        if not node_modules.exists():
            print("📦 Installing frontend dependencies...")
            npm_cmd = "npm.cmd" if self.is_windows else "npm"
            subprocess.run([npm_cmd, "install"], cwd=self.frontend_dir)
            
        print("✅ All dependencies installed")
        
    def start_backend(self):
        """Start the backend server."""
        print("🚀 Starting backend server on port 8088...")
        
        # Use the minimal server for now
        backend_script = self.root_dir / "minimal_webhook_server.py"
        
        cmd = [sys.executable, str(backend_script)]
        
        if self.is_windows:
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(cmd)
            
        self.processes.append(process)
        
        # Wait for backend to start
        time.sleep(3)
        
        # Check if backend is running
        try:
            import requests
            response = requests.get("http://localhost:8088/health")
            if response.status_code == 200:
                print("✅ Backend is running")
            else:
                print("⚠️  Backend may not be fully started")
        except:
            print("⚠️  Could not verify backend status")
            
    def start_frontend(self):
        """Start the frontend development server."""
        print("🚀 Starting frontend on port 5173...")
        
        npm_cmd = "npm.cmd" if self.is_windows else "npm"
        cmd = [npm_cmd, "run", "dev", "--", "--host"]
        
        if self.is_windows:
            process = subprocess.Popen(
                cmd,
                cwd=self.frontend_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            process = subprocess.Popen(cmd, cwd=self.frontend_dir)
            
        self.processes.append(process)
        
    def run(self):
        """Run the dashboard launcher."""
        print("🚀 Codeur Dashboard Launcher")
        print("=" * 40)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.cleanup)
        if not self.is_windows:
            signal.signal(signal.SIGTERM, self.cleanup)
        
        try:
            # Check dependencies
            self.check_dependencies()
            
            # Start services
            self.start_backend()
            self.start_frontend()
            
            # Show URLs
            print("\n✅ Dashboard is ready!")
            print("=" * 40)
            print("📊 Frontend: http://localhost:5173")
            print("🔧 Backend API: http://localhost:8088")
            print("📚 API Docs: http://localhost:8088/docs")
            print("\nPress Ctrl+C to stop all services")
            
            # Keep running
            while True:
                # Check if processes are still running
                for process in self.processes:
                    if process.poll() is not None:
                        print(f"\n⚠️  A service has stopped unexpectedly")
                        self.cleanup()
                        
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self.cleanup()

if __name__ == "__main__":
    launcher = DashboardLauncher()
    launcher.run()