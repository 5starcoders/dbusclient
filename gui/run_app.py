from __future__ import annotations  # Enable postponed evaluation of type hints for faster imports.

import sys  # Provides sys.argv for QApplication to parse command-line args.

# Qt: only import QApplication here; all visual widgets live in the UI layer.
from PySide6.QtWidgets import QApplication

# App components: import the top-level window and the action/controller.
from app.ui.main_window import MainWindow            # Our UI “page component”.
from app.actions.create_user_action import CreateUserAction  # Controller for the Create User flow.


def main() -> int:
    """
    Thin application bootstrap:
    - Initialize the Qt runtime (QApplication).
    - Create the main window (UI) and the action (controller).
    - Wire UI intents → action, and action lifecycle → UI feedback.
    - Enter the Qt event loop.
    """
    app = QApplication(sys.argv)                     # Create the single Qt app object; owns the event loop.

    # App identity: broad/future-proof so we can host multiple D-Bus tools (Accounts, TimeDate, Network, …).
    app.setApplicationName("D-Bus Service Studio")   # Human-readable app name used by desktop integrations.
    app.setOrganizationName("DBusClient")            # Vendor/org string; affects Qt settings/cache paths.
    app.setDesktopFileName("dbus-service-studio")    # Desktop entry ID for Linux environments.

    window = MainWindow()                            # Instantiate our main window (pure UI layer).

    action = CreateUserAction(parent=window)         # Controller; parented to window for lifecycle management.

    # ---------- UI → Action (intent) ----------
    # For now, pass demo/static values. In a later step, these will come from inputs/config.
    def _on_create_user_requested() -> None:
        username = "demo_user"                       # Temporary stub value (no logging).
        realname = "Demo User"                       # Temporary stub value.
        password = "demo-password"                   # Temporary stub value; will be hashed in Phase 3.
        action.execute(username, realname, password) # Kick off the action (will emit started/succeeded/failed).

    window.create_user_requested.connect(_on_create_user_requested)  # Wire UI signal to controller entrypoint.

    # ---------- Action → UI (lifecycle feedback) ----------
    def _on_started() -> None:
        # Keep popups inside the UI layer via convenience helpers.
        window.show_info("Starting… (stub, no D-Bus yet)", title="Create User")

    def _on_succeeded(obj_path: str) -> None:
        # Show the (fake, for now) AccountsService object path to prove end-to-end wiring.
        window.show_info(f"User created (stub).\nObject path:\n{obj_path}", title="Success")

    def _on_failed(message: str) -> None:
        # Surface errors via a UI-owned helper (keeps QMessageBox out of non-UI files).
        window.show_error(message, title="Failed")

    action.started.connect(_on_started)              # When the action begins, notify the user.
    action.succeeded.connect(_on_succeeded)          # On success, show the returned object path.
    action.failed.connect(_on_failed)                # On failure, show an error popup.

    window.show()                                    # Make the window visible on screen.
    return app.exec()                                # Enter the Qt event loop (blocks until app exit).


# Standard launcher guard: run main() only when executed directly (not when imported as a module).
if __name__ == "__main__":
    exit_code = main()                               # Execute the program and capture its exit code.
    raise SystemExit(exit_code)                      # Exit cleanly so shells/scripts receive the proper status.
