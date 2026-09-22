"""
Background worker threads for HAM GUI.

Ported from HPM's per-step QThread worker pattern (see
`MetadataEmbeddingThread` in
Photos/Version-2/Framework/gui/dialogs/step5_dialog.py) so long-running
pipeline steps don't block the UI thread.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class StepRunner(QThread):
    """Runs a single StepProcessor off the UI thread.

    Log messages already reach the GUI via the logger's GUILogHandler —
    Qt auto-queues signal emissions from a worker thread onto the GUI
    thread, so no separate progress signal is needed here. This thread
    only needs to report the terminal outcome.
    """

    finished = pyqtSignal(int, object)  # step_num, StepResult
    error = pyqtSignal(int, str)        # step_num, message

    def __init__(self, step_num, step, context, parent=None):
        super().__init__(parent)
        self.step_num = step_num
        self._step = step
        self._context = context

    def run(self):
        try:
            result = self._step.run(self._context)
        except Exception as exc:  # noqa: BLE001 - surface any step failure to the GUI
            self.error.emit(self.step_num, str(exc))
            return
        self.finished.emit(self.step_num, result)
