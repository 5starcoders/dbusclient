from __future__ import annotations  # Allow postponed type hints; speeds imports and avoids circular refs.

# QtDBus imports: this is Qt’s native D-Bus client API (like fetch()/XHR but for D-Bus).
from PySide6.QtDBus import (
    QDBus,               # Provides call modes (e.g., blocking vs queued).
    QDBusConnection,     # An open connection to a D-Bus (system or session).
    QDBusInterface,      # Convenience wrapper to call a method on (service, path, interface).
    QDBusMessage,        # Represents a D-Bus message (method call / return / error).
)

# Web analogy (JS):
# - Think of this file like a tiny "fetch wrapper" that takes (url + method + body) and returns JSON.
# - Here, the "url" is (service, path, interface), the "method" is the D-Bus member, and "body" is args.


class Invoker:
    """
    Minimal, synchronous D-Bus invoker.

    Responsibilities:
    - Create a typed interface handle for (service, object path, interface).
    - Call a method member with a list of arguments (blocking).
    - Raise a clear error on D-Bus failure; return Python values on success.

    Why synchronous (blocking) for now?
    - Simpler to learn and debug.
    - Adequate for short, privileged admin calls (e.g., CreateUser).
    - We can add async/queued versions later if needed.
    """

    @staticmethod
    def call(
        conn: QDBusConnection,
        service: str,
        object_path: str,
        interface: str,
        member: str,
        args: list | tuple = (),
    ) -> list:
        """
        Perform a blocking D-Bus method call and return the list of returned arguments.

        Parameters:
        - conn: an open QDBusConnection (system/session) — use BusManager.system_bus().
        - service: well-known bus name (e.g., "org.freedesktop.Accounts").
        - object_path: target object path (e.g., "/org/freedesktop/Accounts").
        - interface: interface name (e.g., "org.freedesktop.Accounts").
        - member: method name to invoke (e.g., "CreateUser").
        - args: positional arguments to pass (must match the D-Bus signature order).

        Returns:
        - A list of returned values from the D-Bus reply (empty if the method returns void).
          If you expect a single value, pick index 0 (we keep list to stay generic).

        Raises:
        - RuntimeError with a clear message if the interface is invalid or the call returns an error.
        """
        # Create a convenience interface bound to (service, path, interface) on the given connection.
        # JS analogy: new FetchClient(baseURL = service/path/interface)
        iface = QDBusInterface(service, object_path, interface, conn)

        # If the interface failed to resolve (service/path/interface wrong or unavailable), stop early.
        if not iface.isValid():
            raise RuntimeError(
                f"Invalid D-Bus interface: service='{service}', path='{object_path}', interface='{interface}'"
            )

        # Make a blocking call with a positional arg list.
        # QDBus.CallBlock means: send the method call and wait for the reply (or error) before returning.
        # reply: QDBusMessage is cloning of QDBusMessage
        reply: QDBusMessage = iface.callWithArgumentList(QDBus.CallBlock, member, list(args))

        # If the remote side returned an error, convert it to a Python exception with details.
        if reply.type() == QDBusMessage.ErrorMessage:
            # errorName() is usually something like org.freedesktop.DBus.Error.AccessDenied, etc.
            # errorMessage() carries the human-readable reason.
            raise RuntimeError(f"D-Bus call failed: {reply.errorName()}: {reply.errorMessage()}")

        # Success: extract the returned argument list (could be [], [value], or multiple values).
        return reply.arguments()
