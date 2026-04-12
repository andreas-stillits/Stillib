from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeVar

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")

type Ordering = Literal["completion", "input"]
type ErrorPolicy = Literal["raise", "collect"]
type InterruptPolicy = Literal["cancel", "drain"]


@dataclass(slots=True)
class ProgressUpdate:
    submitted: int
    completed: int
    failed: int
    running: int
    total: int | None
    elapsed_time: float


@dataclass(slots=True)
class CompletedTask[InputType, OutputType]:
    index: int
    task: InputType
    task_name: str
    result: OutputType
    elapsed_time: float


@dataclass(slots=True)
class FailedTask[InputType]:
    index: int
    task: InputType
    task_name: str
    exc_type: str
    exc_message: str
    traceback: str
    elapsed_time: float


type TaskOutcome[InputType, OutputType] = CompletedTask[
    InputType, OutputType
] | FailedTask[InputType]


@dataclass(slots=True)
class RunReport[InputType, OutputType]:
    completed: list[CompletedTask[InputType, OutputType]]
    failed: list[FailedTask[InputType]]
    interrupted: bool
    elapsed_time: float

    @property
    def ok(self) -> bool:
        return (not self.failed) and (not self.interrupted)

    @property
    def results(self) -> list[OutputType]:
        return [item.result for item in self.completed]


class TaskExecutionError(RuntimeError):
    def __init__(
        self,
        failure: FailedTask[Any],
        partial_report: RunReport[Any, Any] | None = None,
    ) -> None:
        self.failure = failure
        self.partial_report = partial_report
        message = (
            f"{failure.task_name} failed with "
            f"{failure.exc_type}: {failure.exc_message}"
        )
        super().__init__(message)


class ParallelRunInterrupted(KeyboardInterrupt):
    def __init__(self, partial_report: RunReport[Any, Any]) -> None:
        self.partial_report = partial_report
        super().__init__("Parallel run interrupted by user")
