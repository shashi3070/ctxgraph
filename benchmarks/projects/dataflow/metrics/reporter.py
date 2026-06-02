from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from dataflow.metrics.collector import MetricsCollector


class MetricsReporter(ABC):
    @abstractmethod
    def report(self, collector: MetricsCollector) -> Any:
        ...


class ConsoleReporter(MetricsReporter):
    def __init__(self, interval: float = 60.0):
        self._interval = interval
        self._last_report: float = 0.0

    def report(self, collector: MetricsCollector) -> Optional[str]:
        now = time.time()
        if now - self._last_report < self._interval:
            return None
        self._last_report = now
        data = collector.to_dict()
        lines = ["=== Metrics Report ==="]
        for name, value in data.get("counters", {}).items():
            lines.append(f"  counter {name}: {value}")
        for name, value in data.get("gauges", {}).items():
            lines.append(f"  gauge {name}: {value}")
        for name, stats in data.get("histograms", {}).items():
            lines.append(f"  histogram {name}: count={stats['count']} avg={stats['avg']:.2f}")
        report = "\n".join(lines)
        print(report)
        return report


class FileReporter(MetricsReporter):
    def __init__(self, output_path: Path):
        self._output_path = output_path

    def report(self, collector: MetricsCollector) -> None:
        data = collector.to_dict()
        data["timestamp"] = time.time()
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        if self._output_path.exists():
            existing = json.loads(self._output_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                existing.append(data)
                data = existing
            else:
                data = [existing, data]
        self._output_path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )


class PrometheusReporter(MetricsReporter):
    def report(self, collector: MetricsCollector) -> str:
        data = collector.to_dict()
        lines: list[str] = []
        for name, value in data.get("counters", {}).items():
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in data.get("gauges", {}).items():
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        return "\n".join(lines)
