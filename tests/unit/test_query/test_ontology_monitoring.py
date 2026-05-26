"""
Tests for ontology monitoring metrics.
"""

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "trustgraph-flow"
    / "trustgraph"
    / "query"
    / "ontology"
    / "monitoring.py"
)
spec = importlib.util.spec_from_file_location("ontology_monitoring", MODULE_PATH)
assert spec is not None and spec.loader is not None
monitoring = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = monitoring
spec.loader.exec_module(monitoring)

PerformanceMonitor = monitoring.PerformanceMonitor
_extract_metric_label = monitoring._extract_metric_label


def test_extract_metric_label_reads_unquoted_label_value():
    metric_name = "cache_requests_total{cache_type=entity,component=ontology}"

    assert _extract_metric_label(metric_name, "cache_type") == "entity"


def test_extract_metric_label_reads_quoted_label_value():
    metric_name = 'cache_requests_total{cache_type="entity",component="ontology"}'

    assert _extract_metric_label(metric_name, "cache_type") == "entity"


def test_extract_metric_label_returns_none_when_label_missing():
    metric_name = "cache_requests_total{component=ontology}"

    assert _extract_metric_label(metric_name, "cache_type") is None


def test_performance_report_ignores_counters_without_cache_type_label():
    monitor = PerformanceMonitor({"enabled": False})
    monitor.metrics_collector.increment(
        "cache_requests_total",
        labels={"component": "ontology"},
    )
    monitor.metrics_collector.increment(
        "cache_type=not_a_label",
        labels={"component": "ontology"},
    )
    monitor.metrics_collector.increment(
        "cache_requests_total",
        labels={"cache_type": "entity"},
    )
    monitor.metrics_collector.increment(
        "cache_hits_total",
        labels={"cache_type": "entity"},
    )

    report = monitor.get_performance_report()

    assert report["cache_performance"] == {
        "entity": {
            "hit_rate": 1.0,
            "total_requests": 1.0,
            "total_hits": 1.0,
        }
    }
