from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot


class CreateUserAction(QObject):
    """
    Controller for the "Create User" flow.

    Web analogy:
    - Think of this as your "controller" (or a small Redux thunk/Action creator).
    - It receives an intent from the UI, coordinates work (DBus calls in later phases),
      and emits results back as events (signals) for the UI to react to.
    """

    # High-level lifecycle signals for the UI (view) to subscribe to.
    started = Signal()                           # Emitted when the action begins (for spinners/disable UI).
    succeeded = Signal(str)                      # Emitted on success; carries the new user's object path.
    failed = Signal(str)                         # Emitted on failure; carries a human-readable error.

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # In Phase 3 we will inject the Accounts adapter dependency here, e.g.:
        # self._accounts = accounts_adapter

    @Slot(str, str, str)
    def execute(self, username: str, realname: str, password: str) -> None:
        """
        Entry point to perform the user creation.
        Phase 7/3 plan:
          - Phase 3/4 will call DBus: CreateUser → SetPassword (hashed).
          - For now, we simulate the flow and emit signals so the UI can be wired end-to-end.
        """
        self.started.emit()

        # PHASE-1/2 stub: simulate success path (no DBus yet).
        # We'll replace this with real AccountsService calls next.
        try:
            # Pretend we called org.freedesktop.Accounts.CreateUser(...)
            # and got back an object path like "/org/freedesktop/Accounts/User1002".
            fake_object_path = "/org/freedesktop/Accounts/UserFAKE"
            # Pretend we then called User.SetPassword(<sha512_shadow_hash>, hint)
            # and it succeeded.
            self.succeeded.emit(fake_object_path)
        except Exception as exc:
            # Any exception maps to a user-visible failure message.
            self.failed.emit(str(exc))
