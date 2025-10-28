from __future__ import annotations  # Faster imports; flexible type hints.

# QtDBus is Qt’s D-Bus binding (like a native “HTTP client” but for D-Bus).
from PySide6.QtDBus import QDBusConnection  # Provides connections to session/system buses.


class BusManager:
    """
    Tiny helper to hand out a shared D-Bus connection.
    Web analogy:
    - Think of this like a singleton Axios instance preconfigured for a base URL.
    - Here, the “base URL” is the **system bus** (root-level services like Accounts).
    """

    _system_bus: QDBusConnection | None = None  # Class-level cache of the system bus connection.

    @classmethod
    def system_bus(cls) -> QDBusConnection:
        """
        Return a live connection to the **system** D-Bus.
        - Creates and caches it on first call.
        - Verifies connectivity and raises a clear error if not connected.
        """
        # If we already created it once, just return the cached connection.
        if cls._system_bus is not None:
            return cls._system_bus

        # Ask Qt for the shared system bus connection (managed by Qt under the hood).
        conn = QDBusConnection.systemBus()

        # Sanity check: if the connection failed, stop early with a clear message.
        if not conn.isConnected():
            # .lastError() can provide extra details if needed later.
            raise RuntimeError("Failed to connect to the system D-Bus (QtDBus).")

        # Cache it for subsequent calls and return it.
        cls._system_bus = conn
        return cls._system_bus
