"""
Historical data storage and retrieval for dashboard analytics.

This module provides time-series data storage for metrics, agent activity,
and system performance tracking over time.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
import json
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
except (ImportError, AttributeError):
    try:
        import aioredis as redis
    except ImportError:
        redis = None

from src.core.logging import get_logger
from src.core.settings import get_settings

logger = get_logger(__name__)


class TimeWindow(Enum):
    """Time windows for data aggregation."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TimeSeriesData:
    """Time series data for a metric."""
    metric_name: str
    points: List[MetricPoint]
    window: TimeWindow
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metric_name': self.metric_name,
            'window': self.window.value,
            'points': [
                {
                    'timestamp': p.timestamp.isoformat(),
                    'value': p.value,
                    'metadata': p.metadata
                }
                for p in self.points
            ]
        }


class HistoricalDataService:
    """
    Service for storing and retrieving historical metrics data.
    
    Provides time-series storage with multiple aggregation windows
    and efficient querying for dashboard visualizations.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize historical data service.
        
        Args:
            redis_client: Optional Redis client for persistent storage
        """
        self.redis_client = redis_client
        self.settings = get_settings()
        
        # In-memory storage for recent data (fallback if no Redis)
        self.memory_store: Dict[str, Dict[TimeWindow, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=1000))
        )
        
        # Aggregation tasks
        self._aggregation_tasks = {}
        self._running = False
        
    async def start(self):
        """Start the historical data service."""
        if self._running:
            return
            
        self._running = True
        
        # Start aggregation tasks for each window
        for window in TimeWindow:
            self._aggregation_tasks[window] = asyncio.create_task(
                self._aggregation_loop(window)
            )
        
        logger.info("Started historical data service")
        
    async def stop(self):
        """Stop the historical data service."""
        self._running = False
        
        # Cancel aggregation tasks
        for task in self._aggregation_tasks.values():
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._aggregation_tasks.values(), return_exceptions=True)
        
        logger.info("Stopped historical data service")
    
    async def record_metric(self, metric_name: str, value: float, 
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric (e.g., 'cpu_usage', 'queue_length')
            value: Metric value
            metadata: Optional metadata for the data point
        """
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            metadata=metadata
        )
        
        # Store in memory (1-minute window always stored)
        self.memory_store[metric_name][TimeWindow.MINUTE_1].append(point)
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_in_redis(metric_name, point)
    
    async def get_metric_history(self, metric_name: str, window: TimeWindow,
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None) -> TimeSeriesData:
        """
        Get historical data for a metric.
        
        Args:
            metric_name: Name of the metric
            window: Time window for aggregation
            start_time: Start of time range (default: now - window)
            end_time: End of time range (default: now)
            
        Returns:
            Time series data for the metric
        """
        if not end_time:
            end_time = datetime.utcnow()
            
        if not start_time:
            # Default to appropriate range for window
            duration_map = {
                TimeWindow.MINUTE_1: timedelta(hours=1),
                TimeWindow.MINUTE_5: timedelta(hours=4),
                TimeWindow.MINUTE_15: timedelta(hours=12),
                TimeWindow.HOUR_1: timedelta(days=2),
                TimeWindow.HOUR_4: timedelta(days=7),
                TimeWindow.DAY_1: timedelta(days=30),
                TimeWindow.WEEK_1: timedelta(days=180)
            }
            start_time = end_time - duration_map.get(window, timedelta(hours=1))
        
        # Try Redis first
        if self.redis_client:
            points = await self._get_from_redis(metric_name, window, start_time, end_time)
            if points:
                return TimeSeriesData(metric_name, points, window)
        
        # Fall back to memory store
        points = self._get_from_memory(metric_name, window, start_time, end_time)
        return TimeSeriesData(metric_name, points, window)
    
    async def get_agent_activity_timeline(self, agent_type: str,
                                        hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get agent activity timeline.
        
        Args:
            agent_type: Type of agent
            hours: Number of hours to look back
            
        Returns:
            List of activity events
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get task completion metrics
        task_data = await self.get_metric_history(
            f"agent.{agent_type}.tasks_completed",
            TimeWindow.MINUTE_5,
            start_time,
            end_time
        )
        
        # Get status change events from Redis if available
        events = []
        if self.redis_client:
            key = f"agent_timeline:{agent_type}"
            raw_events = await self.redis_client.zrangebyscore(
                key,
                start_time.timestamp(),
                end_time.timestamp()
            )
            
            for event_json in raw_events:
                try:
                    events.append(json.loads(event_json))
                except:
                    pass
        
        return events
    
    async def get_system_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get system metrics summary for the specified time period.
        
        Args:
            hours: Number of hours to summarize
            
        Returns:
            Summary statistics for system metrics
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Determine appropriate window based on time range
        if hours <= 1:
            window = TimeWindow.MINUTE_1
        elif hours <= 4:
            window = TimeWindow.MINUTE_5
        elif hours <= 24:
            window = TimeWindow.MINUTE_15
        else:
            window = TimeWindow.HOUR_1
        
        # Get metrics
        metrics_to_fetch = [
            'system.cpu.usage_percent',
            'system.memory.percent',
            'queue.length',
            'queue.processing',
            'flow.messages_per_minute'
        ]
        
        summary = {}
        for metric in metrics_to_fetch:
            data = await self.get_metric_history(metric, window, start_time, end_time)
            if data.points:
                values = [p.value for p in data.points]
                summary[metric] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'current': values[-1] if values else 0,
                    'points': len(values)
                }
            else:
                summary[metric] = {
                    'min': 0, 'max': 0, 'avg': 0, 'current': 0, 'points': 0
                }
        
        return summary
    
    async def _store_in_redis(self, metric_name: str, point: MetricPoint) -> None:
        """Store a metric point in Redis."""
        try:
            # Store in sorted set with timestamp as score
            key = f"metrics:{metric_name}:raw"
            member = json.dumps({
                'v': point.value,
                'm': point.metadata
            })
            
            await self.redis_client.zadd(
                key,
                {member: point.timestamp.timestamp()}
            )
            
            # Set expiration (7 days for raw data)
            await self.redis_client.expire(key, 7 * 24 * 3600)
            
        except Exception as e:
            logger.error(f"Error storing metric in Redis: {e}")
    
    async def _get_from_redis(self, metric_name: str, window: TimeWindow,
                            start_time: datetime, end_time: datetime) -> List[MetricPoint]:
        """Get metric points from Redis."""
        try:
            # Get appropriate key based on window
            if window == TimeWindow.MINUTE_1:
                key = f"metrics:{metric_name}:raw"
            else:
                key = f"metrics:{metric_name}:{window.value}"
            
            # Get data from sorted set
            data = await self.redis_client.zrangebyscore(
                key,
                start_time.timestamp(),
                end_time.timestamp(),
                withscores=True
            )
            
            points = []
            for member, score in data:
                try:
                    data_dict = json.loads(member)
                    points.append(MetricPoint(
                        timestamp=datetime.fromtimestamp(score),
                        value=data_dict['v'],
                        metadata=data_dict.get('m')
                    ))
                except:
                    pass
            
            return points
            
        except Exception as e:
            logger.error(f"Error getting metrics from Redis: {e}")
            return []
    
    def _get_from_memory(self, metric_name: str, window: TimeWindow,
                        start_time: datetime, end_time: datetime) -> List[MetricPoint]:
        """Get metric points from memory store."""
        points = []
        
        if metric_name in self.memory_store and window in self.memory_store[metric_name]:
            for point in self.memory_store[metric_name][window]:
                if start_time <= point.timestamp <= end_time:
                    points.append(point)
        
        return points
    
    async def _aggregation_loop(self, window: TimeWindow) -> None:
        """Aggregation loop for a specific time window."""
        # Window configurations
        window_config = {
            TimeWindow.MINUTE_1: {'interval': 60, 'source': None},
            TimeWindow.MINUTE_5: {'interval': 300, 'source': TimeWindow.MINUTE_1},
            TimeWindow.MINUTE_15: {'interval': 900, 'source': TimeWindow.MINUTE_5},
            TimeWindow.HOUR_1: {'interval': 3600, 'source': TimeWindow.MINUTE_15},
            TimeWindow.HOUR_4: {'interval': 14400, 'source': TimeWindow.HOUR_1},
            TimeWindow.DAY_1: {'interval': 86400, 'source': TimeWindow.HOUR_4},
            TimeWindow.WEEK_1: {'interval': 604800, 'source': TimeWindow.DAY_1}
        }
        
        config = window_config[window]
        if not config['source']:  # Skip MINUTE_1 as it's raw data
            return
        
        while self._running:
            try:
                await asyncio.sleep(config['interval'])
                
                # Aggregate data from source window
                await self._aggregate_window(window, config['source'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation loop for {window.value}: {e}")
    
    async def _aggregate_window(self, target_window: TimeWindow, 
                              source_window: TimeWindow) -> None:
        """Aggregate data from source window to target window."""
        # This would aggregate data from smaller to larger time windows
        # Implementation depends on specific aggregation needs
        pass


# Singleton instance
_historical_service: Optional[HistoricalDataService] = None


async def get_historical_service() -> HistoricalDataService:
    """Get or create the historical data service singleton."""
    global _historical_service
    
    if not _historical_service:
        settings = get_settings()
        redis_client = None
        
        if settings.cache.redis_url and redis:
            try:
                redis_client = await redis.from_url(
                    settings.cache.redis_url,
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")
        
        _historical_service = HistoricalDataService(redis_client)
        await _historical_service.start()
    
    return _historical_service