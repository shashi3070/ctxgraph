from typing import Any, Optional

from dataflow.processors.base import Processor, ProcessorRegistry


class HttpFetchProcessor(Processor):
    def __init__(self, name: str, config: Optional[dict] = None):
        super().__init__(name, config)
        self._default_url = (config or {}).get("url", "")

    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        url = data if isinstance(data, str) else self._default_url
        if not url:
            return data
        return {"url": url, "status": 200, "headers": {"content-type": "application/json"}, "body": "{}"}


class HttpPostProcessor(Processor):
    def process(self, data: Any, context: Optional[dict] = None) -> Any:
        if isinstance(data, dict):
            return {**data, "posted": True}
        return data


ProcessorRegistry.register("http_fetch", HttpFetchProcessor)
ProcessorRegistry.register("http_post", HttpPostProcessor)
