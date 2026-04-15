from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type Ordering = Literal["completion", "input"]
type ErrorPolicy = Literal["raise", "collect"]


# Model for progress updates emitted after each task completion, used for the progress_callback
@dataclass(slots=True)
class ProgressUpdate:
    submitted: int
    completed: int
    failures: int
    running: int
    total: int | None
    elapsed_time: float


# Model for a successfully completed task
@dataclass(slots=True)
class CompletedTask[Task, Result]:
    index: int
    task: Task
    task_name: str
    result: Result
    elapsed_time: float


# Model for a failed task, with info on the exception
@dataclass(slots=True)
class FailedTask[Task]:
    index: int
    task: Task
    task_name: str
    exc_type: str
    exc_message: str
    traceback: str
    infrastructure_error: bool
    elapsed_time: float


# Union type for a task outcome, which can be either a CompletedTask or a FailedTask
type TaskOutcome[Task, Result] = CompletedTask[Task, Result] | FailedTask[Task]


# Run report model to summarize the results of a parallel run
@dataclass(slots=True)
class RunReport[Task, Result]:
    completed: list[CompletedTask[Task, Result]]
    failures: list[FailedTask[Task]]
    interrupted: bool
    elapsed_time: float

    # did all tasks complete successfully without interruption?
    @property
    def ok(self) -> bool:
        return (not self.failures) and (not self.interrupted)

    # get list of results from completed tasks
    @property
    def results(self) -> list[Result]:
        return [item.result for item in self.completed]


# Custom exceptions for error handling in parallel runs
# Inherit from RuntimeError and KeyboardInterrupt respectively
class TaskExecutionError[Task, Result](RuntimeError):
    def __init__(
        self,
        failure: FailedTask[Task],
        partial_report: RunReport[Task, Result] | None = None,
    ) -> None:
        # attach custom information: the failed task and a partial RunReport for debugging
        self.failure = failure
        self.partial_report = partial_report
        message = (
            f"{failure.task_name} failed with {failure.exc_type}: {failure.exc_message}"
        )
        super().__init__(message)


class ParallelRunInterrupted(KeyboardInterrupt):
    def __init__(self, partial_report: RunReport[Any, Any]) -> None:
        # attach the partial RunReport to the exception for debugging
        self.partial_report = partial_report
        super().__init__("Parallel run interrupted by user")
