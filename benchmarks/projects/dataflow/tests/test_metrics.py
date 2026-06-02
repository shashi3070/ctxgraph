import pytest
from dataflow.metrics.collector import MetricsCollector, Counter, Gauge, Histogram
from dataflow.metrics.reporter import ConsoleReporter, FileReporter
from pathlib import Path
import tempfile


class TestMetricsCollector:
    def test_counter(self):
        c = MetricsCollector()
        cnt = c.counter("requests")
        cnt.inc()
        cnt.inc(5)
        assert cnt.value == 6

    def test_gauge(self):
        c = MetricsCollector()
        g = c.gauge("temperature")
        g.set(36.5)
        assert g.value == 36.5
        g.set(37.0)
        assert g.value == 37.0

    def test_histogram(self):
        c = MetricsCollector()
        h = c.histogram("latency")
        h.observe(10.0)
        h.observe(20.0)
        h.observe(30.0)
        assert h.count == 3
        assert h.sum == 60.0
        assert h.avg == 20.0
        assert h.min == 10.0
        assert h.max == 30.0

    def test_record_success_failure(self):
        c = MetricsCollector()
        c.record_success("pipe1")
        c.record_success("pipe1")
        c.record_failure("pipe1")
        assert c.counter("pipeline_success").value == 2
        assert c.counter("pipeline_failure").value == 1
        assert c.counter("pipeline_total").value == 3

    def test_uptime(self):
        c = MetricsCollector()
        assert c.uptime() > 0

    def test_to_dict(self):
        c = MetricsCollector()
        c.record_success("test")
        d = c.to_dict()
        assert "counters" in d
        assert "uptime" in d

    def test_reset(self):
        c = MetricsCollector()
        c.record_success("test")
        assert c.counter("pipeline_success").value == 1
        c.reset()
        assert c.counter("pipeline_success").value == 0


class TestFileReporter:
    def test_file_reporter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            c = MetricsCollector()
            c.record_success("test")
            reporter = FileReporter(path)
            reporter.report(c)
            assert path.exists()
            content = path.read_text()
            assert "pipeline_success" in content
