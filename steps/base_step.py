"""
Base Step Processor for HAM.

Defines the abstract base class and shared data structures used by all 5 steps.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from utils.validator import ValidationResult
from utils.path_manager import PathManager
from config.config_manager import ConfigManager


@dataclass
class StepResult:
    """Result of a single step execution."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    files_processed: List[Path] = field(default_factory=list)


class ProcessingContext:
    """Shared context passed through the pipeline."""

    def __init__(
        self,
        paths: PathManager,
        config: ConfigManager,
        logger: logging.Logger,
        current_step: int = 0,
        batch_id: Optional[str] = None,
    ):
        self.paths = paths
        self.config = config
        self.logger = logger
        self.current_step = current_step
        self.batch_id = batch_id
        self.shared_data: Dict[str, Any] = {}

    def set_data(self, key: str, value: Any):
        self.shared_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.shared_data.get(key, default)


class StepProcessor(ABC):
    """Abstract base class for all HAM step processors."""

    def __init__(self, step_number: int, step_name: str):
        self.step_number = step_number
        self.step_name = step_name
        self.logger: Optional[logging.Logger] = None

    def setup(self, context: ProcessingContext) -> bool:
        self.logger = context.logger
        return True

    @abstractmethod
    def validate_inputs(self, context: ProcessingContext) -> ValidationResult:
        """Validate inputs before execution."""

    @abstractmethod
    def execute(self, context: ProcessingContext) -> StepResult:
        """Execute the step."""

    @abstractmethod
    def validate_outputs(self, context: ProcessingContext) -> ValidationResult:
        """Validate outputs after execution."""

    def run(self, context: ProcessingContext) -> StepResult:
        """Full step lifecycle: validate-in → execute → validate-out."""
        context.current_step = self.step_number

        if not self.setup(context):
            return StepResult(False, f"Setup failed for Step {self.step_number}")

        self.logger.info(f"Starting Step {self.step_number}: {self.step_name}")

        try:
            in_val = self.validate_inputs(context)
            if not in_val.is_valid:
                msg = f"Input validation failed: {'; '.join(in_val.errors)}"
                self.logger.error(msg)
                return StepResult(False, msg)
            for w in in_val.warnings:
                self.logger.warning(f"Input warning: {w}")

            result = self.execute(context)
            if not result.success:
                self.logger.error(f"Step execution failed: {result.message}")
                return result

            out_val = self.validate_outputs(context)
            if not out_val.is_valid:
                msg = f"Output validation failed: {'; '.join(out_val.errors)}"
                self.logger.error(msg)
                return StepResult(False, msg)
            for w in out_val.warnings:
                self.logger.warning(f"Output warning: {w}")

            context.config.update_step_status(self.step_number, True)
            self.logger.info(f"Step {self.step_number} completed successfully")
            return result

        except Exception as e:
            msg = f"Step {self.step_number} raised exception: {e}"
            self.logger.error(msg, exc_info=True)
            return StepResult(False, msg)

    def get_step_config(self, context: ProcessingContext, key: str, default: Any = None) -> Any:
        return context.config.get(f"step_configurations.step{self.step_number}.{key}", default)

    def __str__(self):
        return f"Step {self.step_number}: {self.step_name}"
