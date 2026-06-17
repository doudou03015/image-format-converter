"""Qt worker for background batch conversion."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.models.task import BatchProgress, ConversionTask, SessionSummary
from app.services.converter import ConverterService


class BatchConversionWorker(QObject):
    """Run a batch conversion on a background thread."""

    progress_changed = Signal(object)
    file_finished = Signal(object)
    batch_finished = Signal(object)

    def __init__(self, converter: ConverterService, tasks: list[ConversionTask]) -> None:
        super().__init__()
        self._converter = converter
        self._tasks = tasks
        self._cancel_requested = False

    def cancel(self) -> None:
        """Ask the worker to stop after the current file completes."""

        self._cancel_requested = True

    @Slot()
    def run(self) -> None:
        """Process all queued tasks and emit structured progress events."""

        total = len(self._tasks)
        processed = 0
        success_count = 0
        failure_count = 0
        skipped_count = 0
        results = []

        for task in self._tasks:
            if self._cancel_requested:
                break

            result = self._converter.convert_file(task)
            results.append(result)
            processed += 1

            if result.status == "success":
                success_count += 1
            elif result.status == "failed":
                failure_count += 1
            elif result.status == "skipped":
                skipped_count += 1

            self.file_finished.emit(result)
            self.progress_changed.emit(
                BatchProgress(
                    total=total,
                    processed=processed,
                    success_count=success_count,
                    failure_count=failure_count,
                    skipped_count=skipped_count,
                    current_file=task.source_path.name,
                )
            )

        self.batch_finished.emit(
            SessionSummary(
                total=total,
                processed=processed,
                success_count=success_count,
                failure_count=failure_count,
                skipped_count=skipped_count,
                cancelled=self._cancel_requested,
                results=results,
            )
        )
