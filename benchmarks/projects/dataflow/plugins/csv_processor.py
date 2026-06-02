from typing import Any, Optional

from dataflow.processors.base import Processor, ProcessorRegistry


class CsvParseProcessor(Processor):
    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        import csv
        import io
        if isinstance(data, str):
            reader = csv.DictReader(io.StringIO(data))
            return list(reader)
        return data


class CsvSerializeProcessor(Processor):
    def __init__(self, name: str, config: Optional[dict] = None):
        super().__init__(name, config)
        self._fieldnames = config.get("fieldnames", []) if config else []

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        import csv
        import io
        if not isinstance(data, list):
            return str(data)
        buf = io.StringIO()
        fieldnames = self._fieldnames or (list(data[0].keys()) if data else [])
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue()


ProcessorRegistry.register("csv_parse", CsvParseProcessor)
ProcessorRegistry.register("csv_serialize", CsvSerializeProcessor)
