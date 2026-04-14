from unittest.mock import MagicMock

import pytest

from trustgraph.base import metrics


@pytest.fixture(autouse=True)
def reset_metric_singletons():
    """Temporarily remove metric singletons so each test can inject mocks.

    Saves any existing class-level metrics and restores them after the test
    so that later tests in the same process still find the hasattr() guard
    intact — deleting without restoring causes every subsequent Processor()
    construction to re-register the same Prometheus metric name, which raises
    ValueError: Duplicated timeseries.
    """
    classes_and_attrs = {
        metrics.ConsumerMetrics: [
            "state_metric",
            "request_metric",
            "processing_metric",
            "rate_limit_metric",
        ],
        metrics.ProducerMetrics: ["producer_metric"],
        metrics.ProcessorMetrics: ["processor_metric"],
        metrics.SubscriberMetrics: [
            "state_metric",
            "received_metric",
            "dropped_metric",
        ],
    }

    saved = {}
    for cls, attrs in classes_and_attrs.items():
        for attr in attrs:
            if hasattr(cls, attr):
                saved[(cls, attr)] = getattr(cls, attr)
                delattr(cls, attr)

    yield

    # Remove anything the test may have set, then restore originals
    for cls, attrs in classes_and_attrs.items():
        for attr in attrs:
            if hasattr(cls, attr):
                delattr(cls, attr)

    for (cls, attr), value in saved.items():
        setattr(cls, attr, value)


def test_consumer_metrics_reuses_singletons_and_records_events(monkeypatch):
    enum_factory = MagicMock()
    histogram_factory = MagicMock()
    counter_factory = MagicMock()

    state_labels = MagicMock()
    request_labels = MagicMock()
    processing_labels = MagicMock()
    rate_limit_labels = MagicMock()
    timer = MagicMock()

    enum_factory.return_value.labels.return_value = state_labels
    histogram_factory.return_value.labels.return_value = request_labels
    request_labels.time.return_value = timer
    counter_factory.side_effect = [
        MagicMock(labels=MagicMock(return_value=processing_labels)),
        MagicMock(labels=MagicMock(return_value=rate_limit_labels)),
    ]

    monkeypatch.setattr(metrics, "Enum", enum_factory)
    monkeypatch.setattr(metrics, "Histogram", histogram_factory)
    monkeypatch.setattr(metrics, "Counter", counter_factory)

    first = metrics.ConsumerMetrics("proc", "flow", "name")
    second = metrics.ConsumerMetrics("proc-2", "flow-2", "name-2")

    assert enum_factory.call_count == 1
    assert histogram_factory.call_count == 1
    assert counter_factory.call_count == 2

    first.process("ok")
    first.rate_limit()
    first.state("running")
    assert first.record_time() is timer

    processing_labels.inc.assert_called_once_with()
    rate_limit_labels.inc.assert_called_once_with()
    state_labels.state.assert_called_once_with("running")


def test_producer_metrics_increments_counter_once(monkeypatch):
    counter_factory = MagicMock()
    labels = MagicMock()
    counter_factory.return_value.labels.return_value = labels
    monkeypatch.setattr(metrics, "Counter", counter_factory)

    producer_metrics = metrics.ProducerMetrics("proc", "flow", "output")
    producer_metrics.inc()

    counter_factory.assert_called_once()
    labels.inc.assert_called_once_with()


def test_processor_metrics_reports_info(monkeypatch):
    info_factory = MagicMock()
    labels = MagicMock()
    info_factory.return_value.labels.return_value = labels
    monkeypatch.setattr(metrics, "Info", info_factory)

    processor_metrics = metrics.ProcessorMetrics("proc")
    processor_metrics.info({"kind": "test"})

    info_factory.assert_called_once()
    labels.info.assert_called_once_with({"kind": "test"})


def test_subscriber_metrics_tracks_received_state_and_dropped(monkeypatch):
    enum_factory = MagicMock()
    counter_factory = MagicMock()

    state_labels = MagicMock()
    received_labels = MagicMock()
    dropped_labels = MagicMock()

    enum_factory.return_value.labels.return_value = state_labels
    counter_factory.side_effect = [
        MagicMock(labels=MagicMock(return_value=received_labels)),
        MagicMock(labels=MagicMock(return_value=dropped_labels)),
    ]

    monkeypatch.setattr(metrics, "Enum", enum_factory)
    monkeypatch.setattr(metrics, "Counter", counter_factory)

    subscriber_metrics = metrics.SubscriberMetrics("proc", "flow", "input")
    subscriber_metrics.received()
    subscriber_metrics.state("running")
    subscriber_metrics.dropped("ignored")

    received_labels.inc.assert_called_once_with()
    dropped_labels.inc.assert_called_once_with()
    state_labels.state.assert_called_once_with("running")
