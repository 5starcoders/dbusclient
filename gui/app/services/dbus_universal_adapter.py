from __future__ import annotations  # Enable postponed evaluation of type hints for faster imports and fewer circular refs.

# Import the shared, validated D-Bus system-bus connection provider.
from app.dbus.bus_manager import BusManager  # Hands out a cached QDBusConnection for the system bus.

# Import the minimal invoker that performs a blocking D-Bus method call and returns the reply args.
from app.dbus.invoker import Invoker  # Wrapper around QDBusInterface.callWithArgumentList(...).

# Import the generic method locator that discovers which interface provides a given method (with caching).
from app.dbus.method_locator import MethodLocator  # Finds interface for (service, path, method) via Introspect XML.


class DbusUniversalAdapter:
    """
    Universal D-Bus adapter (service-agnostic).
    - Purpose: Call any method on any object path of any D-Bus service without hard-coding interfaces.
    - How: Uses MethodLocator to discover the interface that declares the method, then Invoker to call it.
    - Scope: Works on the *system bus* by default (good for services like Accounts, timedate1, NetworkManager).
    """

    def __init__(self, bus: str = "system") -> None:
        """
        Construct the adapter and select which bus to use.
        - For now, we support 'system' (the common case for admin services).
        - Session bus support can be added later if needed.
        """
        # Store the target bus type as a simple string for clarity/future extension.
        self._bus = bus  # Expected values: "system" (default). Add "session" in future if required.

    def _conn(self):
        """
        Return an open QDBusConnection based on the selected bus.
        - Currently returns the system bus (from BusManager).
        - This indirection allows easy extension to session bus later.
        """
        # If we ever add session bus, we can branch here (e.g., BusManager.session_bus()).
        return BusManager.system_bus()  # Use the validated, cached system bus connection.

    def call_method(
        self,
        service: str,
        object_path: str,
        method_name: str,
        *args,
    ):
        """
        Call a D-Bus method without hard-coding the interface.
        - Inputs:
            service: well-known D-Bus name (e.g., "org.freedesktop.Accounts").
            object_path: object path on that service (e.g., "/org/freedesktop/Accounts").
            method_name: the D-Bus member to invoke (e.g., "CreateUser").
            *args: positional arguments to pass exactly as the signature expects.
        - Behavior:
            1) Resolve which interface on (service, object_path) declares method_name (cached).
            2) Perform a blocking call using Invoker.
            3) Return the list of returned values (could be empty, one item, or many).
        - Raises:
            RuntimeError if the interface is not found or the D-Bus call fails.
        """
        # Acquire the correct bus connection (system bus for admin services).
        conn = self._conn()  # QDBusConnection instance.

        # Ask the MethodLocator to find which interface exposes the requested method on this object path.
        iface = MethodLocator.get_interface_for_method(conn, service, object_path, method_name)  # str | None
        if not iface:
            # If the interface is not found, raise a clear error so callers can handle it.
            raise RuntimeError(f"Method '{method_name}' not found via introspection on path '{object_path}' (service '{service}').")

        # With the interface resolved, invoke the method using our generic Invoker and return its arguments list.
        return Invoker.call(
            conn=conn,                 # Use the open bus connection.
            service=service,           # Target service name (e.g., org.freedesktop.Accounts).
            object_path=object_path,   # Target object path (manager or per-user object).
            interface=iface,           # Discovered interface that actually declares the method.
            member=method_name,        # The D-Bus member name to call (e.g., CreateUser).
            args=list(args),           # Positional arguments passed through as-is.
        )
