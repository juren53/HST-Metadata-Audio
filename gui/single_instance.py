"""
Single-instance guard for HAM.

Uses QLocalServer / QLocalSocket so a second launch silently raises
the already-running window rather than showing an error dialog.

Usage in launcher:
    guard = SingleInstanceGuard()
    if not guard.try_acquire():
        sys.exit(0)           # existing instance raised; we exit cleanly
    window = MainWindow()
    guard.connect_window(window)
    app.aboutToQuit.connect(guard.release)
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


_SOCKET_NAME = "HSTL-HAM-SingleInstance"
_CONNECT_TIMEOUT_MS = 500
_WRITE_TIMEOUT_MS = 1000


class SingleInstanceGuard:
    """Allows only one HAM process at a time; secondary launches raise the primary."""

    def __init__(self):
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        """
        Return True if this process should become the primary instance.
        Return False if an existing instance was found and signalled to raise
        (caller should exit immediately).
        """
        probe = QLocalSocket()
        probe.connectToServer(_SOCKET_NAME)
        if probe.waitForConnected(_CONNECT_TIMEOUT_MS):
            probe.write(b"raise")
            probe.waitForBytesWritten(_WRITE_TIMEOUT_MS)
            probe.disconnectFromServer()
            return False

        # Become the primary — remove any stale socket from a previous crash
        QLocalServer.removeServer(_SOCKET_NAME)
        self._server = QLocalServer()
        self._server.listen(_SOCKET_NAME)
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
            QLocalServer.removeServer(_SOCKET_NAME)
            self._server = None
