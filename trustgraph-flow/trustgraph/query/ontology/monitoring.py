"""
Performance monitoring and metrics collection for OntoRAG.
Provides comprehensive monitoring of system performance, query patterns, and resource usage.
"""

import logging
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class TimerMetric:
    """Timer metric for measuring duration."""
    name: str
    start_time: float
    labels: Dict[str, str] = field(default_factory=dict)

    def stop(self) -> float:
        """Stop timer and return duration."""
        return time.time() - self.start_time


@dataclass
class PerformanceStats:
    """Performance statistics for a component."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0


@dataclass
class SystemHealth:
    """Overall system health metrics."""
    status: str = "healthy"  # healthy, degraded, unhealthy
    uptime_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    active_connections: int = 0
    queue_size: int = 0
    cache_hit_rate: float = 0.0
    error_rate: float = 0.0


class MetricsCollector:
    """Collects and stores metrics data."""

    def __init__(self, max_metrics: int = 10000, retention_hours: int = 24):
        """Initialize metrics collector.

        Args:
            max_metrics: Maximum number of metrics to retain
            retention_hours: Hours to retain metrics
        """
        self.max_metrics = max_metrics
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()

    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to increment by
            labels: Metric labels
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self.counters[metric_key] += value
            self._add_metric(name, value, MetricType.COUNTER, labels)

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value.

        Args:
            name: Metric name
            value: Gauge value
            labels: Metric labels
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self.gauges[metric_key] = value
            self._add_metric(name, value, MetricType.GAUGE, labels)

    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """Record a timer measurement.

        Args:
            name: Metric name
            duration: Duration in seconds
            labels: Metric labels
        """
        with self._lock:
            metric_key = self._build_key(name, labels)
            self.timers[metric_key].append(duration)

            # Keep only recent measurements
            max_timer_values = 1000
            if len(self.timers[metric_key]) > max_timer_values:
                self.timers[metric_key] = self.timers[metric_key][-max_timer_values:]

            self._add_metric(name, duration, MetricType.TIMER, labels)

    def start_timer(self, name: str, labels: Dict[str, str] = None) -> TimerMetric:
        """Start a timer.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Timer metric object
        """
        return TimerMetric(name=name, start_time=time.time(), labels=labels or {})

    def stop_timer(self, timer: TimerMetric):
        """Stop a timer and record the measurement.

        Args:
            timer: Timer metric to stop
        """
        duration = timer.stop()
        self.record_timer(timer.name, duration, timer.labels)
        return duration

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get counter value.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Counter value
        """
        metric_key = self._build_key(name, labels)
        return self.counters.get(metric_key, 0.0)

    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        """Get gauge value.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Gauge value
        """
        metric_key = self._build_key(name, labels)
        return self.gauges.get(metric_key, 0.0)

    def get_timer_stats(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get timer statistics.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Timer statistics
        """
        metric_key = self._build_key(name, labels)
        values = self.timers.get(metric_key, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'p50': sorted_values[int(len(sorted_values) * 0.5)],
            'p95': sorted_values[int(len(sorted_values) * 0.95)],
            'p99': sorted_values[int(len(sorted_values) * 0.99)]
        }

    def get_metrics(self,
                   name_pattern: Optional[str] = None,
                   since: Optional[datetime] = None) -> List[Metric]:
        """Get metrics matching pattern and time range.

        Args:
            name_pattern: Pattern to match metric names
            since: Only return metrics since this time

        Returns:
            List of matching metrics
        """
        with self._lock:
            results = []
            cutoff_time = since or datetime.now() - timedelta(hours=self.retention_hours)

            for metric_name, metric_queue in self.metrics.items():
                if name_pattern and name_pattern not in metric_name:
                    continue

                for metric in metric_queue:
                    if metric.timestamp >= cutoff_time:
                        results.append(metric)

            return sorted(results, key=lambda m: m.timestamp)

    def cleanup_old_metrics(self):
        """Remove old metrics beyond retention period."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

            for metric_name in list(self.metrics.keys()):
                metric_queue = self.metrics[metric_name]
                # Remove old metrics
                while metric_queue and metric_queue[0].timestamp < cutoff_time:
                    metric_queue.popleft()

                # Remove empty queues
                if not metric_queue:
                    del self.metrics[metric_name]

    def _add_metric(self, name: str, value: float, metric_type: MetricType, labels: Dict[str, str]):
        """Add metric to storage."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metric_type=metric_type
        )
        self.metrics[name].append(metric)

    def _build_key(self, name: str, labels: Dict[str, str]) -> str:
        """Build metric key from name and labels."""
        if not labels:
            return name

        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class PerformanceMonitor:
    """Monitors system performance and component health."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize performance monitor.

        Args:
            config: Monitor configuration
        """
        self.config = config or {}
        self.metrics_collector = MetricsCollector(
            max_metrics=self.config.get('max_metrics', 10000),
            retention_hours=self.config.get('retention_hours', 24)
        )

        self.component_stats: Dict[str, PerformanceStats] = {}
        self.start_time = time.time()
        self.monitoring_enabled = self.config.get('enabled', True)

        # Start background monitoring tasks
        if self.monitoring_enabled:
            self._start_background_tasks()

    def record_request(self,
                      component: str,
                      operation: str,
                      duration: float,
                      success: bool = True,
                      labels: Dict[str, str] = None):
        """Record a request completion.

        Args:
            component: Component name
            operation: Operation name
            duration: Request duration in seconds
            success: Whether request was successful
            labels: Additional labels
        """
        if not self.monitoring_enabled:
            return

        base_labels = {'component': component, 'operation': operation}
        if labels:
            base_labels.update(labels)

        # Record metrics
        self.metrics_collector.increment('requests_total', labels=base_labels)
        self.metrics_collector.record_timer('request_duration', duration, base_labels)

        if success:
            self.metrics_collector.increment('requests_successful', labels=base_labels)
        else:
            self.metrics_collector.increment('requests_failed', labels=base_labels)

        # Update component stats
        self._update_component_stats(component, duration, success)

    def record_query_complexity(self,
                               complexity_score: float,
                               query_type: str,
                               backend: str):
        """Record query complexity metrics.

        Args:
            complexity_score: Query complexity score (0.0 to 1.0)
            query_type: Type of query (SPARQL, Cypher)
            backend: Backend used
        """
        if not self.monitoring_enabled:
            return

        labels = {'query_type': query_type, 'backend': backend}
        self.metrics_collector.set_gauge('query_complexity', complexity_score, labels)

    def record_cache_access(self, hit: bool, cache_type: str = 'default'):
        """Record cache access.

        Args:
            hit: Whether it was a cache hit
            cache_type: Type of cache
        """
        if not self.monitoring_enabled:
            return

        labels = {'cache_type': cache_type}
        self.metrics_collector.increment('cache_requests_total', labels=labels)

        if hit:
            self.metrics_collector.increment('cache_hits_total', labels=labels)
        else:
            self.metrics_collector.increment('cache_misses_total', labels=labels)

    def record_ontology_selection(self,
                                 selected_elements: int,
                                 total_elements: int,
                                 ontology_id: str):
        """Record ontology selection metrics.

        Args:
            selected_elements: Number of selected ontology elements
            total_elements: Total ontology elements
            ontology_id: Ontology identifier
        """
        if not self.monitoring_enabled:
            return

        labels = {'ontology_id': ontology_id}
        self.metrics_collector.set_gauge('ontology_elements_selected', selected_elements, labels)
        self.metrics_collector.set_gauge('ontology_elements_total', total_elements, labels)

        selection_ratio = selected_elements / total_elements if total_elements > 0 else 0
        self.metrics_collector.set_gauge('ontology_selection_ratio', selection_ratio, labels)

    def get_component_stats(self, component: str) -> Optional[PerformanceStats]:
        """Get performance statistics for a component.

        Args:
            component: Component name

        Returns:
            Performance statistics or None
        """
        return self.component_stats.get(component)

    def get_system_health(self) -> SystemHealth:
        """Get overall system health status.

        Returns:
            System health metrics
        """
        # Calculate uptime
        uptime = time.time() - self.start_time

        # Get error rate
        total_requests = self.metrics_collector.get_counter('requests_total')
        failed_requests = self.metrics_collector.get_counter('requests_failed')
        error_rate = failed_requests / total_requests if total_requests > 0 else 0.0

        # Get cache hit rate
        cache_hits = self.metrics_collector.get_counter('cache_hits_total')
        cache_requests = self.metrics_collector.get_counter('cache_requests_total')
        cache_hit_rate = cache_hits / cache_requests if cache_requests > 0 else 0.0

        # Determine status
        status = "healthy"
        if error_rate > 0.1:  # More than 10% error rate
            status = "degraded"
        if error_rate > 0.3:  # More than 30% error rate
            status = "unhealthy"

        return SystemHealth(
            status=status,
            uptime_seconds=uptime,
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report.

        Returns:
            Performance report
        """
        report = {
            'system_health': self.get_system_health(),
            'component_stats': {},
            'top_slow_operations': [],
            'error_patterns': {},
            'cache_performance': {},
            'ontology_usage': {}
        }

        # Component statistics
        for component, stats in self.component_stats.items():
            report['component_stats'][component] = stats

        # Top slow operations
        timer_stats = {}
        for metric_name in self.metrics_collector.timers.keys():
            if 'request_duration' in metric_name:
                stats = self.metrics_collector.get_timer_stats(metric_name)
                if stats:
                    timer_stats[metric_name] = stats

        # Sort by p95 latency
        slow_ops = sorted(
            timer_stats.items(),
            key=lambda x: x[1].get('p95', 0),
            reverse=True
        )[:10]

        report['top_slow_operations'] = [
            {'operation': op, 'stats': stats} for op, stats in slow_ops
        ]

        # Cache performance
        cache_types = set()
        for metric_name in self.metrics_collector.counters.keys():
            if 'cache_type=' in metric_name:
                cache_type = metric_name.split('cache_type=')[1].split(',')[0].split('}')[0]
                cache_types.add(cache_type)

        for cache_type in cache_types:
            labels = {'cache_type': cache_type}
            hits = self.metrics_collector.get_counter('cache_hits_total', labels)
            requests = self.metrics_collector.get_counter('cache_requests_total', labels)
            hit_rate = hits / requests if requests > 0 else 0.0

            report['cache_performance'][cache_type] = {
                'hit_rate': hit_rate,
                'total_requests': requests,
                'total_hits': hits
            }

        return report

    def _update_component_stats(self, component: str, duration: float, success: bool):
        """Update component performance statistics."""
        if component not in self.component_stats:
            self.component_stats[component] = PerformanceStats()

        stats = self.component_stats[component]
        stats.total_requests += 1

        if success:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1

        # Update response time stats
        stats.min_response_time = min(stats.min_response_time, duration)
        stats.max_response_time = max(stats.max_response_time, duration)

        # Get timer stats for percentiles
        timer_stats = self.metrics_collector.get_timer_stats(
            'request_duration', {'component': component}
        )

        if timer_stats:
            stats.avg_response_time = timer_stats.get('avg', 0.0)
            stats.p95_response_time = timer_stats.get('p95', 0.0)
            stats.p99_response_time = timer_stats.get('p99', 0.0)

        # Calculate rates
        stats.error_rate = stats.failed_requests / stats.total_requests

        # Calculate throughput (requests per second over last minute)
        recent_requests = len([
            m for m in self.metrics_collector.get_metrics('requests_total')
            if m.labels.get('component') == component and
            m.timestamp > datetime.now() - timedelta(minutes=1)
        ])
        stats.throughput_per_second = recent_requests / 60.0

    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        def cleanup_worker():
            """Worker to clean up old metrics."""
            while True:
                try:
                    time.sleep(300)  # 5 minutes
                    self.metrics_collector.cleanup_old_metrics()
                except Exception as e:
                    logger.error(f"Metrics cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


# Monitoring decorators

def monitor_performance(component: str,
                       operation: str,
                       monitor: Optional[PerformanceMonitor] = None):
    """Decorator to monitor function performance.

    Args:
        component: Component name
        operation: Operation name
        monitor: Performance monitor instance
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not monitor or not monitor.monitoring_enabled:
                return func(*args, **kwargs)

            timer = monitor.metrics_collector.start_timer(
                'request_duration',
                {'component': component, 'operation': operation}
            )

            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = monitor.metrics_collector.stop_timer(timer)
                monitor.record_request(component, operation, duration, success)

        async def async_wrapper(*args, **kwargs):
            if not monitor or not monitor.monitoring_enabled:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            timer = monitor.metrics_collector.start_timer(
                'request_duration',
                {'component': component, 'operation': operation}
            )

            success = True
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = monitor.metrics_collector.stop_timer(timer)
                monitor.record_request(component, operation, duration, success)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper

    return decorator


class QueryPatternAnalyzer:
    """Analyzes query patterns for optimization insights."""

    def __init__(self, monitor: PerformanceMonitor):
        """Initialize query pattern analyzer.

        Args:
            monitor: Performance monitor instance
        """
        self.monitor = monitor
        self.query_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_query_pattern(self,
                            question_type: str,
                            entities: List[str],
                            complexity: float,
                            backend: str,
                            duration: float,
                            success: bool):
        """Record a query pattern for analysis.

        Args:
            question_type: Type of question
            entities: Entities in question
            complexity: Query complexity score
            backend: Backend used
            duration: Query duration
            success: Whether query succeeded
        """
        pattern = {
            'timestamp': datetime.now(),
            'question_type': question_type,
            'entity_count': len(entities),
            'entities': entities,
            'complexity': complexity,
            'backend': backend,
            'duration': duration,
            'success': success
        }

        pattern_key = f"{question_type}:{len(entities)}"
        self.query_patterns[pattern_key].append(pattern)

        # Keep only recent patterns
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.query_patterns[pattern_key] = [
            p for p in self.query_patterns[pattern_key]
            if p['timestamp'] > cutoff_time
        ]

    def get_optimization_insights(self) -> Dict[str, Any]:
        """Get insights for query optimization.

        Returns:
            Optimization insights and recommendations
        """
        insights = {
            'slow_patterns': [],
            'common_failures': [],
            'backend_performance': {},
            'complexity_analysis': {},
            'recommendations': []
        }

        # Analyze slow patterns
        for pattern_key, patterns in self.query_patterns.items():
            if not patterns:
                continue

            avg_duration = statistics.mean([p['duration'] for p in patterns])
            success_rate = sum(1 for p in patterns if p['success']) / len(patterns)

            if avg_duration > 5.0:  # Slow queries > 5 seconds
                insights['slow_patterns'].append({
                    'pattern': pattern_key,
                    'avg_duration': avg_duration,
                    'count': len(patterns),
                    'success_rate': success_rate
                })

            if success_rate < 0.8:  # Low success rate
                insights['common_failures'].append({
                    'pattern': pattern_key,
                    'success_rate': success_rate,
                    'count': len(patterns)
                })

        # Analyze backend performance
        backend_stats = defaultdict(list)
        for patterns in self.query_patterns.values():
            for pattern in patterns:
                backend_stats[pattern['backend']].append(pattern['duration'])

        for backend, durations in backend_stats.items():
            insights['backend_performance'][backend] = {
                'avg_duration': statistics.mean(durations),
                'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
                'query_count': len(durations)
            }

        # Generate recommendations
        recommendations = []

        # Slow pattern recommendations
        for slow_pattern in insights['slow_patterns']:
            recommendations.append(
                f"Consider optimizing {slow_pattern['pattern']} queries - "
                f"average duration {slow_pattern['avg_duration']:.2f}s"
            )

        # Backend recommendations
        if len(insights['backend_performance']) > 1:
            fastest_backend = min(
                insights['backend_performance'].items(),
                key=lambda x: x[1]['avg_duration']
            )[0]
            recommendations.append(
                f"Consider routing more queries to {fastest_backend} "
                f"for better performance"
            )

        insights['recommendations'] = recommendations

        return insights