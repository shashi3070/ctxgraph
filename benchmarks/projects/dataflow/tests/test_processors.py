import pytest
from dataflow.processors.transform import TransformProcessor, MapProcessor, FilterProcessor, FlatMapProcessor
from dataflow.processors.aggregate import AggregateProcessor, WindowProcessor, GroupByProcessor
from dataflow.processors.io import FileSource, FileSink
from dataflow.processors.base import ProcessorRegistry


class TestTransformProcessors:
    def test_transform_with_function(self):
        p = TransformProcessor("upper", lambda d, ctx: d.upper() if isinstance(d, str) else d)
        assert p.process("hello") == "HELLO"

    def test_map_processor(self):
        p = MapProcessor("double", lambda x, ctx: x * 2)
        assert p.process([1, 2, 3]) == [2, 4, 6]

    def test_filter_processor(self):
        p = FilterProcessor("even", lambda x, ctx: x % 2 == 0)
        assert p.process([1, 2, 3, 4]) == [2, 4]

    def test_flatmap_processor(self):
        p = FlatMapProcessor("expand", lambda x, ctx: [x, x * 10])
        assert p.process([1, 2]) == [1, 10, 2, 20]


class TestAggregateProcessors:
    def test_window_processor(self):
        p = WindowProcessor("window", window_size=3, stride=1)
        result = p.process([1, 2, 3, 4, 5])
        assert len(result) >= 1

    def test_groupby_processor(self):
        p = GroupByProcessor("group", lambda x, ctx: x["type"])
        data = [{"type": "a", "val": 1}, {"type": "b", "val": 2}, {"type": "a", "val": 3}]
        result = p.process(data)
        assert "a" in result
        assert "b" in result
        assert len(result["a"]) == 2


class TestProcessorRegistry:
    def test_register_and_create(self):
        from dataflow.processors.transform import MapProcessor
        ProcessorRegistry.register("test_mapper", MapProcessor)
        proc = ProcessorRegistry.create("test_mapper", "test", {"mapping_fn": lambda x, ctx: x})
        assert proc.name == "test"

    def test_list_processors(self):
        procs = ProcessorRegistry.list()
        assert "csv_parse" in procs
        assert "http_fetch" in procs

    def test_get_unknown(self):
        assert ProcessorRegistry.get("nonexistent") is None

    def test_create_unknown(self):
        with pytest.raises(ValueError):
            ProcessorRegistry.create("nonexistent", "x")
