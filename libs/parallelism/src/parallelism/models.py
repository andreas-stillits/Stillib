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
    duration: float


@dataclass(slots=True)
class TaskSuccess[InputType, OutputType]:
    index: int
    task: InputType
    task_name: str
    result: OutputType
    duration: float


@dataclass(slots=True)
class TaskFailure[InputType]:
    index: int
    task: InputType
    task_name: str
    exc_type: str
    exc_message: str
    traceback: str
    duration: float


type TaskOutcome[InputType, OutputType] = TaskSuccess[
    InputType, OutputType
] | TaskFailure[InputType]


@dataclass(slots=True)
class RunReport[InputType, OutputType]:
    successes: list[TaskSuccess[InputType, OutputType]]
    failures: list[TaskFailure[InputType]]
    interrupted: bool
    duration: float

    @property
    def ok(self) -> bool:
        return (not self.failures) and (not self.interrupted)

    @property
    def results(self) -> list[OutputType]:
        return [item.result for item in self.successes]


class TaskExecutionError(RuntimeError):
    def __init__(
        self,
        failure: TaskFailure[Any],
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


@dataclass(slots=True)
class _BatchSubmission[InputType]:
    indexes: list[int]
    tasks: list[InputType]


@dataclass(slots=True)
class _BatchItemSuccess[OutputType]:
    position: int
    result: OutputType
    duration: float


@dataclass(slots=True)
class _BatchItemFailure:
    position: int
    exc_type: str
    exc_message: str
    traceback: str
    duration: float


type _BatchItem[OutputType] = _BatchItemSuccess[OutputType] | _BatchItemFailure
