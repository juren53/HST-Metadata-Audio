"""Single-instance guard for HAM.

Copied from https://github.com/juren53/single-instance-guard (v1.0.0).
Uses QLocalServer / QLocalSocket so a second launch silently raises
the already-running window rather than showing an error dialog.

Usage in launcher:
    guard = SingleInstanceGuard("HSTL-HAM-SingleInstance")
    if not guard.try_acquire():
        sys.exit(0)           # existing instance raised; we exit cleanly
    window = MainWindow()
    guard.connect_window(window)
    app.aboutToQuit.connect(guard.release)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard:
    """Allows only one process at a time; secondary launches raise the primary."""

    def __init__(
        self,
        app_id: str,
        connect_timeout_ms: int = 500,
        write_timeout_ms: int = 1000,
    ):
        self._socket_name = app_id
        self._connect_timeout_ms = connect_timeout_ms
        self._write_timeout_ms = write_timeout_ms
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        """
        Return True if this process should become the primary instance.
        Return False if an existing instance was found and signalled to raise
        (caller should exit immediately).
        """
        probe = QLocalSocket()
        probe.connectToServer(self._socket_name)
        if probe.waitForConnected(self._connect_timeout_ms):
            probe.write(b"raise")
            probe.waitForBytesWritten(self._write_timeout_ms)
            probe.disconnectFromServer()
            return False

        # Become the primary — remove any stale socket from a previous crash
        QLocalServer.removeServer(self._socket_name)
        self._server = QLocalServer()
        self._server.listen(self._socket_name)
        return True

    def connect_window(self, window) -> None:
        """Wire incoming connections to raise *window*."""
        if self._server is None:
            return
        self._server.newConnection.connect(
            lambda: self._handle_connection(window)
        )

    def _handle_connection(self, window) -> None:
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda: self._on_data(conn, window))

    def _on_data(self, conn, window) -> None:
        data = bytes(conn.readAll())
        if b"raise" in data:
            # Un-minimise, then bring to front
            state = window.windowState() & ~Qt.WindowState.WindowMinimized
            window.setWindowState(state)
            window.show()
            window.raise_()
            window.activateWindow()
        conn.disconnectFromServer()

    def release(self) -> None:
        if self._server:
            self._server.close()
            QLocalServer.removeServer(self._socket_name)
            self._server = None
