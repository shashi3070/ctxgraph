import pytest
from dataflow.events.bus import EventBus
from dataflow.events.handler import CallbackHandler, LoggingHandler, MetricsHandler
from dataflow.events.types import PipelineEvent, ErrorEvent, MetricEvent


class TestEventBus:
    def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []
        bus.subscribe("test_event", CallbackHandler(lambda e: received.append(e)))
        event = PipelineEvent("test_pipe", "test_event")
        bus.emit(event)
        assert len(received) == 1
        assert received[0].type == "test_event"

    def test_wildcard_handler(self):
        bus = EventBus()
        received = []
        bus.subscribe_all(CallbackHandler(lambda e: received.append(e)))
        bus.emit(PipelineEvent("p", "type_a"))
        bus.emit(ErrorEvent("src", "type_b", "err"))
        assert len(received) == 2

    def test_unsubscribe(self):
        bus = EventBus()
        handler = CallbackHandler(lambda e: None)
        bus.subscribe("t", handler)
        assert bus.handler_count() == 1
        bus.unsubscribe("t", handler)
        assert bus.handler_count() == 0

    def test_clear(self):
        bus = EventBus()
        bus.subscribe("a", CallbackHandler(lambda e: None))
        bus.subscribe("b", CallbackHandler(lambda e: None))
        bus.clear()
        assert bus.handler_count() == 0

    def test_metrics_handler(self):
        handler = MetricsHandler()
        bus = EventBus()
        bus.subscribe("metric", handler)
        bus.emit(MetricEvent("test", 42.0))
        assert handler.get_count("metric") == 1
        bus.emit(MetricEvent("test", 100.0))
        assert handler.get_count("metric") == 2


class TestEventTypes:
    def test_pipeline_event(self):
        event = PipelineEvent("my_pipeline", "started", {"version": "1.0"})
        assert event.pipeline_name == "my_pipeline"
        assert "version" in event.data
        assert event.to_dict()["type"] == "started"

    def test_error_event(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            event = ErrorEvent("test_processor", "ValueError", str(e), e)
            assert event.data["error_type"] == "ValueError"
            assert event.data["message"] == "test error"

    def test_metric_event(self):
        event = MetricEvent("processing_rate", 150.0, {"unit": "req/s"})
        assert event.data["value"] == 150.0
        assert event.data["tags"]["unit"] == "req/s"
