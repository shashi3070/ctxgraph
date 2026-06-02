import pytest
from dataflow.core.pipeline import Pipeline, PipelineBuilder
from dataflow.core.stage import PipelineStage, StageStatus
from dataflow.core.context import PipelineContext
from dataflow.core.scheduler import SequentialScheduler, ParallelScheduler
from dataflow.processors.transform import TransformProcessor, MapProcessor, FilterProcessor


class UppercaseStage(PipelineStage):
    def process(self, context):
        if isinstance(context.data, str):
            context.update(context.data.upper())
        return context.data


class ReverseStage(PipelineStage):
    def process(self, context):
        if isinstance(context.data, str):
            context.update(context.data[::-1])
        return context.data


class TestPipeline:
    def test_basic_pipeline(self):
        stages = [UppercaseStage("upper"), ReverseStage("reverse")]
        pipeline = Pipeline("test", stages)
        result = pipeline.run("hello")
        assert result == "OLLEH"
        assert pipeline.status == StageStatus.COMPLETED

    def test_empty_pipeline(self):
        pipeline = Pipeline("empty", [])
        result = pipeline.run("data")
        assert result == "data"

    def test_builder_pattern(self):
        pipeline = (PipelineBuilder("builder")
                    .with_stage(UppercaseStage("upper"))
                    .with_stage(ReverseStage("reverse"))
                    .build())
        result = pipeline.run("world")
        assert result == "DLROW"

    def test_parallel_scheduler(self):
        stages = [UppercaseStage("upper"), ReverseStage("reverse")]
        pipeline = Pipeline("parallel", stages, scheduler=ParallelScheduler(max_workers=2))
        result = pipeline.run("hello")
        assert result is not None

    def test_get_stage_by_name(self):
        stage = UppercaseStage("finder")
        pipeline = Pipeline("test", [stage])
        assert pipeline.get_stage_by_name("finder") is stage
        assert pipeline.get_stage_by_name("nonexistent") is None

    def test_stage_status_transitions(self):
        stage = UppercaseStage("status_test")
        assert stage.status == StageStatus.PENDING
        stage.execute(PipelineContext("test"))
        assert stage.status == StageStatus.COMPLETED

    def test_pipeline_event_emission(self):
        events = []
        pipeline = Pipeline("events", [UppercaseStage("upper")])
        pipeline.event_bus.subscribe("started", type("Handler", (), {"handle": lambda self, e: events.append(e)})())
        pipeline.run("data")
        assert len(events) > 0

    def test_map_processor_in_pipeline(self):
        class MapStage(PipelineStage):
            def __init__(self):
                super().__init__("mapper")
                self.processor = MapProcessor("mapper", lambda x, ctx: x * 2)
            def process(self, context):
                context.update(self.processor.process(context.data))
                return context.data

        pipeline = Pipeline("map", [MapStage()])
        result = pipeline.run([1, 2, 3])
        assert result == [2, 4, 6]
