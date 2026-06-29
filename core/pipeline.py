"""
Pipeline orchestrator for HAM.

Runs steps 1-5 in sequence. Each step is a StepProcessor subclass registered
with Pipeline.register_step(). The pipeline halts on the first step failure
unless continue_on_error=True.
"""

from typing import Dict, List
import logging

from steps.base_step import StepProcessor, ProcessingContext, StepResult


class PipelineResult:
    def __init__(self):
        self.success = True
        self.steps_completed: List[int] = []
        self.step_results: Dict[int, StepResult] = {}
        self.error_message: str = ""

    def add_step_result(self, step_num: int, result: StepResult):
        self.step_results[step_num] = result
        if result.success:
            self.steps_completed.append(step_num)
        else:
            self.success = False
            if not self.error_message:
                self.error_message = f"Step {step_num} failed: {result.message}"


class Pipeline:
    """Orchestrates execution of HAM processing steps."""

    def __init__(self, context: ProcessingContext):
        self.context = context
        self.steps: Dict[int, StepProcessor] = {}
        self.logger: logging.Logger = context.logger

    def register_step(self, step: StepProcessor):
        self.steps[step.step_number] = step
        self.logger.debug(f"Registered {step}")

    def run(
        self,
        start_step: int = 1,
        end_step: int = 5,
        dry_run: bool = False,
        continue_on_error: bool = False,
    ) -> PipelineResult:
        result = PipelineResult()
        action = "Dry-run" if dry_run else "Running"
        self.logger.info(f"{action} pipeline steps {start_step}–{end_step}")

        for step_num in range(start_step, end_step + 1):
            if step_num not in self.steps:
                self.logger.warning(f"Step {step_num} not registered — skipped")
                continue

            step = self.steps[step_num]

            if dry_run:
                self.logger.info(f"Would run {step}")
                continue

            try:
                step_result = step.run(self.context)
                result.add_step_result(step_num, step_result)

                if not step_result.success and not continue_on_error:
                    self.logger.error(f"Pipeline halted at step {step_num}")
                    break
            except Exception as e:
                msg = f"Pipeline exception at step {step_num}: {e}"
                self.logger.error(msg, exc_info=True)
                result.success = False
                result.error_message = msg
                if not continue_on_error:
                    break

        if result.success:
            self.logger.info("Pipeline completed successfully")
        else:
            self.logger.error(f"Pipeline failed: {result.error_message}")

        return result

    def get_registered_steps(self) -> List[int]:
        return sorted(self.steps.keys())
