from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

from dataflow.processors.base import Processor


class SourceProcessor(Processor):
    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        return self.read()

    def read(self) -> Any:
        raise NotImplementedError


class SinkProcessor(Processor):
    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        return self.write(data)

    def write(self, data: Any) -> Any:
        raise NotImplementedError


class FileSource(SourceProcessor):
    def __init__(self, name: str, file_path: str, format: str = "json", config: Optional[dict] = None):
        super().__init__(name, config)
        self._file_path = Path(file_path)
        self._format = format

    def read(self) -> Any:
        if not self._file_path.exists():
            raise FileNotFoundError(f"Source file not found: {self._file_path}")
        text = self._file_path.read_text(encoding="utf-8")
        if self._format == "json":
            return json.loads(text)
        elif self._format == "csv":
            reader = csv.DictReader(text.splitlines())
            return list(reader)
        elif self._format == "text":
            return text.splitlines()
        raise ValueError(f"Unsupported format: {self._format}")

    @property
    def path(self) -> Path:
        return self._file_path


class FileSink(SinkProcessor):
    def __init__(self, name: str, file_path: str, format: str = "json", append: bool = False, config: Optional[dict] = None):
        super().__init__(name, config)
        self._file_path = Path(file_path)
        self._format = format
        self._append = append

    def write(self, data: Any) -> str:
        mode = "a" if self._append else "w"
        if self._format == "json":
            text = json.dumps(data, indent=2, default=str)
        elif self._format == "csv":
            if isinstance(data, list) and data:
                import io
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                text = buf.getvalue()
            else:
                text = str(data)
        elif self._format == "text":
            text = "\n".join(data) if isinstance(data, list) else str(data)
        else:
            text = str(data)
        self._file_path.write_text(text, encoding="utf-8")
        return text

    @property
    def path(self) -> Path:
        return self._file_path


class KafkaSource(SourceProcessor):
    def __init__(self, name: str, topic: str, bootstrap_servers: str = "localhost:9092", config: Optional[dict] = None):
        super().__init__(name, config)
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._consumer = None

    def read(self) -> Any:
        return {"topic": self._topic, "messages": [], "source": "kafka"}


class KafkaSink(SinkProcessor):
    def __init__(self, name: str, topic: str, bootstrap_servers: str = "localhost:9092", config: Optional[dict] = None):
        super().__init__(name, config)
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._producer = None

    def write(self, data: Any) -> dict:
        return {"topic": self._topic, "messages_sent": 1, "target": "kafka"}
