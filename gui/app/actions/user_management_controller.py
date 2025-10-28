from __future__ import annotations  # Postpone type evaluation; speeds imports and avoids certain circular refs.

import crypt  # Provides SHA-512 shadow hashing (Linux glibc crypt); avoids storing plaintext passwords.
from PySide6.QtCore import QObject, Signal, Slot  # Qt base class + typed signals/slots for evented workflow.

     # Generic D-Bus caller that discovers interfaces via Introspection.
from app.services.dbus_universal_adapter import (DbusUniversalAdapter)
   


class UserManagementController(QObject):
    """
    A single controller that can host *all* user-related workflows (create, update, delete, etc.).
    - Today: implements `create_user(...)` end-to-end using the universal D-Bus adapter.
    - Tomorrow: add more methods (e.g., delete_user, set_real_name, lock_user), keeping one cohesive hub.
    - Design: UI emits an intent → controller coordinates → emits lifecycle results back to the UI.
    """

    # Lifecycle signals for the UI to react (enable spinner, show success/error, etc.).
    started = Signal()          # Emitted when any user-management operation begins.
    succeeded = Signal(str)     # Emitted on success; carries a string payload (e.g., created user object path).
    failed = Signal(str)        # Emitted on failure; carries a human-readable error message.

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the controller and its dependencies.
        - Uses the universal adapter on the *system* bus (Accounts service lives there).
        - Stores stable service identifiers (service name + manager path); no interface names are hard-coded.
        """
        super().__init__(parent)                              # Initialize QObject base (required for signals/slots).
        self._adapter = DbusUniversalAdapter(bus="system")    # Generic, interface-resolving D-Bus caller.
        self._service = "org.freedesktop.Accounts"            # Stable well-known name (discoverable; not an iface).
        self._manager_path = "/org/freedesktop/Accounts"      # Manager object path hosting CreateUser.
        self._account_type = 1                                # 1 = Standard user (AccountsService enum); configurable.

    @Slot(str, str, str)
    def create_user(self, username: str, realname: str, password: str) -> None:
        """
        Create a user and set its password, emitting lifecycle signals around the operation.

    Args:
        username: New account's login name (e.g., "alice").
        realname: Human-friendly full name (e.g., "Alice Liddell").
        password: Plaintext from UI; will be hashed in-memory (SHA-512 shadow) before D-Bus call.

    Emits:
        started()                         → immediately when invoked
        succeeded(user_object_path: str)  → when both CreateUser and SetPassword succeed
        failed(message: str)              → on any error
    """
    self.started.emit()  # Tell the UI we’re starting (disable button/spinner if desired).

    try:
        # --- Phase A: Create the user ---
        # NOTE: call_method(service, object_path, method_name, *args)
        # IMPORTANT: Use ALL POSITIONAL args here to avoid mixing keyword + positional.
        reply_args = self._adapter.call_method(
            self._service,                # service         → "org.freedesktop.Accounts"
            self._manager_path,           # object_path     → "/org/freedesktop/Accounts"
            "CreateUser",                 # method_name     → "CreateUser"
            username,                     # args[0] (s)     → username
            realname,                     # args[1] (s)     → real name
            int(self._account_type),      # args[2] (i)     → accountType (1 = standard user)
        )

        # Validate reply: CreateUser returns the new user's object path as the first (and only) value.
        if not reply_args or not isinstance(reply_args[0], str):
            raise RuntimeError("Accounts.CreateUser returned an unexpected reply (no object path).")

        user_object_path: str = reply_args[0]  # e.g., "/org/freedesktop/Accounts/User1002"

        # --- Phase B: Hash the password (SHA-512 shadow) and set it on the user object ---
        # Build a proper $6$ salt and produce a shadow-compatible hash; no plaintext is stored or logged.
        sha512_shadow_hash: str = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))

        # Call SetPassword on the per-user object.
        # Again, use ALL POSITIONAL args to keep the call syntax valid.
        self._adapter.call_method(
            self._service,            # service         → "org.freedesktop.Accounts"
            user_object_path,         # object_path     → per-user object from CreateUser
            "SetPassword",            # method_name     → "SetPassword"
            sha512_shadow_hash,       # args[0] (s)     → shadow-style SHA-512 hash
            "",                       # args[1] (s)     → hint (empty for now)
        )

        # If both calls succeed, notify UI with the created user’s object path.
        self.succeeded.emit(user_object_path)

    except Exception as exc:
        # Surface a clean error string to the UI.
        self.failed.emit(str(exc))
