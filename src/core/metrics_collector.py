"""
System metrics collection service for real-time monitoring.

This module provides CPU, memory, GPU, and process metrics collection
with WebSocket broadcasting for the dashboard.
"""

import asyncio
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    
from src.core.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collects and broadcasts system resource metrics."""
    
    def __init__(self, realtime_service, interval: int = 5):
        """
        Initialize metrics collector.
        
        Args:
            realtime_service: Service for WebSocket broadcasting
            interval: Collection interval in seconds
        """
        self.realtime_service = realtime_service
        self.interval = interval
        self._running = False
        self._task = None
        self._last_metrics = {}
        
    async def start(self):
        """Start collecting system metrics."""
        if self._running:
            logger.warning("Metrics collector already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._collection_loop())
        logger.info(f"Started metrics collector with {self.interval}s interval")
        
    async def stop(self):
        """Stop collecting metrics."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped metrics collector")
        
    async def _collection_loop(self):
        """Main collection loop."""
        while self._running:
            try:
                metrics = await self._collect_metrics()
                self._last_metrics = metrics
                
                # Broadcast to subscribers
                await self.realtime_service.broadcast({
                    'type': 'system_metrics',
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': metrics
                }, topic='metrics')
                
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.interval)
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        metrics = {}
        
        # CPU metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            
            metrics['cpu'] = {
                'usage_percent': cpu_percent,
                'frequency_current': cpu_freq.current if cpu_freq else 0,
                'frequency_min': cpu_freq.min if cpu_freq else 0,
                'frequency_max': cpu_freq.max if cpu_freq else 0,
                'cores_physical': cpu_count,
                'cores_logical': cpu_count_logical,
                'per_core_usage': psutil.cpu_percent(interval=0.1, percpu=True)
            }
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")
            metrics['cpu'] = self._get_default_cpu_metrics()
        
        # Memory metrics
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics['memory'] = {
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_gb': round(swap.used / (1024**3), 2),
                'swap_percent': swap.percent
            }
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
            metrics['memory'] = self._get_default_memory_metrics()
        
        # GPU metrics
        metrics['gpu'] = await self._collect_gpu_metrics()
        
        # Process metrics
        try:
            process = psutil.Process()
            process_info = process.as_dict(attrs=['cpu_percent', 'memory_info', 'num_threads', 'open_files'])
            
            metrics['process'] = {
                'memory_mb': round(process_info['memory_info'].rss / (1024**2), 2),
                'memory_percent': round(process.memory_percent(), 2),
                'cpu_percent': process_info['cpu_percent'],
                'threads': process_info['num_threads'],
                'open_files': len(process_info['open_files']) if process_info['open_files'] else 0
            }
        except Exception as e:
            logger.error(f"Error collecting process metrics: {e}")
            metrics['process'] = self._get_default_process_metrics()
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            metrics['network'] = {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")
            metrics['network'] = self._get_default_network_metrics()
        
        # Disk usage
        try:
            disk = psutil.disk_usage('/')
            metrics['disk'] = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")
            metrics['disk'] = self._get_default_disk_metrics()
            
        return metrics
    
    async def _collect_gpu_metrics(self) -> List[Dict[str, Any]]:
        """Collect GPU metrics if available."""
        gpu_metrics = []
        
        if not GPU_AVAILABLE:
            return gpu_metrics
            
        try:
            gpus = GPUtil.getGPUs()
            for i, gpu in enumerate(gpus):
                gpu_metrics.append({
                    'id': i,
                    'name': gpu.name,
                    'load_percent': round(gpu.load * 100, 1),
                    'memory_used_mb': round(gpu.memoryUsed, 1),
                    'memory_total_mb': round(gpu.memoryTotal, 1),
                    'memory_percent': round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1) if gpu.memoryTotal > 0 else 0,
                    'temperature': gpu.temperature,
                    'uuid': gpu.uuid
                })
        except Exception as e:
            logger.debug(f"Could not collect GPU metrics: {e}")
            
        return gpu_metrics
    
    def get_last_metrics(self) -> Dict[str, Any]:
        """Get the last collected metrics."""
        return self._last_metrics.copy()
    
    @staticmethod
    def _get_default_cpu_metrics() -> Dict[str, Any]:
        """Return default CPU metrics structure."""
        return {
            'usage_percent': 0,
            'frequency_current': 0,
            'frequency_min': 0,
            'frequency_max': 0,
            'cores_physical': 1,
            'cores_logical': 1,
            'per_core_usage': [0]
        }
    
    @staticmethod
    def _get_default_memory_metrics() -> Dict[str, Any]:
        """Return default memory metrics structure."""
        return {
            'total_gb': 0,
            'used_gb': 0,
            'available_gb': 0,
            'percent': 0,
            'swap_total_gb': 0,
            'swap_used_gb': 0,
            'swap_percent': 0
        }
    
    @staticmethod
    def _get_default_process_metrics() -> Dict[str, Any]:
        """Return default process metrics structure."""
        return {
            'memory_mb': 0,
            'memory_percent': 0,
            'cpu_percent': 0,
            'threads': 0,
            'open_files': 0
        }
    
    @staticmethod
    def _get_default_network_metrics() -> Dict[str, Any]:
        """Return default network metrics structure."""
        return {
            'bytes_sent_mb': 0,
            'bytes_recv_mb': 0,
            'packets_sent': 0,
            'packets_recv': 0
        }
    
    @staticmethod
    def _get_default_disk_metrics() -> Dict[str, Any]:
        """Return default disk metrics structure."""
        return {
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0,
            'percent': 0
        }